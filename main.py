import requests
import re
import networkx as nx
import getBal
from pyvis.network import Network
from collections import defaultdict
from cex_checker import check_for_cex
#lets first focus on reading the transaction data (transfers fo usdc.usdt,sol,wsol)
SOL_PRICE = 170
# I will be adding the ability to automatically build a spanning tree of all associated wallets based on th params i setout
#for now I will decide the end criteria to be at most max number of seen nodes eg9 max 50 )
visited_nodes = set() # set since each wallet needs to be unique

class NodeStack:
    def __init__(self):
        self.stack = []

    def push(self, item: str):
        if isinstance(item, str):
            self.stack.append(item)
        else:
            raise ValueError("non string type")

    def pop(self):
        if self.stack:
            return self.stack.pop()
        return None #if enmpty

    def size(self):
        return len(self.stack)

    def __repr__(self):
        return f"StringStack({self.stack})"

    def __str__(self):
        if not self.stack:
            return "[empty stack]"
        lines = [f"{i}: {val}" for i, val in enumerate(reversed(self.stack))]
        return "Top\n" + "\n".join(lines)

wallet_stack = NodeStack() # creating a stack object

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
            #print(tx['description'])
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


first_node = "9VxJw5ngvTfv3SkBZnfn2bMk8H29QXMgA6MfGtuHkZhx"

#here we append the starting node to the stack

wallet_stack.push(first_node)

#transactions = fetch_all_transactions(user)
#processed_txs = pre_process_transaction_list(transactions)
#filtered_txns = filter_transactions_by_usd(processed_txs, 50, sol_price=SOL_PRICE)

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
seen_wallet_cache = [] #i can use seen nodes but i rather decouple this for now
cex_wallets = []
MAX_SEEN_NODES = 50
while True:
    if wallet_stack.size() == 0 or len(visited_nodes) >= MAX_SEEN_NODES:
        break # ending the traversal
    print(wallet_stack)
    current_node = wallet_stack.pop()
    sol_balance = getBal.get_sol_balance_quicknode(current_node)
    print(f"{sol_balance} SOL in {current_node}")
    if current_node in cex_wallets or sol_balance > 1000: #for now we assume cex >1000
        print(f'omitted {current_node} since it is likely a cex wallet')
        continue # we will ommit it ( since its a cex)
    print(f"current node: {current_node}")
    visited_nodes.add(current_node)
    transactions = fetch_all_transactions(current_node) # dont need to consider None value since above handles this anyway
    processed_txs = pre_process_transaction_list(transactions)
    filtered_txns = filter_transactions_by_usd(processed_txs, 50, sol_price=SOL_PRICE)

    for sender, currency, amount, receiver in filtered_txns:
        #need to make sure the wallet of question is in the receiver or sender side
        if sender == current_node or receiver == current_node:
            if sender not in visited_nodes:
                visited_nodes.add(sender)
                wallet_stack.push(sender)
            if receiver not in visited_nodes:
                visited_nodes.add(receiver)
                wallet_stack.push(receiver)

            usd_value = float(amount) * (SOL_PRICE if currency.lower() == 'sol' else 1)
            node_a, node_b = sorted([sender, receiver])  # always same order

            if sender not in seen_wallet_cache: #this is to help label cex wallets
                check = check_for_cex(sender)
                seen_wallet_cache.append(sender)
                if check:
                    cex_wallets.append(sender)
            if receiver not in seen_wallet_cache:
                check = check_for_cex(receiver)
                seen_wallet_cache.append(receiver)
                if check:
                    cex_wallets.append(receiver)

            if sender < receiver and sender not in cex_wallets and receiver not in cex_wallets:
                edge_data[(node_a, node_b)]["from_to_usd"] += usd_value
                edge_data[(node_a, node_b)]["from_to_count"] += 1
            else:
                edge_data[(node_a, node_b)]["to_from_usd"] += usd_value
                edge_data[(node_a, node_b)]["to_from_count"] += 1

# Step 1: Aggregate transfers between nodes
for (node1, node2), values in edge_data.items():
    # Skip edge if both directions are below threshold
    if values["from_to_count"] < MIN_TX_COUNT and values["to_from_count"] < MIN_TX_COUNT: #change to or later ( testing now )
        #also consider low bal transactions
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
        <a href='https://gmgn.ai/sol/address/{node}' target='_blank'>View on GMGN.ai</a><br>
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
html_file = f"wallet_graph_{first_node}.html"
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
#will pre-process the data from each wallet then we will us that to build transaction chart.
#make a modified version where it will automatically check the new wallets and explore to depth x
#needs to ignore cex wallets and other defi wallets effectively.
#we want to find connections to actual trader
#filer by transfer volume and counts
#then for each trader maybe compute their pnl and most impressive wins idk?
#needs a comprehensive db result too  for future analysis
