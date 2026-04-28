import requests
import pandas as pd
from bs4 import BeautifulSoup

url = "https://store.steampowered.com/search/?filter=topsellers"
response = requests.get(url, timeout=20)

print("Status code:", response.status_code)

import requests
import pandas as pd
from bs4 import BeautifulSoup
import time
import os
from datetime import datetime

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
}

rows = []
total = 350
scrape_date = datetime.now().isoformat()

for start in range(0, total, 25):
    url = f"https://store.steampowered.com/search/?filter=topsellers&start={start}"
    response = requests.get(url, headers=headers, timeout=20)
    response.encoding = "utf-8"
    soup = BeautifulSoup(response.text, "html.parser")

    for item in soup.select("a.search_result_row"):
        title_el = item.select_one("span.title")
        title = title_el.get_text(strip=True) if title_el else None

        release_el = item.select_one("div.search_released")
        release = release_el.get_text(strip=True) if release_el else None

        review_el = item.select_one("span.search_review_summary")
        rating = review_el.get("data-tooltip-html", None) if review_el else None
        if rating:
            rating = rating.split("<br>")[0].strip()

        price_el = item.select_one("div.search_price_discount_combined")
        price = None
        if price_el:
            raw = price_el.get("data-price-final")
            if raw:
                price = int(raw) / 100

        platforms = [span.get("class", [""])[1] for span in item.select("span.platform_img")]
        platform = ", ".join(platforms) if platforms else None

        rows.append({
            "title":    title,
            "platform": platform,
            "price":    price,
            "rating":   rating,
            "release":  release,
            "scrape_date": scrape_date,
        })

    time.sleep(1)

df = pd.DataFrame(rows)
df = df.drop_duplicates(subset=["title"])
df

df["rating"] = df["rating"].fillna("Unknown")
df["release"] = df["release"].fillna("Unknown")
df["price"] = df["price"].fillna(0)

print(df.isnull().sum())
print(df.dtypes)


df["price_tier"] = df["price"].apply(
    lambda p: "Free" if p == 0
    else ("Budget" if p < 20
    else ("Mid-range" if p < 40 else "Premium"))
)

filename = "steam_history.csv"

if os.path.exists(filename):
    df.to_csv(filename, mode="a", header=False, index=False)
else:
    df.to_csv(filename, index=False)


from supabase import create_client
from datetime import datetime



import os

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_KEY"]

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

scrape_time = datetime.now().isoformat()

rows = []
for _, row in df.iterrows():
    rows.append({
        "title":    str(row.get("title", "")),
        "platform": str(row.get("platform", "")),
        "price":    float(row.get("price", 0)),
        "rating":   str(row.get("rating", "")),
        "release":  str(row.get("release", "")),
        "price_tier": str(row.get("price_tier", "")),
        "scrape_date": str(row.get("scrape_date", "")),
    })

result = supabase.table("games").insert(rows).execute()
print(f"✅ Inserted {len(rows)} rows into Supabase")

avg_price = df["price"].mean()

if avg_price < 20:
    print(f"ALERT: Average price dropped below 20 ({avg_price:.2f})")

if os.path.exists("steam_history.csv"):
    historical = pd.read_csv("steam_history.csv")

    if "scrape_date" in historical.columns:
        prev_runs = historical.groupby("scrape_date")["price"].mean()

        if len(prev_runs) > 1:
            prev_avg = prev_runs.iloc[-2]
            change_pct = ((avg_price - prev_avg) / prev_avg) * 100

            if abs(change_pct) > 10:
                print(f"ALERT: Price swing detected {change_pct:+.1f}%")