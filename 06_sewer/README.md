# 06 下水道データの作成（Python）

QGIS から書き出した下水道ノード・管路の CSV から、解析モデル用の
**マンホールデータ `manhole_bshosei.dat`** と **管渠データ `conduit_bshosei.dat`** を作ります。

## フォルダ

```
06_sewer/city4/                         ← 作業フォルダ（ここで実行する）
├── Nodes.csv                           ← 入力（03 で書き出し）
├── Branches_with_diameter.csv          ← 入力（03 で書き出し）
├── *.qmd                               ← QGIS のメタデータ（無くてもよい）
├── idplusone.py                        ← ① ID を 1 始まりに
├── nodeconnectbranch.py                ← ② ノードに接続管路を付与
├── makemanhole.py                      ← ③ マンホールデータ
├── makeconduit.py                      ← ④ 管渠データ
└── （以下は出力例）
    Nodes_id_plus1.csv, Branches_with_diameter_id_plus1.csv,
    node_with_connections2_re.csv, manhole_bshosei.dat, conduit_bshosei.dat
```

## 実行方法

```bash
cd 06_sewer/city4
python idplusone.py
python nodeconnectbranch.py
#   ↓ ここで node_with_connections2_re.csv の z 列（管底高）を確認・修正（下記）
python makemanhole.py
python makeconduit.py
```

## 処理の流れと入出力

| 順 | スクリプト | 入力 | 出力 | 内容 |
|---|---|---|---|---|
| ① | `idplusone.py` | `Nodes.csv`, `Branches_with_diameter.csv` | `Nodes_id_plus1.csv`, `Branches_with_diameter_id_plus1.csv` | QGIS の 0 始まり ID を Fortran 用に 1 始まりにする |
| ② | `nodeconnectbranch.py` | ①の 2 ファイル | `node_with_connections2_re.csv` | 各ノードに接続する管路の数（`connect_r`）と ID 一覧を追加 |
| ③ | `makemanhole.py` | `node_with_connections2_re.csv` | `manhole_bshosei.dat` | マンホールデータを固定書式で出力 |
| ④ | `makeconduit.py` | `Branches_with_diameter_id_plus1.csv`, `manhole_bshosei.dat` | `conduit_bshosei.dat` | 両端マンホールの高さから勾配を計算し管渠データを出力 |

## 標高 z について
`makemanhole.py` は CSV の `z` 列をそのままマンホール底高 `bs_mh` として使います。
city4 の例では、`Nodes.csv` では z = 0（地表）ですが、`node_with_connections2_re.csv` では **z = −2.5 m** に書き換えてあります（地表から 2.5 m 下に管を埋設した想定）。
② と ③ の間で、Excel などで z 列を設定してください。

## 出力の書式

**`manhole_bshosei.dat`**
```
138                                     ← マンホール数
     id     inf    ngrp        x_mh        y_mh      bs_mh       area        num    isw_mh
       1       1       1    152500.0    502500.0     -2.500        1.0          2        1     109
```
`num` = 接続管路数、`isw_mh` = 接続管路の ID（`num` 個）。`inf`, `ngrp`, `area` は固定値（1, 1, 1.0）。

**`conduit_bshosei.dat`**
```
235                                     ← 管路数
branch_id  inf  ngrp  shp  idd1  idd2  rn    slp      bsup     bsdw     mhup  mhdw  ipt  x_sw ...
1          1    1    2    800  800  0.013 0.00000  -2.50    -2.50    1     2     2    152500.0  502500.0  152500.0  502700.0
```
`idd1, idd2` = 管径 [mm]、`rn` = マニングの粗度係数、`slp` = 勾配、`bsup/bsdw` = 上下流端の管底高、`mhup/mhdw` = 上下流のマンホール番号。

## 次の段階へ
`manhole_bshosei.dat`, `conduit_bshosei.dat` → 07（河川への排水接続）と 08（最終入力）で使います。

## ⚠ 要確認
- `shp`（断面形状コード、例では 2）や `ipt` の意味は解析本体のソースで確認してください。
- city012 用の同じスクリプトと出力は `archive/Fortran_input_city012/sewer/` にあります。
