import csv

# 入力ファイルと出力ファイルのパス
input_file = 'node_with_connections2_re.csv'
output_file = 'manhole_bshosei3.dat'  # .txtではなく.datとして保存

# 入力ファイルを開き、データを読み取ります
with open(input_file, mode='r') as infile, open(output_file, mode='w') as outfile:
    reader = csv.reader(infile)
    
    # ヘッダーを読み飛ばします
    header = next(reader)
    
    # ヘッダーを除いた行数をカウントします
    imh = sum(1 for _ in reader)
    
    # ファイルポインタをリセットして再度読み込みます
    infile.seek(0)
    reader = csv.reader(infile)
    next(reader)  # ヘッダーを再度スキップ
    
    # imhの値を出力ファイルに書き込みます
    outfile.write(f"{imh}\n")
    
    # 出力ファイルにヘッダーを書き込みます
    outfile.write('     id     inf    ngrp        x_mh        y_mh      bs_mh       area        num    isw_mh\n')
    
    # 各行を処理し、出力ファイルに書き込みます
    for row in reader:
        # 各フィールドを適切なデータ型に変換します
        id_val = int(row[0])
        x_mh_val = float(row[1])
        y_mh_val = float(row[2])
        z_mh_val = float(row[3]) 
        num_val = int(row[4])
        
        # isw_mhフィールドをスペースで分割し、空の要素を除去
        isw_mh_vals = [int(val) for val in row[5].split(' ') if val]  # 空文字列を除去してからintに変換
        
        # 固定値の設定
        inf_val = 1
        ngrp_val = 1
        area_val = 1.0
        
        # フォーマットして出力ファイルに書き込みます
        isw_mh_formatted = f"{id_val:8d} {inf_val:7d} {ngrp_val:7d} {x_mh_val:11.1f} {y_mh_val:11.1f} {z_mh_val:10.3f} {area_val:10.1f} {num_val:10d}"
        isw_mh_str = ''.join(f"{val:8d}" for val in isw_mh_vals)
        
        # 出力ファイルに書き込みます
        outfile.write(f"{isw_mh_formatted} {isw_mh_str}\n")
