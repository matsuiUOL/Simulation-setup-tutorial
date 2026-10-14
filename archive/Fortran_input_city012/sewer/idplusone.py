import pandas as pd

# ===============================
# 1. Nodes ファイル
# ===============================
nodes_file = "Nodes2.csv"
nodes_out  = "Nodes2_id_plus1.csv"

df_nodes = pd.read_csv(nodes_file)

# +1 する列
node_id_cols = ["Nodes_id"]

for col in node_id_cols:
    df_nodes[col] = df_nodes[col].astype(int) + 1

df_nodes.to_csv(nodes_out, index=False)

print(f"Saved: {nodes_out}")


# ===============================
# 2. Branches ファイル
# ===============================
branches_file = "Branches_with_diameter.csv"
branches_out  = "Branches_with_diameter_id_plus1.csv"

df_br = pd.read_csv(branches_file)

# +1 する列
branch_id_cols = ["Branches_id", "start_node_id", "end_node_id"]

for col in branch_id_cols:
    df_br[col] = df_br[col].astype(int) + 1

df_br.to_csv(branches_out, index=False)

print(f"Saved: {branches_out}")
