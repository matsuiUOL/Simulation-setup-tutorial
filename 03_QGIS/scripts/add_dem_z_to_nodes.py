# レイヤ名・標高フィールド名を必要に応じて変えてください
nodes_layer_name = 'Nodes_xy'
dem_layer_name   = 'reDEM5m'
dem_z_field_name = 'z'   # DEM側の標高フィールド名

from qgis.core import QgsProject, QgsSpatialIndex, QgsField
from qgis.PyQt.QtCore import QVariant

# レイヤ取得
nodes_layer_list = QgsProject.instance().mapLayersByName(nodes_layer_name)
dem_layer_list   = QgsProject.instance().mapLayersByName(dem_layer_name)

if not nodes_layer_list or not dem_layer_list:
    raise Exception("レイヤ名が見つかりません。nodes_layer_name / dem_layer_name を確認してください。")

nodes_layer = nodes_layer_list[0]
dem_layer   = dem_layer_list[0]

# Nodes側に z フィールドが無ければ追加
prov = nodes_layer.dataProvider()
field_names = [f.name() for f in prov.fields()]
if 'z' not in field_names:
    prov.addAttributes([QgsField('z', QVariant.Double)])
    nodes_layer.updateFields()
    print("Nodes_xy にフィールド 'z' を追加しました。")

# DEM点レイヤに空間インデックス作成
print("DEMレイヤの空間インデックスを作成中...")
dem_index = QgsSpatialIndex(dem_layer.getFeatures())
print("空間インデックス作成完了。")

# ノードごとに最近傍点の平均zを計算
tolerance = 1e-6  # 「ほぼ同じ距離」とみなす許容誤差
k_nearest = 8     # 距離チェック用に取ってくる最近傍点の個数

z_field_idx = nodes_layer.fields().indexFromName('z')

updated = 0

with edit(nodes_layer):
    for node in nodes_layer.getFeatures():
        node_geom = node.geometry()
        if node_geom.isEmpty():
            continue

        # まず最も近いDEM点を1つ取得して「最小距離」を求める
        nearest_ids = dem_index.nearestNeighbor(node_geom.asPoint(), 1)
        if not nearest_ids:
            continue

        nearest_feat = dem_layer.getFeature(nearest_ids[0])
        dmin = node_geom.distance(nearest_feat.geometry())  # ★ ここを修正

        # その距離 dmin とほぼ同じ距離のDEM点を複数取得
        candidate_ids = dem_index.nearestNeighbor(node_geom.asPoint(), k_nearest)

        zs = []
        for fid in candidate_ids:
            f = dem_layer.getFeature(fid)
            d = node_geom.distance(f.geometry())            # ★ ここも修正
            if abs(d - dmin) <= tolerance:
                z_val = f[dem_z_field_name]
                if z_val is not None:
                    try:
                        zs.append(float(z_val))
                    except Exception:
                        pass

        if zs:
            z_mean = sum(zs) / len(zs)
            node[z_field_idx] = z_mean
            nodes_layer.updateFeature(node)
            updated += 1

print(f"更新完了: {updated} 個のノードに平均標高 z を付与しました。")
