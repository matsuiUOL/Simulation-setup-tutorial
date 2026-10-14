#!/usr/bin/env python
import numpy as np
import rasterio
from rasterio.transform import from_origin
from rasterio.crs import CRS
import geopandas as gpd
from shapely.geometry import LineString, Point
from pathlib import Path


def create_directories(base_dir: Path):
    dem_dir = base_dir / "01_DEM"
    layers_dir = base_dir / "02_GIS_layers"
    dem_dir.mkdir(parents=True, exist_ok=True)
    layers_dir.mkdir(parents=True, exist_ok=True)
    return dem_dir, layers_dir


def make_dem(dem_path: Path, epsg: int = 6677):
    # DEM パラメータ
    dx = 5.0
    dy = 5.0
    nx = 600   # 600 * 5m = 3000 m
    ny = 600

    # 解析範囲（左上原点） - 適宜変更可
    origin_x = 152000.0
    origin_y = 505000.0

    transform = from_origin(origin_x, origin_y, dx, dy)
    crs = CRS.from_epsg(epsg)

    x = np.arange(nx)
    y = np.arange(ny)
    X, Y = np.meshgrid(x, y)

    # 緩い勾配（南→北に傾斜）
    dem = 0.004 * (ny - Y)

    # 中央付近に谷（のちの河川コリドーに合わせる）
    valley = 1.5 * np.exp(-((X - nx/2) / 100.0)**2)
    dem -= valley

    # 微地形
    #dem += 0.3 * (np.sin(X/25.0) * np.sin(Y/30.0))

    dem = dem.astype("float32")

    with rasterio.open(
        dem_path,
        "w",
        driver="GTiff",
        height=ny,
        width=nx,
        count=1,
        dtype="float32",
        crs=crs,
        transform=transform,
    ) as dst:
        dst.write(dem, 1)

    xmin = origin_x
    xmax = origin_x + nx * dx
    ymax = origin_y
    ymin = origin_y - ny * dy

    return xmin, xmax, ymin, ymax, dx, dy, crs


def make_river(river_path: Path, city_bbox, river_corridor, crs):
    """
    河川コリドーの中心に、縦方向の開渠（LineString）を1本作る簡易版。
    必要なら、ここをジグザグや分岐にしてもOK。
    """
    xmin_u, xmax_u, ymin_u, ymax_u = city_bbox
    x_river_c, river_w = river_corridor

    # シンプルに南北に1本
    river_line = LineString([(x_river_c, ymin_u), (x_river_c, ymax_u)])

    gdf = gpd.GeoDataFrame(
        {"river_id": [0]},
        geometry=[river_line],
        crs=crs,
    )
    gdf.to_file(river_path)

def make_roads(roads_path: Path, city_bbox, river_corridor, crs):
    xmin_u, xmax_u, ymin_u, ymax_u = city_bbox
    x_river_c, river_w = river_corridor

    roads = []
    road_spacing = 200.0

    # コリドー幅を少し広めに避ける（道路が開渠に近づきすぎないように）
    avoid_half_width = river_w / 2.0 + 30.0  # +30m 余裕

    # 南北道路
    x_vals = np.arange(xmin_u, xmax_u + 1e-6, road_spacing)
    x_used = []
    for x in x_vals:
        if abs(x - x_river_c) < avoid_half_width:
            continue
        roads.append(LineString([(x, ymin_u), (x, ymax_u)]))
        x_used.append(x)

    # 東西道路
    y_vals = np.arange(ymin_u, ymax_u + 1e-6, road_spacing)
    y_used = []
    for y in y_vals:
        roads.append(LineString([(xmin_u, y), (xmax_u, y)]))
        y_used.append(y)

    gdf = gpd.GeoDataFrame(
        {"road_id": np.arange(len(roads))},
        geometry=roads,
        crs=crs,
    )
    gdf.to_file(roads_path)

    return np.array(x_used), np.array(y_used)

def make_sewer_nodes_and_links(nodes_path: Path, links_path: Path,
                               x_roads, y_roads,
                               city_bbox, river_corridor, crs):
    xmin_u, xmax_u, ymin_u, ymax_u = city_bbox
    x_river_c, river_w = river_corridor

    # 道路から少しずらす（ここで道路との非一致を表現）
    offset_x = 10.0
    offset_y = 10.0

    x_mh_vals = np.clip(x_roads + offset_x, xmin_u, xmax_u)
    y_mh_vals = np.clip(y_roads + offset_y, ymin_u, ymax_u)

    points = []
    node_ids = []
    idx_map = {}

    node_id = 0
    for ix, x in enumerate(x_mh_vals):
        for iy, y in enumerate(y_mh_vals):
            # 河川コリドー内にはマンホールを置かない
            if abs(x - x_river_c) < river_w / 2.0 + 30.0:
                continue

            # （お好みで微妙にランダムなズレを足すことも可能）
            # x_rand = x + np.random.uniform(-3.0, 3.0)
            # y_rand = y + np.random.uniform(-3.0, 3.0)
            p = Point(x, y)
            points.append(p)
            node_ids.append(node_id)
            idx_map[(ix, iy)] = node_id
            node_id += 1

    nodes_gdf = gpd.GeoDataFrame(
        {"node_id": node_ids},
        geometry=points,
        crs=crs,
    )
    nodes_gdf.to_file(nodes_path)

    # 以下、リンク生成は元コードほぼそのまま
    link_geoms = []
    start_ids = []
    end_ids = []

    n_x = len(x_mh_vals)
    n_y = len(y_mh_vals)

    def has_node(ix, iy):
        return (ix, iy) in idx_map

    def add_link(ix1, iy1, ix2, iy2):
        nid1 = idx_map[(ix1, iy1)]
        nid2 = idx_map[(ix2, iy2)]
        p1 = nodes_gdf.loc[nodes_gdf["node_id"] == nid1].geometry.values[0]
        p2 = nodes_gdf.loc[nodes_gdf["node_id"] == nid2].geometry.values[0]
        link_geoms.append(LineString([p1, p2]))
        start_ids.append(nid1)
        end_ids.append(nid2)

    # 東西方向
    for ix in range(n_x - 1):
        for iy in range(n_y):
            if has_node(ix, iy) and has_node(ix + 1, iy):
                add_link(ix, iy, ix + 1, iy)

    # 南北方向
    for ix in range(n_x):
        for iy in range(n_y - 1):
            if has_node(ix, iy) and has_node(ix, iy + 1):
                add_link(ix, iy, ix, iy + 1)

    link_ids = list(range(len(link_geoms)))
    links_gdf = gpd.GeoDataFrame(
        {"link_id": link_ids,
         "start_id": start_ids,
         "end_id": end_ids},
        geometry=link_geoms,
        crs=crs,
    )
    links_gdf.to_file(links_path)


def main():
    base_dir = Path(__file__).resolve().parent
    dem_dir, layers_dir = create_directories(base_dir)

    dem_path = dem_dir / "artificial_dem_epsg6677.tif"
    roads_path = layers_dir / "roads.shp"
    nodes_path = layers_dir / "sewer_nodes.shp"
    links_path = layers_dir / "sewer_links.shp"
    river_path = layers_dir / "river.shp"   # 追加

    xmin, xmax, ymin, ymax, dx, dy, crs = make_dem(dem_path, epsg=6677)

    margin = 500.0
    xmin_u = xmin + margin
    xmax_u = xmax - margin
    ymin_u = ymin + margin
    ymax_u = ymax - margin
    city_bbox = (xmin_u, xmax_u, ymin_u, ymax_u)

    # 河川コリドー（縦方向の空白帯）
    x_river_c = 0.5 * (xmin_u + xmax_u) - 200.0
    river_w = 200.0
    river_corridor = (x_river_c, river_w)

    # DEM -> OK
    # 河川ライン
    make_river(river_path, city_bbox, river_corridor, crs)

    # 道路
    x_roads, y_roads = make_roads(roads_path, city_bbox, river_corridor, crs)

    # 下水 nodes & links
    make_sewer_nodes_and_links(
        nodes_path, links_path,
        x_roads, y_roads,
        city_bbox, river_corridor, crs
    )


    # 道路生成
    x_roads, y_roads = make_roads(roads_path, city_bbox, river_corridor, crs)
    print(f"Roads saved to: {roads_path}")

    # 下水道ノード＆リンク生成
    make_sewer_nodes_and_links(
        nodes_path, links_path,
        x_roads, y_roads,
        city_bbox, river_corridor, crs
    )
    print(f"Sewer nodes saved to: {nodes_path}")
    print(f"Sewer links saved to: {links_path}")


if __name__ == "__main__":
    main()
