# 04 GiD でのメッシュ作成

01 で作った Shapefile を GiD に読み込み、**三角形（一部四角形）の非構造メッシュ** を作ります。
05 の Fortran は、**全体メッシュ 1 つ** と **属性ごとのメッシュ 4 つ** を突き合わせて、各メッシュに土地利用属性を付けます。

## フォルダ

```
04_GiD/
├── city4/beforeMesh.gid/   ← メッシュ分割前の GiD プロジェクト（city4）。GiD で開ける
└── example_msh_city4/      ← 出力例（05 の入力になる .msh）
    ├── city4_after_all.msh ← 全体メッシュ
    ├── city4_road.msh      ← 道路部分だけ（属性 1）
    ├── city4_building.msh  ← 建物（街区）部分だけ（属性 2）
    ├── city4_river.msh     ← 河道部分だけ（属性 3）
    └── city4_others.msh    ← それ以外（河川沿い空地など）（属性 4）
```

## 手順（概要）

1. **GiD を起動し、Shapefile を読み込む**
   `Files → Import → Shapefile`（GiD のバージョンにより `GIS → Import shapefile`）で次を読み込む。
   - `roads_edges_*.shp`（道路の縁）
   - `city_blocks_*.shp`（街区）
   - `river_polygon_*.shp`（河道）
   - `river_side_gap_polygons.shp` / `forGiD/*.shp`（境界・補助線）
2. **線を整理してサーフェスを作る**
   重複線の削除（`Utilities → Collapse → Model`）を行い、閉じた領域ごとに `Geometry → Create → NURBS surface` でサーフェスを作る。
3. **メッシュサイズを決めてメッシュ分割**
   `Mesh → Unstructured → Assign sizes` で要素サイズを指定し、`Mesh → Generate mesh`。
4. **全体メッシュを書き出す**
   `Files → Export → Mesh`（または `Mesh → Save`）で `city4_after_all.msh` として保存。
5. **属性ごとのメッシュを書き出す**
   道路・建物・河道・その他のサーフェスだけを残した状態で、同じく `.msh` を 4 つ書き出す。
   （GiD の Layer 機能で属性ごとにレイヤ分けしておき、表示レイヤを切り替えて書き出すと楽です）

## .msh の書式（GiD ASCII）

```
MESH dimension 3 ElemType Triangle Nnode 3
Coordinates
    1          155000          505000               0
    ...
End Coordinates
Elements
    1   2026   2034   2017
    ...
End Elements
```

## 次の段階へ
5 つの `.msh` を `05_mesh_preprocess/city4/` に、**上の名前で** 置きます（Fortran 側でファイル名を固定しているため）。

## ⚠ 要確認
- 上の GiD メニュー名は一般的な操作の目安です。研究室で使っている GiD のバージョンに合わせて、実際の操作を追記してください。
- 05 では「全体メッシュの各要素の重心が、どの属性別メッシュの三角形に入るか」で属性を決めます。そのため属性別メッシュは、全体メッシュと同じ範囲を隙間なく覆っている必要があります。
- 属性別 `.msh` の 1 行目は `ElemType Linear Nnode 2` になっていますが、中身は 3 節点の三角形です（Fortran は 1 行目を読み飛ばすので問題ありません）。
- 古い試行の `.gid` プロジェクトと `.msh` は `archive/GiD_old_projects/` にあります。
