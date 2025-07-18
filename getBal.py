import requests
import json

endpoint = "https://dimensional-few-breeze.solana-mainnet.quiknode.pro/263c9938190e8f9d6c70bb5cbf43a4d2508cd795/"

def get_sol_balance_quicknode(pubkey: str, endpoint_url = endpoint) -> float:
    """
    Fetches the SOL balance of a wallet using QuickNode's Solana RPC endpoint.

    Args:
        pubkey (str): The Solana wallet public key.
        endpoint_url (str): The full QuickNode RPC endpoint URL.

    Returns:
        float: The wallet balance in SOL.
    """
    headers = {
        "Content-Type": "application/json"
    }

    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "getBalance",
        "params": [pubkey]
    }

    try:
        response = requests.post(endpoint_url, headers=headers, data=json.dumps(payload))
        response.raise_for_status()  # Raise an error for bad status codes

        result = response.json()
        lamports = result['result']['value']
        return lamports / 1_000_000_000  # Convert lamports to SOL

    except Exception as e:
        print(f"Error fetching balance: {e}")
        return -1  # You can handle this differently if needed


