import requests
import asyncio
from playwright.async_api import async_playwright
import csv
import os
#need to check sns names too
cex_keywords = ['binance','okx','crypto.com','bybit','coinbase','stake.com',
                'stake','bitmart','mexc','bitget','kraken','exchange','robinhood','backpack','kucoin',
                'gate.io','vault','exchange wallet']

filename = 'cex_addresses.csv'

async def get_solscan_labels(address: str):
    url = f"https://solscan.io/account/{address}"
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)  # or headless=False to watch it work
        page = await browser.new_page()
        await page.goto(url, wait_until='networkidle')

        # Wait for the main info section
        await page.wait_for_selector("div", timeout=10000)

        # Extract Public name
        public_name = None
        try:
            name_element = await page.query_selector("div:has-text('Public name')")
            if name_element:
                wrapper = await name_element.evaluate_handle("node => node.parentElement.parentElement.nextElementSibling")
                if wrapper:
                    name = await wrapper.query_selector("div.font-bold")
                    if name:
                        public_name = (await name.inner_text()).strip()
        except Exception:
            pass

        # Extract tags (e.g. #Coinbase Exchange, #Exchange Wallet)
        tags = []
        try:
            tag_elements = await page.query_selector_all("a[href^='/labelcloud']")
            for tag in tag_elements:
                txt = await tag.inner_text()
                if txt.startswith("#"):
                    tags.append(txt.strip("#"))
        except Exception:
            pass

        await browser.close()
        return tags

def is_cex_related(tags):
    all_texts = tags
    all_texts = [t.lower() for t in all_texts]
    matches = []

    for keyword in cex_keywords:
        keyword = keyword.lower()
        for text in all_texts:
            if keyword in text:
                matches.append(keyword)
                break  # Only record one match per keyword
    if matches:
        print("Likely CEX wallet — matched:", matches)
        return True
    else:
        print("No CEX match — likely private or unknown wallet")
        return False



def analyze_avg_tx_time(wallet_address):
    api_key = "3e1717e1-bf69-45ae-af63-361e43b78961"
    url = f"https://api.helius.xyz/v0/addresses/{wallet_address}/transactions?api-key={api_key}"

    response = requests.get(url)

    if not response.ok:
        print(f"API error: {response.status_code}")
        return False

    transactions = response.json()

    if len(transactions) < 50:
        #print("Not enough transactions to calculate average time.")
        return False

    # Extract and sort timestamps (most recent first)
    timestamps = [tx['timestamp'] for tx in transactions if 'timestamp' in tx]
    timestamps.sort(reverse=True)

    # Calculate time differences
    diffs = [timestamps[i] - timestamps[i + 1] for i in range(len(timestamps) - 1)]
    avg_diff = sum(diffs) / len(diffs)
    if avg_diff<5:
        return True
    return False

def check_for_cex(wallet_address):
    if not os.path.isfile(filename):
        return []
    with open(filename, mode='r') as csvfile:
        reader = csv.reader(csvfile)
        next(reader, None)  # Skip header
        cex_list = [row[0] for row in reader if row]
    if wallet_address in cex_list:
        return True
    result = is_cex_related(asyncio.run(get_solscan_labels(wallet_address)))
    if result:
        file_exists = os.path.isfile(filename)
        with open(filename, mode='a', newline='') as csvfile:
            writer = csv.writer(csvfile)
            if not file_exists:
                writer.writerow(['solana_address'])  # header
            writer.writerow([wallet_address])
    return result

