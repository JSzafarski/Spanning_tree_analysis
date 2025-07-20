import requests

def analyze_avg_tx_time(wallet_address):
    api_key = "3e1717e1-bf69-45ae-af63-361e43b78961"
    url = f"https://api.helius.xyz/v0/addresses/{wallet_address}/transactions?api-key={api_key}"

    response = requests.get(url)

    if not response.ok:
        print(f"API error: {response.status_code}")
        return False

    transactions = response.json()

    if len(transactions) < 50:
        print("Not enough transactions to calculate average time.")
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

