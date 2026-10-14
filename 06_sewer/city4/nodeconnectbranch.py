import pandas as pd

# ノードファイルとブランチファイルのパスを指定（あなたのファイルの場所に置き換えてください）
node_file = 'Nodes_id_plus1.csv'  # ノードファイルのパス
branch_file = 'Branches_with_diameter_id_plus1.csv'  # ブランチファイルのパス

# ノードとブランチデータをDataFrameとして読み込む
node_df = pd.read_csv(node_file)
branch_df = pd.read_csv(branch_file)

# 各ノードの接続情報を保持する辞書を作成
node_connections = {}

# ブランチのDataFrameをループして、開始ノードと終了ノードにブランチIDを追加
for _, row in branch_df.iterrows():
    start_node = row['start_node_id']
    end_node = row['end_node_id']
    branch_id = row['Branches_id']
    
    # 開始ノードと終了ノードにそれぞれ接続されているブランチIDを追加
    if start_node not in node_connections:
        node_connections[start_node] = []
    if end_node not in node_connections:
        node_connections[end_node] = []
        
    node_connections[start_node].append(branch_id)
    node_connections[end_node].append(branch_id)

# connect_r（接続数）とconnect_branch_ids（接続されているブランチID）列を追加
node_df['connect_r'] = node_df['Nodes_id'].apply(lambda x: len(node_connections.get(x, [])))
node_df['connect_branch_ids'] = node_df['Nodes_id'].apply(lambda x: ' '.join(map(lambda y: str(int(y)), node_connections.get(x, []))))

# 結果をCSVファイルに保存
output_file = 'node_with_connections2_re.csv'
node_df.to_csv(output_file, index=False)

print(f'ファイルを作成しました: {output_file}')
