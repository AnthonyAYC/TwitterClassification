import asyncio
import json
import csv
from playwright.async_api import async_playwright

MAX_TWEETS = 10        # <<--- defina quantos tweets quer coletar
AUTH_FILE = "auth.json"
SEARCH_QUERY = "suicídio lang:pt"
OUTPUT_FILE = "tweets.csv"

async def load_cookies(context):
    """Carrega cookies salvos em auth.json"""
    try:
        with open(AUTH_FILE, "r", encoding="utf-8") as f:
            cookies = json.load(f)
        await context.add_cookies(cookies)
        print("Cookies carregados de auth.json.")
    except Exception as e:
        print("Erro ao carregar auth.json:", e)
        print("⚠️ Você precisa exportar cookies do navegador (Chrome/Firefox).")
        exit()

async def scrape():
    async with async_playwright() as p:
        browser = await p.firefox.launch(headless=False)
        context = await browser.new_context()

        await load_cookies(context)

        page = await context.new_page()

        url = f"https://x.com/search?q={SEARCH_QUERY}&src=typed_query&f=live"
        await page.goto(url)
        await page.wait_for_timeout(5000)

        print("🔍 Procurando tweets na página...")

        results = []
        collected = set()

        while len(results) < MAX_TWEETS:

            # ⛔ Se não achar tweets, aviso
            tweets = page.locator("article[data-testid='tweet']")
            count = await tweets.count()

            print(f"➡️ Tweets detectados no DOM: {count}")

            if count == 0:
                print("⚠️ Nenhum tweet encontrado! Pode ser:")
                print("- Login falhou")
                print("- Página do X não carregou corretamente")
                print("- Bloqueio temporário")
                print("- Seletor mudou")
                await page.wait_for_timeout(3000)
                continue

            # ⬇️ Iterar nos tweets
            for i in range(count):

                if len(results) >= MAX_TWEETS:
                    break

                t = tweets.nth(i)

                try:
                    # Username
                    user_el = t.locator("div[data-testid='User-Name'] a").first
                    username = await user_el.get_attribute("href")
                    if username:
                        username = username.replace("/", "")

                    # Texto
                    text_el = t.locator("div[data-testid='tweetText']")
                    tweet_text = await text_el.inner_text() if await text_el.count() > 0 else ""

                    # Timestamp
                    time_el = t.locator("time")
                    timestamp = await time_el.get_attribute("datetime") if await time_el.count() > 0 else None

                    # ID único
                    key = (username, timestamp)
                    if key in collected:
                        continue

                    # Abrir perfil para obter localização
                    location = None
                    if username:
                        profile_page = await context.new_page()
                        await profile_page.goto(f"https://x.com/{username}")
                        await profile_page.wait_for_timeout(2000)

                        loc_el = profile_page.locator("span[data-testid='UserLocation']")
                        if await loc_el.count() > 0:
                            location = await loc_el.inner_text()

                        await profile_page.close()

                    collected.add(key)
                    results.append({
                        "username": username,
                        "text": tweet_text,
                        "timestamp": timestamp,
                        "location": location
                    })

                    print(f"\n📌 Tweet coletado ({len(results)}/{MAX_TWEETS}):")
                    print(f"👤 @{username}")
                    print(f"🕒 {timestamp}")
                    print(f"📍 {location}")
                    print(f"💬 {tweet_text}\n")

                except Exception as e:
                    print("Erro ao processar tweet:", e)

            # Scroll forte para carregar mais
            await page.mouse.wheel(0, 6000)
            await page.wait_for_timeout(2500)

        # Salvar CSV
        with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["username", "text", "timestamp", "location"])
            writer.writeheader()
            writer.writerows(results)

        print(f"\n🎉 Concluído! {len(results)} tweets salvos em {OUTPUT_FILE}")
        await browser.close()


asyncio.run(scrape())
