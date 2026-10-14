# conduit.dat作成テスト
import math
import csv

# 入力ファイルのパス
branch_file = 'Branches_with_diameter_id_plus1.csv'
manhole_file = 'manhole_bshosei3.dat'  
output_file = 'conduit_bshosei3.dat'  # 出力先を.datファイルに設定

# マンホール情報を辞書に格納する
manhole_data = {}
with open(manhole_file, mode='r') as manhole_dat:
    # ヘッダー行をスキップする
    next(manhole_dat)
    
    for line in manhole_dat:
        fields = line.split()
        # 必要なフィールド数をチェック
        if len(fields) >= 6:  # node_id, inf, ngrp, x_mh, y_mh, bs_mhの6つのフィールドを期待
            try:
                node_id = int(fields[0])
                x_mh = float(fields[3])
                y_mh = float(fields[4])
                bs_mh = float(fields[5])
                manhole_data[node_id] = {
                    'x_mh': x_mh,
                    'y_mh': y_mh,
                    'bs_mh': bs_mh
                }
            except ValueError as e:
                print(f"Error processing line: {line.strip()} - {e}")
        else:
            print(f"Warning: Line skipped due to insufficient data - {line.strip()}")

# ブランチ情報を読み込み、出力ファイルに書き込む
with open(branch_file, mode='r') as branch_csv, open(output_file, mode='w') as output_dat:
    reader = csv.reader(branch_csv)
    
    # ヘッダー行をスキップ
    next(reader)
    ## 追記 ##
    # ヘッダーを除いた行数をカウントします
    iswr = sum(1 for _ in reader)
    
    # ファイルポインタをリセットして再度読み込みます
    branch_csv.seek(0)
    reader = csv.reader(branch_csv)
    next(reader)  # ヘッダーを再度スキップ
    
    # imhの値を出力ファイルに書き込みます
    output_dat.write(f"{iswr}\n")

    ## 追記終わり ##
    # ヘッダーを書き込む
    output_dat.write('branch_id  inf  ngrp  shp  idd1  idd2  rn    slp      bsup     bsdw     mhup  mhdw  ipt  x_sw      y_sw\n')
    
    for row in reader:
        try:
            branch_id = int(row[0])
            mhup_id = int(row[1])
            mhdw_id = int(row[2])
            diameter = int(row[3])
        
            # マンホールの情報を取得
            mhup = manhole_data.get(mhup_id)
            mhdw = manhole_data.get(mhdw_id)
            
            if mhup is None or mhdw is None:
                print(f"Warning: Missing manhole data for branch {branch_id}. Skipping this branch.")
                continue
            
            # 勾配を計算 (slp = (bsup - bsdw) / 距離)
            distance = math.sqrt((mhup['x_mh'] - mhdw['x_mh']) ** 2 + (mhup['y_mh'] - mhdw['y_mh']) ** 2)
            slp = (mhup['bs_mh'] - mhdw['bs_mh']) / distance if distance != 0 else 0
            
            # 出力データを構築
            row_output = [
                branch_id,             # branch_id
                1,                     # inf
                1,                     # ngrp
                2,                     # shp
                diameter,              # idd1
                diameter,              # idd2
                0.013,                 # rn
                slp,                   # slp
                mhup['bs_mh'],         # bsup
                mhdw['bs_mh'],         # bsdw
                mhup_id,               # mhup
                mhdw_id,               # mhdw
                2,                     # ipt
                mhup['x_mh'],          # x_sw (ipt=1 の x座標)
                mhup['y_mh'],          # y_sw (ipt=1 の y座標)
                mhdw['x_mh'],          # x_sw (ipt=2 の x座標)
                mhdw['y_mh']           # y_sw (ipt=2 の x座標)
            ]
            
            
            # 各データを適切な幅でフォーマットし、出力ファイルに書き込み
            output_dat.write(f"{row_output[0]:<10d} {row_output[1]:<4d} {row_output[2]:<4d} {row_output[3]:<4d} "
                             f"{row_output[4]:<4d} {row_output[5]:<4d} {row_output[6]:<5.3f} {row_output[7]:<8.5f} "
                             f"{row_output[8]:<8.2f} {row_output[9]:<8.2f} {row_output[10]:<5d} {row_output[11]:<5d} "
                             f"{row_output[12]:<4d} {row_output[13]:<9.1f} {row_output[14]:<9.1f} {row_output[15]:<9.1f} {row_output[16]:<9.1f}\n")
        except ValueError as e:
            print(f"Error processing row: {row} - {e}")
