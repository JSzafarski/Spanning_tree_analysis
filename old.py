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