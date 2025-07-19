

from solana.publickey import PublicKey
from solana.rpc.api import Client
import base58
import base64

client = Client("https://api.mainnet-beta.solana.com")
SNS_PROGRAM_ID = PublicKey("namesLPVzxjrxjZg5wrgK8GvF4r1Zdsa1bCrf")

def get_reverse_account(wallet_address: str):
    seed = b"\x0A" + base58.b58decode(wallet_address)
    reverse_account, _ = PublicKey.find_program_address([seed], SNS_PROGRAM_ID)
    return reverse_account

def reverse_lookup(wallet_address: str):
    reverse_account = get_reverse_account(wallet_address)
    result = client.get_account_info(reverse_account)
    if not result['result']['value']:
        return None

    data = base64.b64decode(result['result']['value']['data'][0])
    name = data[96:].split(b"\x00", 1)[0].decode()
    return name

print(reverse_lookup("9KzbY92H6Q3yU9sEDqxq9kXyX8fpwRmD2AxvHZkEtxGp"))
