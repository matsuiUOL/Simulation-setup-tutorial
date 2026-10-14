# 環境構築

## 必要なソフト

| ソフト | 用途 | 段階 |
|---|---|---|
| Python 3.10 以上 | 都市生成・DEM・下水道・河川データ | 01, 02, 06, 07 |
| QGIS 3.x | Shapefile の確認、属性編集、CSV 書き出し | 03 |
| GiD | メッシュ作成 | 04 |
| Fortran コンパイラ（Intel `ifx` または `gfortran`） | メッシュ前処理、解析本体 | 05 |
| Git | バージョン管理・GitHub への push | – |

## Python ライブラリ

`geopandas` と `rasterio` は pip だとインストールに失敗しやすいので、**conda（Miniforge）** を勧めます。

```bash
# Miniforge を入れたあと
conda create -n vcity python=3.11 numpy pandas geopandas shapely rasterio -c conda-forge
conda activate vcity
```

pip を使う場合:
```bash
pip install -r requirements.txt
```

| ライブラリ | 使う段階 |
|---|---|
| numpy | 01, 02 |
| pandas | 06（`idplusone.py`, `nodeconnectbranch.py`） |
| geopandas, shapely, rasterio | 01（都市生成）, 03（`makeRiverpoly.py`） |
| （標準ライブラリのみ） | 07 の大半, 06 の `makemanhole.py`, `makeconduit.py` |

`03_QGIS/scripts/add_dem_z_to_nodes.py` は **QGIS 内の Python コンソール専用** です（通常の Python では動きません）。

## Fortran

```bash
# Intel oneAPI（研究室標準）
ifx mesh_attribution.f90 -o mesh_attri.out

# gfortran でも可
gfortran mesh_attribution.f90 -o mesh_attri.out
```

Windows では WSL（Ubuntu）上で `sudo apt install gfortran` とするのが手軽です。

## 座標系
すべて **JGD2011 平面直角座標系 第 IX 系（EPSG:6677）** です。QGIS のプロジェクト CRS もこれに合わせてください。
