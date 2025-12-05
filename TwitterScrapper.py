import asyncio
import json
import os
import csv
import random
import TextProcessing as tp
import RandomValues as rv
from playwright.async_api import async_playwright
from datetime import datetime, timezone, timedelta
from urllib.parse import quote


MAX_TWEETS = 50
AUTH_FILE = "auth.json"
SEARCH_QUERY = '("suicida" OR "suicídio" OR "me matar" OR "meu bilhete suicida" OR "minha carta suicida" OR "ir dormir pra sempre")'
OUTPUT_FILE = "csv_files/tweets.csv"

# Carregar tweets existentes
existing_tweet_ids = set()
results = []

file_exists = os.path.exists(OUTPUT_FILE)

if file_exists:
    with open(OUTPUT_FILE, "r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            results.append(row)
            existing_tweet_ids.add(row["tweet_id"])

# proxies
PROXIES = []

def convert_utc_to_brasilia(utc_str):
    if not utc_str:
        return None
    # Parse do string ISO 8601
    dt_utc = datetime.fromisoformat(utc_str.replace("Z", "+00:00"))
    # Fuso horário de Brasília: UTC-3
    brasilia_tz = timezone(timedelta(hours=-3))
    dt_brasilia = dt_utc.astimezone(brasilia_tz)
    return dt_brasilia.strftime("%Y-%m-%d %H:%M:%S")

async def load_cookies(context):
    try:
        with open(AUTH_FILE, "r", encoding="utf-8") as f:
            cookies = json.load(f)
        await context.add_cookies(cookies)
        print("Cookies carregados de auth.json.")
    except Exception as e:
        print("Erro ao carregar auth.json:", e)
        exit()


def build_x_query(terms,since=None,until=None, lang="pt"):

    query = "(" + " OR ".join([f'"{t}"' for t in terms]) + ")"

    if since:
        query += f" since:{since}"
    if until:
        query += f" until:{until}"
    if lang:
        query += f" lang:{lang}"
    # codifica para URL
    return quote(query)

async def scrape_day(page, day_start, day_end):

    query = build_x_query(terms=[
        "suicida", "suicídio", "me matar",
        "meu bilhete suicida", "minha carta suicida",
        "ir dormir pra sempre"],
        since = day_start,
        until = day_end
    )

    url = f"https://x.com/search?q={query}&src=typed_query&f=live"

    await page.goto(url)
    await page.wait_for_timeout(rv.random_wait())

    collected_today = 0

    while collected_today < MAX_TWEETS:

        tweets = page.locator("article:has(div[data-testid='User-Name'])")
        count = await tweets.count()

        for i in range(count):

            if collected_today >= MAX_TWEETS:
                break

            t = tweets.nth(i)

            try:
                tweet_id = await t.locator("a[href*='/status/']").first.get_attribute("href")
                tweet_id = tweet_id.split("/")[-1] if tweet_id else None

                text_loc = t.locator("div[data-testid='tweetText']")
                tweet_text = await text_loc.first.inner_text() if await text_loc.count() > 0 else None
                if tweet_text:
                    tweet_text = tp.clean_text(tweet_text)

                timestamp = await t.locator("time").first.get_attribute("datetime")
                timestamp_br = convert_utc_to_brasilia(timestamp)

                if not tweet_id or tweet_id in existing_tweet_ids:
                    continue

                try:
                    tooltip_locator = t.locator("div[data-testid='HoverCard'], span[data-testid='UserLocation']")
                    location = await tooltip_locator.inner_text() if await tooltip_locator.count() > 0 else None
                except:
                    location = None

                existing_tweet_ids.add(tweet_id)
                results.append({
                    "tweet_id": tweet_id,
                    "text": tweet_text,
                    "timestamp": timestamp_br,
                    "location": location
                })

                collected_today += 1

                print(f"\n📌 ({collected_today}/{MAX_TWEETS}) - {day_start}")
                print(f"ID: {tweet_id}")
                print(f"Data: {timestamp_br}")
                print(f"Loc: {location}")
                print(f"Tweet: {tweet_text}\n")

            except Exception as e:
                print("Erro ao processar tweet:", e)

        await page.mouse.wheel(0, rv.random_scroll())
        await page.wait_for_timeout(rv.random_wait())

    print(f"✔️ Dia {day_start} completo ({collected_today} tweets).")

async def scrape():
    proxy = random.choice(PROXIES) if PROXIES else None

    async with async_playwright() as p:
        browser = await p.firefox.launch(
            headless=False,
            proxy={"server": proxy} if proxy else None
        )

        context = await browser.new_context(
            user_agent=rv.get_random_user_agent(),
            viewport=rv.get_random_viewport()
        )

        await load_cookies(context)
        page = await context.new_page()

        # Loop de dias
        start = datetime(2025, 11, 1)
        end = datetime(2025, 11, 5)

        current = start

        while current <= end:
            day_start = current.strftime("%Y-%m-%d")
            day_end   = (current + timedelta(days=1)).strftime("%Y-%m-%d")

            print(f"\n=============================")
            print(f"📅 Coletando dia {day_start}")
            print(f"=============================\n")

            await scrape_day(page, day_start, day_end)

            current += timedelta(days=1)

        await browser.close()

        # salvar CSV
        with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["tweet_id", "text", "timestamp", "location"])
            writer.writeheader()
            writer.writerows(results)

        print(f"\n💾 {len(results)} tweets salvos em {OUTPUT_FILE}")


asyncio.run(scrape())
