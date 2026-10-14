# 02 DEM の x y z テキスト化（Python）

Fortran のメッシュ前処理（05 の `bsmake_corrected.f90`）は、各メッシュの地盤高を
**x y z 形式のテキスト DEM** から内挿します。そのファイル `out5m.txt` を作ります。

## スクリプト

| スクリプト | 地形 | 出力先 |
|---|---|---|
| `make_DEM_city0.py` | **平坦（z = 0）** ← city0・city4 で使用 | `DEM_text/city0/out5m2.txt` |
| `make_DEMtext2.py` | 南が高く北が低い緩勾配 + 中央の谷 | `DEM_text/out5m2.txt` |
| `make_DEMtext.py` | 旧版 | `DEM_text/out5m.txt` |

```bash
cd 02_DEM_text
python make_DEM_city0.py
```

## 出力の書式

```
152002.500 504997.500 0.000
152007.500 504997.500 0.000
...
```
- 1 行 1 セル、`x y z`（空白区切り）。x, y は **セル中心** 座標。
- 北西の角から東へ、行ごとに南へ並ぶ（600 × 600 = 360,000 行）。

`example_output/out5m.txt` が city4 で実際に使ったファイルです（`make_DEM_city0.py` の出力と同一）。

## 使い方
05 の作業フォルダに **`out5m.txt` という名前で** コピーします。

```bash
cp DEM_text/city0/out5m2.txt ../05_mesh_preprocess/city4/out5m.txt
```

## 注意
- DEM の範囲・原点・解像度は 01 の `makecity_3.py` と **必ず一致** させてください（どちらも原点 (152000, 505000)、5 m、600×600）。
- 01 で地形を変えた場合は、こちらの `generate_dem_array()` も同じ式に変更します。
