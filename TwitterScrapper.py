import asyncio
import os
import csv
import random
import glob
import json
import TextProcessing as tp
import RandomValues as rv
from playwright.async_api import async_playwright
from datetime import datetime, timezone, timedelta
from urllib.parse import quote

# --- CONFIGURAÇÕES ---
MAX_TWEETS_PER_QUERY = 15
MAX_RELOADS = 3
DATA_INICIO=(2025,11,16)
DATA_FINAL=(2025,11,30)
ACCOUNTS_DIR = "accounts"  # Pasta onde ficam os JSONs das contas
OUTPUT_FILE = "tweets.csv"
PROXIES = []

# Seus grupos de pesquisa
QUERY_GROUPS = [
    ["suicida", "suicídio", "me matar", "meu bilhete suicida", "minha carta suicida", "ir dormir pra sempre"],
    ["acabar com a minha vida", "nunca acordar", "não consigo continuar", "não vale a pena viver", "pronto para pular"],
    ["dormir pra sempre", "quero morrer", "estar morto", "melhor sem mim", "melhor morto"],
    ["plano de suicídio", "pacto de suicídio", "cansado de viver", "não quero estar aqui", "morrer sozinho"]
]

# Controle de Concorrência
global_lock = asyncio.Lock()
existing_tweet_ids = set()

# --- PREPARAÇÃO DE ARQUIVOS ---
if not os.path.exists("csv_files"):
    os.makedirs("csv_files")
if not os.path.exists(ACCOUNTS_DIR):
    os.makedirs(ACCOUNTS_DIR)

# Definição das colunas
CSV_FIELDS = ["tweet_id", "text", "timestamp", "query_group", "account_used"]

# Carregar IDs já salvos para evitar duplicatas
if os.path.exists(OUTPUT_FILE):
    with open(OUTPUT_FILE, "r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if "tweet_id" in row:
                existing_tweet_ids.add(row["tweet_id"])
else:
    with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        writer.writeheader()


def convert_utc_to_brasilia(utc_str):
    if not utc_str: return None
    dt_utc = datetime.fromisoformat(utc_str.replace("Z", "+00:00"))
    brasilia_tz = timezone(timedelta(hours=-3))
    return dt_utc.astimezone(brasilia_tz).strftime("%Y-%m-%d %H:%M:%S")


def build_x_query(terms, since=None, until=None, lang="pt"):
    query = "(" + " OR ".join([f'"{t}"' for t in terms]) + ")"
    query += " -filter:media -filter:links"
    if since: query += f" since:{since}"
    if until: query += f" until:{until}"
    if lang: query += f" lang:{lang}"
    return quote(query)


async def save_tweet(data):
    """Salva no CSV imediatamente (Thread-Safe)"""
    async with global_lock:
        with open(OUTPUT_FILE, "a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
            writer.writerow(data)


async def scrape_specific_query_with_account(browser, account_file, terms, day_start, day_end, group_index):
    account_name = os.path.basename(account_file).replace(".json", "")

    # 1. Cria o contexto SEM o storage_state
    context = await browser.new_context(
        user_agent=rv.get_random_user_agent(),
        viewport=rv.get_random_viewport()
    )

    # 2. Carrega e limpa os cookies do arquivo JSON manualmente
    try:
        with open(account_file, "r", encoding="utf-8") as f:
            cookies_list = json.load(f)

        # Pequena limpeza para garantir compatibilidade com Playwright
        clean_cookies = []
        for c in cookies_list:
            # O Playwright as vezes reclama desses campos se vierem da extensão
            c.pop("sameSite", None)
            c.pop("storeId", None)
            c.pop("hostOnly", None)
            c.pop("expirationDate", None)  # Opcional: as vezes data quebrada atrapalha
            clean_cookies.append(c)

        await context.add_cookies(clean_cookies)
        print(f"      {account_name}: Cookies carregados com sucesso.")

    except Exception as e:
        print(f"   ❌ Erro ao carregar cookies de {account_name}: {e}")
        await context.close()
        return

    page = await context.new_page()
    log_prefix = f"[G{group_index + 1}|{account_name}]"
    print(f"   👤 {log_prefix} Iniciando '{terms[0]}...' em {day_start}")

    try:
        query = build_x_query(terms=terms, since=day_start, until=day_end)
        url = f"https://x.com/search?q={query}&src=typed_query&f=live"

        await page.goto(url, timeout=60000)
        await page.wait_for_timeout(rv.random_wait())

        # --- VERIFICAÇÃO DE LOGIN (Lógica Invertida e Mais Segura) ---
        try:
            # Verifica se o ícone do perfil (canto inferior esquerdo) está presente
            # Isso confirma que estamos logados com sucesso.
            await page.wait_for_selector("[data-testid='SideNav_AccountSwitcher_Button']", timeout=10000)
        except Exception:
            # Se não achou o perfil, verifica se estamos na URL de login ou se tem o modal de login
            if "login" in page.url or await page.locator("[data-testid='login']").count() > 0:
                print(f"   ⛔ {log_prefix} FALHA REAL DE LOGIN: Redirecionado para login.")
                await page.screenshot(path=f"debug/debug_login_fail_{account_name}.png")
                await context.close()
                return
            else:
                print(f"   ⚠️ {log_prefix} Aviso: Login incerto (Perfil não achado), mas tentando continuar...")

        # --- TRATAMENTO DO BANNER DE AJUDA (CVV) ---
        # Aquele banner gigante empurra o conteúdo. Vamos tentar fechá-lo ou scrollar.
        try:
            # Tenta clicar no botão "x" ou similar se existir, ou apenas dar um scroll inicial
            # O X costuma renderizar tweets apenas quando entram na viewport
            await page.mouse.wheel(0, 500)
            await page.wait_for_timeout(2000)
        except:
            pass
        # ---------------------------------------------

        collected = 0
        scrolls_without_new_data = 0
        last_collected_count = 0
        reloads_done = 0
        MAX_SCROLLS_WITHOUT_DATA = 5

        try:
            print(f"   ⏳ {log_prefix} Aguardando carregamento dos tweets...")
            await page.wait_for_selector("article", timeout=20000)
        except Exception:
            print(f"   ⚠️ {log_prefix} Nenhum tweet visível após 20s. Tentando seguir assim mesmo.")

        while collected < MAX_TWEETS_PER_QUERY:
            tweets = page.locator("article[data-testid='tweet']")
            count = await tweets.count()

            if count == 0:
                scrolls_without_new_data += 1
            else:
                for i in range(count):
                    if collected >= MAX_TWEETS_PER_QUERY: break
                    try:
                        t = tweets.nth(i)

                        link_el = t.locator("a[href*='/status/']").first
                        if not await link_el.count(): continue
                        tweet_url = await link_el.get_attribute("href")
                        tweet_id = tweet_url.split("/")[-1]

                        async with global_lock:
                            if tweet_id in existing_tweet_ids: continue
                            existing_tweet_ids.add(tweet_id)

                        text_loc = t.locator("div[data-testid='tweetText']").first
                        tweet_text = await text_loc.inner_text() if await text_loc.count() else ""
                        if tweet_text: tweet_text = tp.clean_text(tweet_text)

                        time_loc = t.locator("time").first
                        timestamp = await time_loc.get_attribute("datetime") if await time_loc.count() else None
                        timestamp_br = convert_utc_to_brasilia(timestamp)

                        record = {
                            "tweet_id": tweet_id,
                            "text": tweet_text,
                            "timestamp": timestamp_br,
                            "query_group": group_index + 1,
                            "account_used": account_name
                        }

                        await save_tweet(record)
                        collected += 1
                    except Exception:
                        pass

            if collected == last_collected_count:
                scrolls_without_new_data += 1
            else:
                scrolls_without_new_data = 0
                last_collected_count = collected

            if scrolls_without_new_data >= MAX_SCROLLS_WITHOUT_DATA:
                if reloads_done < MAX_RELOADS:
                    print(f"   🔄 {log_prefix} Reloading ({reloads_done + 1}/{MAX_RELOADS})...")
                    try:
                        await page.reload(timeout=60000)
                        await page.wait_for_timeout(4000)
                        scrolls_without_new_data = 0
                        reloads_done += 1
                        continue
                    except:
                        break
                else:
                    print(f"   ⚠️ {log_prefix} Parando: Estagnou.")
                    try:
                        await page.screenshot(path=f"debug/debug_{account_name}_{day_start}.png")
                    except:
                        pass
                    break

            await page.mouse.wheel(0, rv.random_scroll())
            await page.wait_for_timeout(rv.random_wait())

        print(f"   ✅ {log_prefix} Feito: {collected} tweets.")

    except Exception as e:
        print(f"   ❌ {log_prefix} Erro: {e}")
    finally:
        await context.close()

async def scrape():
    MODO_REPARO = True

    DIA_ALVO = (2025, 11, 26)

    GRUPO_ALVO = 2

    account_files = glob.glob(os.path.join(ACCOUNTS_DIR, "*.json"))
    if not account_files:
        print(f"❌ ERRO: Nenhuma conta encontrada na pasta '{ACCOUNTS_DIR}'!")
        print("Rode o script de login primeiro para gerar os arquivos .json")
        return

    print(f"🔎 Usando {len(account_files)} contas: {[os.path.basename(f) for f in account_files]}")

    proxy = random.choice(PROXIES) if PROXIES else None

    async with async_playwright() as p:
        browser = await p.firefox.launch(headless=False, proxy={"server": proxy} if proxy else None)

        start = datetime(*DATA_INICIO)
        end = datetime(*DATA_FINAL)

        if MODO_REPARO:
            print(f"MODO REPARO: Rodando APENAS o Grupo {GRUPO_ALVO} no dia {DIA_ALVO}")
            start = datetime(*DIA_ALVO)
            end = datetime(*DIA_ALVO)  # Começa e termina no mesmo dia

        current = start
        while current <= end:
            day_start = current.strftime("%Y-%m-%d")
            day_end = (current + timedelta(days=1)).strftime("%Y-%m-%d")

            print(f"\n=== Data: {day_start} ===")

            tasks = []
            for idx, terms in enumerate(QUERY_GROUPS):
                group_number = idx + 1

                # --- CORREÇÃO AQUI ---
                if MODO_REPARO and group_number != GRUPO_ALVO:
                    continue  # Pula os grupos que não são o alvo
                # ---------------------
                assigned_account = account_files[idx % len(account_files)]

                task = asyncio.wait_for(
                    scrape_specific_query_with_account(browser, assigned_account, terms, day_start, day_end, idx),
                    timeout=420
                )
                tasks.append(task)

            # Aguarda todos os grupos do dia terminarem
            results = await asyncio.gather(*tasks, return_exceptions=True)

            for res in results:
                if isinstance(res, Exception) and not isinstance(res, asyncio.TimeoutError):
                    print(f" Erro na thread: {res}")

            current += timedelta(days=1)

        await browser.close()
        print("\nFim da coleta.")


if __name__ == "__main__":
    asyncio.run(scrape())