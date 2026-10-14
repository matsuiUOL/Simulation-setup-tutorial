# 01 仮想都市の生成（Python）

道路・街区（建物）・河川・ポンプ場・下水道ネットワークを持つ **仮想都市** を Python で作り、
DEM（GeoTIFF）と GIS レイヤ（Shapefile）として書き出します。

## フォルダ

```
01_virtual_city/
├── city4/                      ← 標準例（本川 + 支川の合流あり）
│   ├── makecity_3.py           ← ★ これを実行する（最新版）
│   ├── city4.png               ← 完成イメージ
│   ├── 01_DEM/city_confluence_v3/          ← 出力例：DEM (.tif)
│   ├── 02_GIS_layers/city_confluence_v3/   ← 出力例：各レイヤ (.shp) と gap_points.csv
│   ├── forGiD/                 ← GiD 読み込み用に QGIS で整えた補助レイヤ
│   └── old_versions/           ← makecity.py, makecity_2.py（旧版）
└── city012/                    ← 単一河川の都市（city0/1/2）
    ├── makeDRSM7.py            ← city1&2 用
    ├── makeDRSM_city0.py       ← city0 用
    ├── 01_DEM/city0/  02_GIS_layers/city0/   ← 出力例
    └── old_versions/           ← makeDRSM〜6, makeDEM.py, makeRoad.py
```

## 実行方法

```bash
cd 01_virtual_city/city4
python makecity_3.py
```

スクリプトと同じ場所に `01_DEM/city_confluence_v3/` と `02_GIS_layers/city_confluence_v3/` が作られ、ファイルが書き出されます。

## 出力されるファイル（city4）

| ファイル | 種類 | 内容 |
|---|---|---|
| `01_DEM/.../artificial_dem_confluence_v2_epsg6677.tif` | ラスタ | 5 m DEM（city4 は標高 0 の平坦地形） |
| `roads_confluence_v2.shp` | ポリゴン | 道路（幅 40 m、200 m 間隔） |
| `roads_edges_confluence_v2.shp` | ライン | 道路の縁線（GiD でメッシュの境界に使う） |
| `city_blocks_confluence_v2.shp` | ポリゴン | 街区（建物ブロック） |
| `river_center_confluence_v2.shp` | ライン | 河川中心線（本川・支川） |
| `river_polygon_confluence_v2.shp` | ポリゴン | 河道 |
| `river_gaps_confluence_v2.shp` / `river_side_gap_polygons.shp` | ポリゴン | 河川沿いの空地（道路でも街区でもない部分） |
| `pump_station_confluence_v2.shp` | ポイント | ポンプ場 |
| `sewer_nodes_confluence_v2.shp` | ポイント | 下水道ノード（= 道路交差点、マンホール） |
| `sewer_links_confluence_v2.shp` | ライン | 下水道管路（ノード間） |
| `gap_points.csv` | CSV | 河川沿い空地の角点座標（GiD での点入力用） |

※ `.shp` には必ず `.shx .dbf .prj .cpg` がセットで付きます。**まとめて移動・コピー** してください。

## 主なパラメータ（`makecity_3.py` 内）

| 変数・引数 | 既定値 | 意味 |
|---|---|---|
| `dx, dy` / `nx, ny` | 5 m / 600 | DEM の解像度とセル数（3 km 四方） |
| `origin_x, origin_y` | 152000, 505000 | 領域の左上座標（EPSG:6677） |
| `margin` | 500 m | 領域外周から都市までの余白 |
| `main_width` / `trib_width` | 30 m / 15 m | 本川・支川の河道幅 |
| `road_width` / `road_spacing` | 40 m / 200 m | 道路幅と道路間隔 |

都市の形を変えたい場合はここを変更します。

## 次の段階へ
- 生成した `.shp` を QGIS で開いて確認 → [`03_QGIS`](../03_QGIS/README.md)
- `.shp` を GiD に読み込んでメッシュ化 → [`04_GiD`](../04_GiD/README.md)

## ⚠ 要確認
- 出力フォルダ名は `city_confluence_v3` ですが、ファイル名は `_v2` のままです（スクリプト側の命名）。
- `forGiD/` の 4 レイヤ（`cornerP`, `riverpolygon`, `river_boundary`, `roadedge`）は、スクリプトでは作られていません。QGIS で手作業で作成したものと思われます。
- 河川データ作成（07）の `makedanmen_v2.py` では支川幅を 20 m としており、ここ（15 m）と値が異なります。
