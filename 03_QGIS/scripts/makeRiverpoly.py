import geopandas as gpd
from shapely.geometry import LineString

# ----------------------------
# 条件
# ----------------------------
crs_epsg = 6677
width = 30.0                 # 河道幅 [m]
half_width = width / 2.0

# 中心線の座標（上端・下端）
x1, y1 = 153500, 505000
x2, y2 = 153500, 502000

# ----------------------------
# 中心線の作成
# ----------------------------
centerline = LineString([
    (x1, y1),
    (x2, y2)
])

# ----------------------------
# 幅30mのポリゴン作成
# cap_style=2 で端を四角形状にする
# ----------------------------
river_polygon = centerline.buffer(
    half_width,
    cap_style=2,   # 1:丸, 2:四角, 3:平ら
    join_style=2
)

# ----------------------------
# GeoDataFrame化
# ----------------------------
gdf = gpd.GeoDataFrame(
    {"name": ["river"]},
    geometry=[river_polygon],
    crs=f"EPSG:{crs_epsg}"
)

# ----------------------------
# 保存
# ----------------------------
gdf.to_file("river_polygon.shp", encoding="utf-8")
gdf.to_file("river_polygon.gpkg", driver="GPKG")

print(gdf)
print("保存完了: river_polygon.shp, river_polygon.gpkg")