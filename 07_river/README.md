# 07 河川データの作成（Python）

1 次元河道モデルの入力（断面・河道形状・境界条件・初期条件）と、
河道と **2 次元氾濫原** ・ **下水道** との接続データを作ります。

## フォルダ

```
07_river/city4/      ← 作業フォルダ（ここで実行する。スクリプト・入力・出力例がすべて入っている）
```

### 05・06 から持ってくる入力ファイル
| ファイル | 作った段階 |
|---|---|
| `inf.dat`, `mesh.dat`, `link.dat`, `node.dat`, `bs_op_corrected.dat` | 05 |
| `manhole_bshosei.dat`, `conduit_bshosei.dat` | 06 |

（city4 の例ではコピー済みです。都市を作り直したら、上書きしてください。）

## city4 の河川（断面番号）

| reach | 断面番号 `IND` | 延長 | 河床高（上流 → 下流） |
|---|---|---|---|
| 本川 上流（main_up） | 1 – 30 | 1500 m | −2.00 → −2.75 m |
| 本川 下流（main_down） | 31 – 61 | 1500 m | −2.75 → −3.50 m |
| 支川（trib） | 62 – 92 | 1500 m | −1.75 → −2.75 m |

断面間隔は約 50 m、合計 92 断面です。これらの値は **各スクリプト冒頭の `REACHES` などで共通に定義** されているので、変えるときは全スクリプトをそろえて変更してください。

## 実行手順

```bash
cd 07_river/city4

# (1) 河道断面の初期データ
python makekasho_init_v2.py           # → kasho_v2_ini_confluence.dat
cp kasho_v2_ini_confluence.dat kasho_ini.dat   # (2) が kasho_ini.dat という名前で読むため

# (2) 河道 ↔ 氾濫原の接続
python makerivto2d_re.py              # → riv_to_2d_v2.dat

# (3) 堤防高を 2 次元側の地盤高から決めて断面データ完成
python makekasho_city4_v2.py          # → kasho_v2.dat

# (4) 断面形状 → 水位-面積・水位-径深テーブル
python makedanmen_v2.py               # → river_danmen_v2.dat
python makehahr_v2.py                 # → h-a_v2.dat, h-r_v2.dat

# (5) 境界条件（上流流量・下流水位）
python makehydr_v2.py                 # → hydr_v2.dat

# (6) 初期条件
python makeshoki_v2.py                # → shoki_v2.dat

# (7) 下水道 ↔ 河川の接続
python makemh_riv.py                  # → mh_riv.csv（+ mh_riv_debug.csv）
python csv_to_dat.py                  # → mh_to_riv.dat
python makesw_riv.py                  # → sw_riv.dat
python makesw_riv_gr.py               # → sw_riv_gr.dat（+ connect4_mesh_*.csv）
```

## 各スクリプトの入出力

| 順 | スクリプト | 入力 | 出力 | 内容 |
|---|---|---|---|---|
| 1 | `makekasho_init_v2.py` | （パラメータ） | `kasho_v2_ini_confluence.dat` | 断面番号、距離標、河床高、粗度、断面間隔、勾配の初期値 |
| 2 | `makerivto2d_re.py` | `inf.dat`, `mesh.dat`, `link.dat`, `kasho_ini.dat` | `riv_to_2d_v2.dat` | 各断面の左岸・右岸で、河道メッシュと氾濫原メッシュの境界リンクを対応づける |
| 3 | `makekasho_city4_v2.py` | `kasho_v2_ini_confluence.dat`, `riv_to_2d_v2.dat`, `link.dat`, `bs_op_corrected.dat` | `kasho_v2.dat` | 接続する 2 次元メッシュの地盤高から左右岸の堤防高を設定 |
| 4a | `makedanmen_v2.py` | （パラメータ） | `river_danmen_v2.dat` | 横断形状（矩形断面、5 m 間隔の点） |
| 4b | `makehahr_v2.py` | `river_danmen_v2.dat` | `h-a_v2.dat`, `h-r_v2.dat` | 水位ごとの通水断面積 A、径深 R |
| 5 | `makehydr_v2.py` | （パラメータ） | `hydr_v2.dat` | 本川・支川の上流端流量、下流端水位（0.5 h 刻み、6 h） |
| 6 | `makeshoki_v2.py` | `kasho_v2.dat` | `shoki_v2.dat` | 各断面の初期水位・流量（河床 + 0.8 m など） |
| 7a | `makemh_riv.py` | `inf.dat`, `mesh.dat`, `kasho_v2.dat`, `manhole_bshosei.dat` | `mh_riv.csv` | 河道メッシュから **100 m 以内** のマンホール（= 河川に排水するマンホール）と最寄りの河川断面の対応。距離は `threshold` で変更 |
| 7b | `csv_to_dat.py` | `mh_riv.csv` | `mh_to_riv.dat` | 空白区切りに変換 |
| 7c | `makesw_riv.py` | `conduit_bshosei.dat`, `mh_to_riv.dat` | `sw_riv.dat` | 河川へ吐き出す管渠（管渠番号、マンホール番号、断面番号） |
| 7d | `makesw_riv_gr.py` | `inf.dat`, `mesh.dat`, `kasho_v2.dat`, `sw_riv.dat` | `sw_riv_gr.dat` | 断面番号を代表の河道メッシュ番号に置き換えた版 |

## 主な境界・初期条件（変更する場所）

| 項目 | ファイル | 変数 | city4 の値 |
|---|---|---|---|
| 本川上流流量 | `makehydr_v2.py` | `Q_MAIN_BASE`, `Q_MAIN_PEAK` | 2.0 m³/s（一定） |
| 支川上流流量 | `makehydr_v2.py` | `Q_TRIB_BASE`, `Q_TRIB_PEAK` | 1.0 m³/s（一定） |
| 下流端水位 | `makehydr_v2.py` | `H_BASE`, `H_PEAK` | −3.0 m（一定） |
| 計算時間 | `makehydr_v2.py` | `T_TOTAL_HOURS`, `DT_HOURS` | 6 h, 0.5 h 刻み |
| 初期水深 | `makeshoki_v2.py` | `h0` | 0.8 m |
| 粗度係数 | `makekasho_init_v2.py` | `N_MANNING` | 0.030 |
| 河道幅・堤防高 | `makedanmen_v2.py` | `width`, `levee_h` | 本川 30 m / 4.0 m、支川 20 m / 3.5 m |

Fortran 本体がこれらをどの書式で読むかは [`docs/fortran_input_read_code.md`](../docs/fortran_input_read_code.md) を参照してください。

## 次の段階へ
出来上がったファイルを Fortran が読む名前にして `08_fortran_input/` に集めます。

## 再現性の確認
上の手順を city4 の入力から実行し直し、`kasho_v2.dat`, `riv_to_2d_v2.dat`, `h-a_v2.dat`, `h-r_v2.dat`, `hydr_v2.dat`, `shoki_v2.dat`, `mh_to_riv.dat`, `sw_riv.dat`, `sw_riv_gr.dat` が出力例と **完全に一致** することを確認済みです。
（`makemh_riv.py` は元ファイルでは距離のしきい値がコメントアウトされていたため、出力例に合わせて `threshold = 100.0` を有効にしています。）

## ⚠ 要確認
- `makerivto2d_re.py` は `kasho_ini.dat` を読みます。使うのは距離標（`DIST` 列）だけで、`kasho_ini.dat` と `kasho_v2_ini_confluence.dat` の距離標は同じであることを確認済みです。
- `sw_riv.dat` と `sw_riv_gr.dat` のどちらを解析で使ったかは記録がありません（`docs/fortran_input_read_code.md` の `connect_4` 参照）。
- 旧版（v1、`_re` なし等）のスクリプトと、city012 用の `makedata1hr / makedata6hr / remakedata_2000` は `archive/River_all_versions/` にあります。
- `archive/River_all_versions/river/river.f90` は 1 次元河道単体の計算プログラム（2002, k.kawaike）で、河川データの動作確認に使えます。
