import requests
import re
import networkx as nx
import getBal
from pyvis.network import Network
from collections import defaultdict
from cex_checker import analyze_avg_tx_time


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



user = "BobpBzS3joQtbpY8VRycnFguHwxHLD7hRwguBe4dDCsk"
transactions = fetch_all_transactions(user)
processed_txs = pre_process_transaction_list(transactions)
filtered_txns = filter_transactions_by_usd(processed_txs, 100, sol_price=SOL_PRICE)



'''G = nx.MultiDiGraph()
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
    <button onclick="navigator.clipboard.writeText('{sender}')">Copy</button><br>
    <button onclick="hideNode('{sender}')">❌ Hide</button>
    """

    receiver_html = f"""
    <b>{receiver}</b><br>
    <a href='https://solscan.io/account/{receiver}' target='_blank'>View on Solscan</a><br>
    <button onclick="navigator.clipboard.writeText('{receiver}')">Copy</button><br>
    <button onclick="hideNode('{receiver}')">❌ Hide</button>
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
html_file = f"wallet_graph_{user}.html"
net.write_html(html_file, notebook=False, open_browser=True)
with open(html_file, 'r', encoding='utf-8') as f:
    html = f.read()

# JavaScript to hide a node and its edges
inject_script = """
<script>
function hideNode(nodeId) {
    var network = window.network;
    if (!network) return;

    var updateArray = [];
    var connectedEdges = network.getConnectedEdges(nodeId);

    // Hide node
    updateArray.push({id: nodeId, hidden: true});

    // Optionally hide edges too
    connectedEdges.forEach(function(edgeId) {
        updateArray.push({id: edgeId, hidden: true});
    });

    network.body.data.nodes.update(updateArray.filter(obj => obj.id in network.body.nodes || obj.id in network.body.edges));
}
</script>
"""

# Insert the script before </body>
html = html.replace("</body>", inject_script + "\n</body>")

# Save updated HTML
with open(html_file, 'w', encoding='utf-8') as f:
    f.write(html)'''


G = nx.Graph()
net = Network(height='1200px', width='100%', notebook=False, directed=False)
net.barnes_hut()


# Aggregation map
edge_data = defaultdict(lambda: {
    "from_to_usd": 0.0,
    "to_from_usd": 0.0,
    "from_to_count": 0,
    "to_from_count": 0
})

seen_nodes = {}
HIGH_BAL = 1000
MIN_TX_COUNT = 1  # only show edge if in or out count >= this
seen_wallet_cache = []
cex_wallets = []
for sender, currency, amount, receiver in filtered_txns:
    usd_value = float(amount) * (SOL_PRICE if currency.lower() == 'sol' else 1)
    node_a, node_b = sorted([sender, receiver])  # always same order

    if sender not in seen_wallet_cache: #this is to help label cex wallets
        check = analyze_avg_tx_time(sender)
        seen_wallet_cache.append(sender)
        if check:
            cex_wallets.append(sender)
    if receiver not in seen_wallet_cache:
        check = analyze_avg_tx_time(receiver)
        seen_wallet_cache.append(receiver)
        if check:
            cex_wallets.append(receiver)

    if sender < receiver:
        edge_data[(node_a, node_b)]["from_to_usd"] += usd_value
        edge_data[(node_a, node_b)]["from_to_count"] += 1
    else:
        edge_data[(node_a, node_b)]["to_from_usd"] += usd_value
        edge_data[(node_a, node_b)]["to_from_count"] += 1

# Step 1: Aggregate transfers between nodes
for (node1, node2), values in edge_data.items():
    # Skip edge if both directions are below threshold
    if values["from_to_count"] < MIN_TX_COUNT or values["to_from_count"] < MIN_TX_COUNT:
        continue

    # Cache balances
    for node in [node1, node2]:
        if node not in seen_nodes:
            seen_nodes[node] = getBal.get_sol_balance_quicknode(node)
    cex_flag = ''
    if node in cex_wallets:
        cex_flag = "(CEX likely)"
    def node_html(node):
        return f"""
        <b>{node} {cex_flag}</b><br>
        <a href='https://solscan.io/account/{node}' target='_blank'>View on Solscan</a><br>
        <button onclick="navigator.clipboard.writeText('{node}')">Copy</button><br>
        <button onclick="hideNode('{node}')">❌ Hide</button>
        """

    for node in [node1, node2]:
        net.add_node(
            node,
            label=f"{node[:6]}...{node[-4:]} {seen_nodes[node]:.2f} SOL",
            title=node_html(node),
            font={'size': 20},
            color='red' if seen_nodes[node] > HIGH_BAL else None
        )

    # Get values
    out_val = values["from_to_usd"]
    in_val = values["to_from_usd"]
    out_count = values["from_to_count"]
    in_count = values["to_from_count"]
    total_val = out_val + in_val

    # New label with tx count
    edge_label = f"→ ${out_val:.2f} ({out_count}) | ← ${in_val:.2f} ({in_count})"
    edge_width = min(12, max(1, total_val / 1000))

    net.add_edge(
        node1,
        node2,
        label=edge_label,
        title=edge_label,
        width=edge_width
    )

# Step 3: Save and open HTML
user = "wallet_user"
html_file = f"wallet_graph_{user}.html"
net.write_html(html_file, notebook=False, open_browser=True)

# Inject JS for hideNode()
with open(html_file, 'r', encoding='utf-8') as f:
    html = f.read()

inject_script = """
<script>
function hideNode(nodeId) {
    var network = window.network;
    if (!network) return;

    var updateArray = [];
    var connectedEdges = network.getConnectedEdges(nodeId);
    updateArray.push({id: nodeId, hidden: true});
    connectedEdges.forEach(function(edgeId) {
        updateArray.push({id: edgeId, hidden: true});
    });

    network.body.data.nodes.update(updateArray.filter(obj => obj.id in network.body.nodes || obj.id in network.body.edges));
}
</script>
"""

html = html.replace("</body>", inject_script + "\n</body>")

with open(html_file, 'w', encoding='utf-8') as f:
    f.write(html)

#need a good transaction parsing function
#the data structure returned will be something like  [{amount,time},...]
#will pre process the data from each wallet then we will us ethat to build transaction chart.


#make a modidifed version where it will automatically check the new wallets and explore to dethp x
#needs to ignore cex wallets and other defi wallets effectively.
#we want to find connections to actual trader
#filer by transfer voluem and counts
#then for each trader maybe comput their pnl and most impressive wins idk?

#needs a comprehenshive db result too  for future analysis
