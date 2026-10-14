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
    # -------------------------
    # DEM パラメータ
    # -------------------------
    dx = 5.0
    dy = 5.0
    nx = 400   # 400 * 5m = 2000m
    ny = 400

    # 解析範囲（左上原点）
    origin_x = 152000.0
    origin_y = 505000.0

    transform = from_origin(origin_x, origin_y, dx, dy)
    crs = CRS.from_epsg(epsg)

    # ローカルグリッド
    x = np.arange(nx)
    y = np.arange(ny)
    X, Y = np.meshgrid(x, y)

    # 南→北に緩い勾配（Yが小さい方を南とするなら調整してください）
    dem = 0.005 * (ny - Y)  # 北側高め

    # 中央に谷
    valley = 1.5 * np.exp(-((X - nx / 2) / 80.0) ** 2)
    dem -= valley

    # 微地形
    dem += 0.3 * (np.sin(X / 20.0) * np.sin(Y / 25.0))

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

    # 範囲情報も返す（道路・下水生成に使う）
    xmin = origin_x
    xmax = origin_x + nx * dx
    ymax = origin_y
    ymin = origin_y - ny * dy

    return xmin, xmax, ymin, ymax, dx, dy, crs


def make_roads(roads_path: Path, xmin, xmax, ymin, ymax, crs):
    roads = []

    road_spacing = 200.0  # 道路間隔 [m]

    # 南北道路（x 一定）
    x_vals = np.arange(xmin, xmax + 1e-6, road_spacing)
    for x in x_vals:
        roads.append(LineString([(x, ymin), (x, ymax)]))

    # 東西道路（y 一定）
    y_vals = np.arange(ymin, ymax + 1e-6, road_spacing)
    for y in y_vals:
        roads.append(LineString([(xmin, y), (xmax, y)]))

    gdf = gpd.GeoDataFrame(
        {"road_id": np.arange(len(roads))},
        geometry=roads,
        crs=crs,
    )
    gdf.to_file(roads_path)


def make_sewer_nodes_and_links(nodes_path: Path, links_path: Path,
                               xmin, xmax, ymin, ymax, crs):
    # マンホール間隔（道路間隔と合わせておく）
    mh_spacing = 200.0

    x_vals = np.arange(xmin, xmax + 1e-6, mh_spacing)
    y_vals = np.arange(ymin, ymax + 1e-6, mh_spacing)

    # ノード生成（グリッド状の交点）
    points = []
    node_ids = []
    idx_map = {}  # (ix, iy) -> node_id

    node_id = 0
    for ix, x in enumerate(x_vals):
        for iy, y in enumerate(y_vals):
            points.append(Point(x, y))
            node_ids.append(node_id)
            idx_map[(ix, iy)] = node_id
            node_id += 1

    nodes_gdf = gpd.GeoDataFrame(
        {"node_id": node_ids},
        geometry=points,
        crs=crs,
    )
    nodes_gdf.to_file(nodes_path)

    # リンク生成（上下左右に接続）
    link_geoms = []
    link_ids = []
    start_ids = []
    end_ids = []

    n_x = len(x_vals)
    n_y = len(y_vals)

    def add_link(ix1, iy1, ix2, iy2):
        nid1 = idx_map[(ix1, iy1)]
        nid2 = idx_map[(ix2, iy2)]
        p1 = nodes_gdf.loc[nodes_gdf["node_id"] == nid1].geometry.values[0]
        p2 = nodes_gdf.loc[nodes_gdf["node_id"] == nid2].geometry.values[0]
        link_geoms.append(LineString([p1, p2]))
        start_ids.append(nid1)
        end_ids.append(nid2)

    # 東西方向リンク
    for ix in range(n_x - 1):
        for iy in range(n_y):
            add_link(ix, iy, ix + 1, iy)

    # 南北方向リンク
    for ix in range(n_x):
        for iy in range(n_y - 1):
            add_link(ix, iy, ix, iy + 1)

    link_ids = list(range(len(link_geoms)))

    links_gdf = gpd.GeoDataFrame(
        {
            "link_id": link_ids,
            "start_id": start_ids,
            "end_id": end_ids,
        },
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

    # DEM 作成
    xmin, xmax, ymin, ymax, dx, dy, crs = make_dem(dem_path, epsg=6677)
    print(f"DEM saved to: {dem_path}")
    print(f"Extent X: {xmin} 〜 {xmax}")
    print(f"Extent Y: {ymin} 〜 {ymax}")
    print(f"CRS: {crs.to_string()}")

    # 道路生成
    make_roads(roads_path, xmin, xmax, ymin, ymax, crs)
    print(f"Roads saved to: {roads_path}")

    # 下水道ノード＆リンク生成
    make_sewer_nodes_and_links(nodes_path, links_path, xmin, xmax, ymin, ymax, crs)
    print(f"Sewer nodes saved to: {nodes_path}")
    print(f"Sewer links saved to: {links_path}")


if __name__ == "__main__":
    main()
