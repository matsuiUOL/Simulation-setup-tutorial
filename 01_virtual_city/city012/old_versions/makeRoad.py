from shapely.geometry import LineString
import geopandas as gpd

roads = []

# 南北道路
for x in range(0, 2000, 200):
    roads.append(LineString([(x, 0), (x, 2000)]))

# 東西道路
for y in range(0, 2000, 200):
    roads.append(LineString([(0, y), (2000, y)]))

gdf = gpd.GeoDataFrame(geometry=roads, crs="EPSG:6677")
gdf.to_file("roads.shp")
