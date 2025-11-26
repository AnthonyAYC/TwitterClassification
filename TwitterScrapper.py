import asyncio
import json
import os
import csv
import re
import random
from playwright.async_api import async_playwright
from datetime import datetime, timezone, timedelta


MAX_TWEETS = 30
AUTH_FILE = "auth.json"
SEARCH_QUERY = "(suicídio OR triste) lang:pt"
OUTPUT_FILE = "tweets.csv"

# --- Carregar tweets existentes ---
existing_tweet_ids = set()
results = []

file_exists = os.path.exists(OUTPUT_FILE)

if file_exists:
    with open(OUTPUT_FILE, "r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            results.append(row)
            existing_tweet_ids.add(row["tweet_id"])

# Opcional: proxies
PROXIES = [

]

def convert_utc_to_brasilia(utc_str):
    if not utc_str:
        return None
    # Parse do string ISO 8601
    dt_utc = datetime.fromisoformat(utc_str.replace("Z", "+00:00"))
    # Fuso horário de Brasília: UTC-3
    brasilia_tz = timezone(timedelta(hours=-3))
    dt_brasilia = dt_utc.astimezone(brasilia_tz)
    return dt_brasilia.strftime("%Y-%m-%d %H:%M:%S")

def random_wait(a=800, b=1800):
    return random.randint(a, b)


def random_scroll():
    return random.randint(1800, 3500)


def get_random_user_agent():
    uas = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/121.0 Safari/537.36",
        "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:123.0) Gecko/20100101 Firefox/123.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15) AppleWebKit/605.1.15 Version/17.0 Safari/605.1.15",
    ]
    return random.choice(uas)


def get_random_viewport():
    return {
        "width": random.randint(1100, 1600),
        "height": random.randint(700, 1000)
    }


async def load_cookies(context):
    try:
        with open(AUTH_FILE, "r", encoding="utf-8") as f:
            cookies = json.load(f)
        await context.add_cookies(cookies)
        print("Cookies carregados de auth.json.")
    except Exception as e:
        print("Erro ao carregar auth.json:", e)
        exit()


async def scrape():
    proxy = random.choice(PROXIES) if PROXIES else None

    async with async_playwright() as p:
        browser = await p.firefox.launch(
            headless=False,
            proxy={"server": proxy} if proxy else None
        )

        context = await browser.new_context(
            user_agent=get_random_user_agent(),
            viewport=get_random_viewport()
        )

        await load_cookies(context)

        page = await context.new_page()

        url = f"https://x.com/search?q={SEARCH_QUERY}&src=typed_query&f=live"
        await page.goto(url)
        await page.wait_for_timeout(random_wait())

        print("🔍 Coletando tweets...")

        collected_this_run = set()

        while len(collected_this_run) < MAX_TWEETS:

            # ⛔ Se não achar tweets, aviso
            tweets = page.locator("article:has(div[data-testid='User-Name'])")
            count = await tweets.count()

            # ⬇️ Iterar nos tweets
            for i in range(count):

                if len(collected_this_run) >= MAX_TWEETS:
                    break

                t = tweets.nth(i)

                try:
                    # Username
                    tweet_id = await t.locator("a[href*='/status/']").first.get_attribute("href")
                    tweet_id = tweet_id.split("/")[-1] if tweet_id else None

                    # Texto
                    text_loc = t.locator("div[data-testid='tweetText']")
                    tweet_text = await text_loc.first.inner_text() if await text_loc.count() > 0 else None
                    if tweet_text:
                        tweet_text = re.sub(r'\s+', ' ', tweet_text).strip()

                    # Timestamp
                    timestamp = await t.locator("time").first.get_attribute("datetime")
                    timestamp_br = convert_utc_to_brasilia(timestamp)

                    # ID único
                    key = tweet_id
                    if key in existing_tweet_ids or not tweet_id:
                        continue

                    # Abrir perfil para obter localização
                    location = None
                    try:
                        tooltip_locator = t.locator("div[data-testid='HoverCard'], span[data-testid='UserLocation']")
                        if await tooltip_locator.count() > 0:
                            location = await tooltip_locator.inner_text()
                        else:
                            location = None
                    except:
                        location = None

                    existing_tweet_ids.add(key)
                    collected_this_run.add(key)
                    results.append({
                        "tweet_id": tweet_id,
                        "text": tweet_text,
                        "timestamp": timestamp_br,
                        "location": location
                    })

                    print(f"\n📌 Tweet coletado ({len(collected_this_run)}/{MAX_TWEETS}):")
                    print(f"ID {tweet_id}")
                    print(f"🕒 {timestamp_br}")
                    print(f"📍 {location}")
                    print(f"💬 {tweet_text}\n")

                except Exception as e:
                    print("Erro ao processar tweet:", e)

            # anti-bloqueio: scroll aleatório
            await page.mouse.wheel(0, random_scroll())
            await page.wait_for_timeout(random_wait())
        await browser.close()
        # salvar CSV
        with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["tweet_id", "text", "timestamp", "location"])
            writer.writeheader()
            writer.writerows(results)

        print(f"\n📁 Concluído! {len(results)} tweets salvos em {OUTPUT_FILE}")

asyncio.run(scrape())
