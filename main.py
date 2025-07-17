import requests
import re
import networkx as nx
import matplotlib.pyplot as plt


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
transactions = fetch_all_transactions("ERAkXtjhjaFwCnuy8E4oVJvz8mHA7W1wJpMsj1pcjbJF")
processed_txs = pre_process_transaction_list(transactions)
filtered_txns = filter_transactions_by_usd(processed_txs, 100, sol_price=SOL_PRICE)

from pyvis.network import Network


G = nx.MultiDiGraph()

# Create a pyvis Network
net = Network(height='1200px', width='100%', notebook=False, directed=True)

# Optional: for better physics + drag response
net.barnes_hut()

# Add nodes and edges to pyvis
for sender, currency, amount, receiver in filtered_txns:
    usd_value = float(amount) * (170 if currency.lower() == 'sol' else 1)
    label = f"{float(amount):.4f} {currency.upper()})"

    # Add nodes if not already added
    net.add_node(sender, label=sender , title=sender)
    net.add_node(receiver, label=receiver , title=receiver)

    # Add edge with label
    net.add_edge(sender, receiver, label=label, title=label)

# Display the interactive graph
net.write_html("wallet_graph.html", notebook=False, open_browser=True)


#need a good transaction parsing function

#the data structure returned will be something like  [{amount,time},...]
#will pre process the data from each wallet then we will us ethat to build transaction chart.
