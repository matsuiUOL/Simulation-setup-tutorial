# 05 メッシュ前処理（Fortran）

GiD の `.msh` から、氾濫解析で使う **メッシュ・リンク（辺）・属性・地盤高** のデータを作ります。
3 本の Fortran プログラムを順番に実行します。

## フォルダ

```
05_mesh_preprocess/city4/      ← 作業フォルダ（ここで実行する）
├── run_mesh.sh                ← コンパイル + 3 本を順に実行
├── mesh_attribution.f90       ← ① 属性付け
├── pred.f90                   ← ② mesh.dat / link.dat 作成
├── bsmake_corrected.f90       ← ③ 地盤高作成
├── city4_*.msh (5 個)          ← 入力（04 の出力）
└── node.dat, mesho.dat, centroid.dat, inf.dat, mesh.dat, link.dat, bs_op_corrected.dat ← 出力例
```

`out5m.txt`（10 MB）は容量節約のためここには入れていません。**実行前に 02 からコピー** してください。

## 実行方法

```bash
cd 05_mesh_preprocess/city4
cp ../../02_DEM_text/example_output/out5m.txt .
bash run_mesh.sh
```

`run_mesh.sh` は Intel Fortran（`ifx`）を使います。gfortran しかない場合は中の `ifx` を `gfortran` に置き換えてください。
Windows で動かす場合は WSL か、Intel oneAPI のコマンドプロンプトで同じ順にコンパイル・実行します。

## 処理の流れと入出力

| 順 | プログラム | 入力 | 出力 | 内容 |
|---|---|---|---|---|
| ① | `mesh_attribution.f90` | `city4_after_all.msh`（全体）<br>`city4_road.msh`, `city4_building.msh`, `city4_river.msh`, `city4_others.msh` | `node.dat`, `mesho.dat`, `centroid.dat`, `inf.dat` | 全体メッシュの各要素の重心が、どの属性メッシュに入るかで属性を決める |
| ② | `pred.f90` | `node.dat`, `mesho.dat` | `mesh.dat`, `link.dat` | 要素と辺（リンク）の接続関係、面積、重心、辺長などを作る |
| ③ | `bsmake_corrected.f90` | `centroid.dat`, `out5m.txt` | `bs_op_corrected.dat`（+ `check*.dat`） | 重心に近い DEM 3 点から距離の重み付きで地盤高を求める |

※ 入出力のファイル名は **各 .f90 の open 文で固定** されています。都市名を変えるときは `.f90` 内のファイル名も変えてください。

## 属性コード（`inf.dat` の 2 列目）

| コード | 属性 | 由来する .msh |
|---|---|---|
| 1 | 道路 | `city4_road.msh` |
| 2 | 建物（街区） | `city4_building.msh` |
| 3 | 河道 | `city4_river.msh` |
| 4 | その他（空地など） | `city4_others.msh` |

city4 の例：道路 1506 / 建物 1063 / 河道 216 / その他 1396 要素（合計 4181）。

## 出力ファイルの中身（概要）

| ファイル | 中身 |
|---|---|
| `node.dat` | 節点数、各節点の番号と x, y |
| `mesho.dat` | 各要素を構成する節点番号 |
| `centroid.dat` | 各要素の重心 x, y |
| `inf.dat` | 要素番号と属性コード |
| `mesh.dat` | 1 行目に要素数。各要素 4 行：①番号・辺数・節点 ②構成リンク ③面積・重心 x, y ④重み |
| `link.dat` | 1 行目にリンク数。各リンク 3 行：①番号・両側の要素（0 は境界）・両端節点 ②長さ・法線方向 ③予備 |
| `bs_op_corrected.dat` | 要素番号と地盤高 [m] |
| `check*.dat` | 地盤高内挿の確認用（Git には入れない） |

## 次の段階へ
- `mesh.dat`, `link.dat`, `node.dat`, `inf.dat`, `bs_op_corrected.dat` → 07（河川）と 08（最終入力）で使います。

## ⚠ 要確認
- `mesh.dat` / `link.dat` 各行の列の意味は、出力例から読み取った概要です。正確な定義は解析本体のソースで確認してください。
- 元フォルダには `bsmake_corrected_city0.f90` もありました（`archive/Fortran_input_city012/mesh/city4/`）。city0 用の差分と思われます。
