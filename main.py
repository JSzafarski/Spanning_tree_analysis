import requests
import re
import networkx as nx
import getBal
KNOWN_WALLETS = [] #for cex'es ect....

#lets first focus on reading the transaction data ( transfers fo usdc.usdt,sol,wsol)
SOL_PRICE = 170

def fetch_all_transactions(wallet_address):
    api_key = "3e1717e1-bf69-45ae-af63-361e43b78961"
    base_url = f"https://api.helius.xyz/v0/addresses/{wallet_address}/transactions?api-key={api_key}"

    url = base_url
    last_signature = None
    all_transactions = []

    while True:
        if last_signature:
            url = f"{base_url}&before={last_signature}"

        response = requests.get(url)

        if not response.ok:
            print(f"API error: {response.status_code}")
            break

        transactions = response.json()

        if transactions and len(transactions) > 0:
            print(f"Fetched batch of {len(transactions)} transactions")
            all_transactions.extend(transactions)
            last_signature = transactions[-1]["signature"]
        else:
            print(f"Finished! Total transactions: {len(all_transactions)}")
            break

    return all_transactions



def parse_transaction(description):
    pattern = re.compile(
        r'(?P<from>\w{32,})\s+transferred\s+(?P<amount>[0-9,]+(?:\.\d+)?)[\s\xa0]+(?P<currency>sol|usdc|usdt)\s+to\s+(?P<to>\w{32,})',
        re.IGNORECASE
    )

    match = pattern.search(description)
    if match:
        groups = match.groupdict()
        amount = groups['amount'].replace(',', '')  # Normalize commas
        return [groups['from'], groups['currency'].lower(), amount, groups['to']]
    return None


def pre_process_transaction_list(tx_list):
    compiled_result = []
    for tx in tx_list:
        if 'transferred' in tx['description'] and 'multiple accounts' not in tx['description']:
            print(tx['description'])
            res = parse_transaction(tx['description'])
            if res is not None:
                compiled_result.append(res)
    return compiled_result

def filter_transactions_by_usd(transactions, min_usd, sol_price=170):
    filtered = []

    for sender, currency, amount_str, receiver in transactions:
        amount = float(amount_str)
        if currency.lower() == 'sol':
            usd_value = amount * sol_price
        elif currency.lower() in {'usdc', 'usdt'}:
            usd_value = amount
        else:
            continue  # Skip unsupported currency
        if usd_value >= min_usd:
            filtered.append([sender, currency.lower(), f"{amount:.8f}", receiver])

    return filtered


# Example usage:
user = "DqqvEiiB73n1zXULMtUpWkFjgKUQ5zEfqBibsgReVoqj"
transactions = fetch_all_transactions(user)
processed_txs = pre_process_transaction_list(transactions)
filtered_txns = filter_transactions_by_usd(processed_txs, 100, sol_price=SOL_PRICE)

from pyvis.network import Network


G = nx.MultiDiGraph()
net = Network(height='1200px', width='100%', notebook=False, directed=True)
net.barnes_hut()

seen_nodes = {}
for sender, currency, amount, receiver in filtered_txns:
    usd_value = float(amount) * (170 if currency.lower() == 'sol' else 1)
    high_val_warning = lambda val: "(HIGH VALUE)" if val > 5000 else ""
    label = f"{float(amount):.2f} {currency.upper()} {high_val_warning(usd_value)}"

    # Custom title with tooltip & click-to-copy JavaScript
    sender_html = f"""
    <b>{sender}</b><br>
    <a href='https://solscan.io/account/{sender}' target='_blank'>View on Solscan</a><br>
    <button onclick="navigator.clipboard.writeText('{sender}')">Copy</button>
    """

    receiver_html = f"""
    <b>{receiver}</b><br>
    <a href='https://solscan.io/account/{receiver}' target='_blank'>View on Solscan</a><br>
    <button onclick="navigator.clipboard.writeText('{receiver}')">Copy</button>
    """
    #label nodes with high sol value ( probably exchange)
    HIGH_BAL = 1000
    if sender not in seen_nodes:
        balance = getBal.get_sol_balance_quicknode(sender)
        seen_nodes[sender] = balance
    if receiver not in seen_nodes:
        balance = getBal.get_sol_balance_quicknode(receiver)
        seen_nodes[receiver] = balance

    # Determine color based on balance
    sender_color = 'red' if seen_nodes[sender] > HIGH_BAL else None
    receiver_color = 'red' if seen_nodes[receiver] > HIGH_BAL else None

    net.add_node(sender, label=sender[:6] + "..." + sender[-4:] + f" {float(seen_nodes[sender]):.2f} SOL", title=sender_html, font={'size': 20},color=sender_color)
    net.add_node(receiver, label=receiver[:6] + "..." + receiver[-4:] + f" {float(seen_nodes[receiver]):.2f} SOL", title=receiver_html, font={'size': 20},color=receiver_color)

    net.add_edge(sender, receiver, label=label, title=label,font={'size': 40})

# Write and open the HTML
net.write_html(f"wallet_graph_{user}.html", notebook=False, open_browser=True)


#need a good transaction parsing function
#the data structure returned will be something like  [{amount,time},...]
#will pre process the data from each wallet then we will us ethat to build transaction chart.


#make a modidifed version where it will automatically check the new wallets and explore to dethp x
#needs to ignore cex wallets and other defi wallets effectively.
#we want to find connections to actual trader
#filer by transfer voluem and counts
#then for each trader maybe comput their pnl and most impressive wins idk?

#needs a comprehenshive db result too  for future analysis
