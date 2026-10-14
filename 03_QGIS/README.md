# 03 QGIS での確認と下水道データの書き出し

01 で作った `.shp` を QGIS で開き、

1. 都市の形が正しいか目で確認する
2. GiD に読み込ませる境界レイヤを整える（必要に応じて）
3. **下水道のノードと管路を CSV で書き出す**（06 の入力）

を行います。

## フォルダ

```
03_QGIS/
├── scripts/
│   ├── add_dem_z_to_nodes.py   ← QGIS の Python コンソールで実行：ノードに DEM 標高 z を付与
│   └── makeRiverpoly.py        ← 河川中心線から幅 30 m の河道ポリゴンを作る（単体実行）
└── example_layers_city012/     ← city012 で実際に QGIS 上で作ったレイヤ一式（参考）
    ├── Nodes_xy / Nodes_xyz    ← 下水道ノード（z なし / z あり）
    ├── Branches                ← 下水道管路
    ├── Boundary*, extra*, Road_manu, Newriv ← GiD 用に手作業で作った境界・補助線
    └── Virtual_City*.png       ← 完成イメージ
```

## 手順

### 1. レイヤを開く
QGIS で「レイヤ → レイヤを追加 → ベクタレイヤを追加」から `01_virtual_city/city4/02_GIS_layers/city_confluence_v3/*.shp` をすべて読み込みます。
DEM（`.tif`）はラスタレイヤとして追加します。プロジェクトの CRS は **EPSG:6677** にします。

### 2. 下水道ノードに標高 z を付ける（地形がある場合）
1. 02 で作った `out5m.txt` を「区切りテキストレイヤ」として読み込み（x, y, z 列、EPSG:6677）、レイヤ名を `reDEM5m` にする
2. ノードレイヤの名前を `Nodes_xy` にする
3. 「プラグイン → Python コンソール」で `scripts/add_dem_z_to_nodes.py` を開いて実行
   → `Nodes_xy` に最寄り DEM 点の平均標高 `z` が入る

city4 は平坦（z = 0）なので、この手順は省略して z 列を手で追加しても構いません。

### 3. 管径を付ける
管路レイヤ（`sewer_links_...`）の属性テーブルに整数フィールド `Diameter`（mm）を追加し、管径を入力します（city4 の例ではすべて 800 mm）。

### 4. CSV で書き出す（06 の入力）
各レイヤを右クリック →「エクスポート → 地物の保存」で **CSV** を選び、次の列構成で保存します。

**`Nodes.csv`**（ノード = マンホール）
```
Nodes_id,xcoord,ycoord,z
0,152500,502500,0
1,152500,502700,0
```

**`Branches_with_diameter.csv`**（管路）
```
Branches_id,start_node_id,end_node_id,Diameter
0,0,1,800
1,1,2,800
```

- `xcoord, ycoord` は「属性テーブル → フィールド計算機」で `$x`, `$y` を計算して作ります。
- ID は 0 始まりのままで OK（06 の `idplusone.py` で 1 始まりに直します）。
- 01 の `.shp` の列名（`node_id`, `link_id`, `start_id`, `end_id`）を上の名前に変更してから書き出してください。

書き出した 2 つの CSV を `06_sewer/city4/` に置きます。

## ⚠ 要確認
- `example_layers_city012/` の各レイヤの作成手順（どれを GiD に渡したか）は記録が残っていません。分かる人は追記してください。
