import numpy as np
import rasterio
from rasterio.transform import from_origin
from rasterio.crs import CRS
import geopandas as gpd
from shapely.geometry import LineString, Point, Polygon
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


def make_river_rectangular(
    river_center_path: Path,
    river_polygon_path: Path,
    pump_path: Path,
    city_bbox,
    x_river_c: float,
    river_attr_width: float,
    ymax_dem: float,
    crs,
):
    """
    河川を「上下端がフラットな長方形ポリゴン」として作成する。

    - 上端（北側）: DEM 全体の ymax_dem
    - 下端（南側）: city_bbox の ymin_u（= 道路縁の下端）
    """

    xmin_u, xmax_u, ymin_u, ymax_u = city_bbox

    # ★ 下端 = 道路縁の下端（city エリアの南端）
    y_bottom = ymin_u - 20.0
    # ★ 上端 = DEM 全体の境界
    y_top = ymax_dem

    # 河川中心線（見た目用）：長方形の中央を通る縦線
    river_line = LineString([(x_river_c, y_bottom), (x_river_c, y_top)])

    river_center_gdf = gpd.GeoDataFrame(
        {"river_id": [0]},
        geometry=[river_line],
        crs=crs,
    )
    river_center_gdf.to_file(river_center_path)

    # ★ 河川幅 river_attr_width の長方形ポリゴン（上下フラット）
    half_w = river_attr_width / 2.0
    x_left = x_river_c - half_w
    x_right = x_river_c + half_w

    river_poly = Polygon([
        (x_left,  y_bottom),
        (x_right, y_bottom),
        (x_right, y_top),
        (x_left,  y_top),
    ])

    river_poly_gdf = gpd.GeoDataFrame(
        {
            "river_id": [0],
            "landuse": ["river"],
        },
        geometry=[river_poly],
        crs=crs,
    )
    river_poly_gdf.to_file(river_polygon_path)

    # 下流端（北側端）にポンプ場ポイント
    pump_point = Point(x_river_c, y_top)
    pump_gdf = gpd.GeoDataFrame(
        {
            "pump_id": [0],
            "type": ["pump_station"],
        },
        geometry=[pump_point],
        crs=crs,
    )
    pump_gdf.to_file(pump_path)

def make_roads(
    roads_path: Path,
    road_edges_path: Path,
    city_bbox,
    river_corridor,
    crs,
    road_width: float = 40.0,   # ★ 幅20mに修正
):
    """
    - roads_path: 道路中心線(LineString)
    - road_edges_path: 道路面ポリゴン(長方形)
    """

    xmin_u, xmax_u, ymin_u, ymax_u = city_bbox
    x_river_c, river_w = river_corridor

    roads_center = []   # LineString
    roads_polygons = [] # Polygon
    road_ids = []

    road_spacing = 200.0
    avoid_half_width = river_w / 2.0 + 30.0  # 河川コリドー＋余白

    half_w = road_width / 2.0  # = 10.0 m

    x_vals = np.arange(xmin_u, xmax_u + 1e-6, road_spacing)
    y_vals = np.arange(ymin_u, ymax_u + 1e-6, road_spacing)

    x_used = []
    y_used = []

    rid = 0

    # --- 縦道路（南北方向） ---
    for x0 in x_vals:
        if abs(x0 - x_river_c) < avoid_half_width:
            continue

        # 中心線：city_bbox 全体まで
        line = LineString([(x0, ymin_u), (x0, ymax_u)])
        roads_center.append(line)

        # ポリゴン：city_bbox 全体まで
        poly = Polygon([
            (x0 - half_w, ymin_u - half_w),
            (x0 + half_w, ymin_u - half_w),
            (x0 + half_w, ymax_u + half_w),
            (x0 - half_w, ymax_u + half_w),
        ])
        roads_polygons.append(poly)

        road_ids.append(rid)
        x_used.append(x0)
        rid += 1

    # --- 横道路（東西方向） ---
    for y0 in y_vals:
        # 中心線：city_bbox 全体
        line = LineString([(xmin_u, y0), (xmax_u, y0)])
        roads_center.append(line)

        # ポリゴン：city_bbox 全体
        poly = Polygon([
            (xmin_u - half_w, y0 - half_w),
            (xmax_u + half_w, y0 - half_w),
            (xmax_u + half_w, y0 + half_w),
            (xmin_u - half_w, y0 + half_w),
        ])
        roads_polygons.append(poly)

        road_ids.append(rid)
        y_used.append(y0)
        rid += 1

    # --- 河川両岸道路（縦） ---
    bank_offset = 20.0
    x_left_bank = max(x_river_c - (river_w / 2.0 + bank_offset), xmin_u)
    x_right_bank = min(x_river_c + (river_w / 2.0 + bank_offset), xmax_u)

    for x0 in [x_left_bank, x_right_bank]:
        line = LineString([(x0, ymin_u), (x0, ymax_u)])
        roads_center.append(line)

        poly = Polygon([
            (x0 - half_w, ymin_u - half_w),
            (x0 + half_w, ymin_u - half_w),
            (x0 + half_w, ymax_u + half_w),
            (x0 - half_w, ymax_u + half_w),
        ])
        roads_polygons.append(poly)

        road_ids.append(rid)
        x_used.append(x0)
        rid += 1

    # --- 橋 1 本（横） ---
    y_bridge = 0.5 * (ymin_u + ymax_u)
    line = LineString([(xmin_u, y_bridge), (xmax_u, y_bridge)])
    roads_center.append(line)

    poly = Polygon([
        (xmin_u - half_w, y_bridge - half_w),
        (xmax_u + half_w, y_bridge - half_w),
        (xmax_u + half_w, y_bridge + half_w),
        (xmin_u - half_w, y_bridge + half_w),
    ])
    roads_polygons.append(poly)

    road_ids.append(rid)
    y_used.append(y_bridge)
    rid += 1

    # --- 出力 ---
    roads_center_gdf = gpd.GeoDataFrame(
        {"road_id": road_ids},
        geometry=roads_center,
        crs=crs,
    )
    roads_center_gdf.to_file(roads_path)

    roads_edges_gdf = gpd.GeoDataFrame(
        {"road_id": road_ids},
        geometry=roads_polygons,
        crs=crs,
    )
    roads_edges_gdf.to_file(road_edges_path)

    # 下水道用：
    x_roads = np.array(sorted(set(x_used)))
    y_roads = np.array(sorted(set(y_used)))
    return x_roads, y_roads

def make_sewer_nodes_and_links(nodes_path: Path, links_path: Path,
                               x_roads, y_roads,
                               city_bbox, river_corridor, crs):
    xmin_u, xmax_u, ymin_u, ymax_u = city_bbox
    x_river_c, river_w = river_corridor

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
            # 河川＋余白の内側にはマンホールを置かない
            if abs(x - x_river_c) < river_w / 2.0 + 30.0:
                continue

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

def make_city_blocks_and_river_gaps(
    blocks_path: Path,
    river_gap_path: Path,
    city_bbox,
    x_roads,
    y_roads,
    x_river_c: float,
    river_attr_width: float,
    road_width: float,
    crs,
):
    """
    city エリア内で：
      1) 道路縁に囲まれたブロックポリゴン
      2) 道路縁と河川ポリゴンの間の長方形ポリゴン
    を生成して shapefile 出力する。
    """

    xmin_u, xmax_u, ymin_u, ymax_u = city_bbox

    # 一応ソート & 重複除去
    x_list = np.array(sorted(set(x_roads)))
    y_list = np.array(sorted(set(y_roads)))

    half_w = road_width / 2.0

    # 河川ポリゴンの左右端
    x_river_min = x_river_c - river_attr_width / 2.0
    x_river_max = x_river_c + river_attr_width / 2.0

    # ─────────────────────────
    # 1) 道路縁で囲まれた通常ブロック
    # ─────────────────────────
    block_polys = []
    block_ids = []
    bid = 0

    for i in range(len(x_list) - 1):
        # この2本の縦道路の間にできる「ブロック」の x 範囲
        x_left = x_list[i]     + half_w
        x_right = x_list[i+1]  - half_w
        if x_right <= x_left:
            continue

        for j in range(len(y_list) - 1):
            # この2本の横道路の間にできる「ブロック」の y 範囲
            y_bottom = y_list[j]    + half_w
            y_top    = y_list[j+1]  - half_w
            if y_top <= y_bottom:
                continue

            # このブロックが河川領域と重なるかチェック
            # → 重なるものは「通常ブロック」から除外（後で river_gap 側で扱う）
            if not (x_right <= x_river_min or x_left >= x_river_max):
                # x 範囲が [x_river_min, x_river_max] と交差する
                continue

            poly = Polygon([
                (x_left,  y_bottom),
                (x_right, y_bottom),
                (x_right, y_top),
                (x_left,  y_top),
            ])

            block_polys.append(poly)
            block_ids.append(bid)
            bid += 1

    blocks_gdf = gpd.GeoDataFrame(
        {"block_id": block_ids},
        geometry=block_polys,
        crs=crs,
    )
    blocks_gdf.to_file(blocks_path)

    # ─────────────────────────
    # 2) 道路縁と河川ポリゴンの間の長方形（左右両岸）
    # ─────────────────────────
    # x_roads から河川の左右に最も近い道路（両岸道路）を推定
    # （既に left/right bank を別途持っているなら、それを渡してもOK）
    x_left_bank_candidates  = [x for x in x_list if x < x_river_c]
    x_right_bank_candidates = [x for x in x_list if x > x_river_c]
    if not x_left_bank_candidates or not x_right_bank_candidates:
        print("Warning: could not find left/right bank roads from x_roads")
        river_gap_gdf = gpd.GeoDataFrame(
            {"gap_id": [], "side": []},
            geometry=[],
            crs=crs,
        )
        river_gap_gdf.to_file(river_gap_path)
        return

    x_left_bank  = max(x_left_bank_candidates)
    x_right_bank = min(x_right_bank_candidates)

    gap_polys = []
    gap_ids = []
    gap_side = []   # 'left' or 'right'
    gid = 0

    for j in range(len(y_list) - 1):
        y_bottom = y_list[j]    + half_w
        y_top    = y_list[j+1]  - half_w
        if y_top <= y_bottom:
            continue

        # 左岸側：左岸道路の内側端 → 河川ポリゴン左端
        x1_left = x_left_bank + half_w   # 道路縁の「川側」の端
        x2_left = x_river_min           # 河川ポリゴン左端

        if x2_left > x1_left:
            poly_left = Polygon([
                (x1_left, y_bottom),
                (x2_left, y_bottom),
                (x2_left, y_top),
                (x1_left, y_top),
            ])
            gap_polys.append(poly_left)
            gap_ids.append(gid)
            gap_side.append("left")
            gid += 1

        # 右岸側：河川ポリゴン右端 → 右岸道路の内側端
        x1_right = x_river_max          # 河川ポリゴン右端
        x2_right = x_right_bank - half_w  # 道路縁の「川側」の端

        if x2_right > x1_right:
            poly_right = Polygon([
                (x1_right, y_bottom),
                (x2_right, y_bottom),
                (x2_right, y_top),
                (x1_right, y_top),
            ])
            gap_polys.append(poly_right)
            gap_ids.append(gid)
            gap_side.append("right")
            gid += 1

    river_gap_gdf = gpd.GeoDataFrame(
        {
            "gap_id": gap_ids,
            "side": gap_side,  # 'left' or 'right'
        },
        geometry=gap_polys,
        crs=crs,
    )
    river_gap_gdf.to_file(river_gap_path)


def main():
    base_dir = Path(__file__).resolve().parent
    dem_dir, layers_dir = create_directories(base_dir)

    dem_path = dem_dir / "7artificial_dem_epsg6677.tif"
    roads_path = layers_dir / "roads7.shp"
    road_edges_path = layers_dir / "roads_edges7.shp"
    nodes_path = layers_dir / "sewer_nodes7.shp"
    links_path = layers_dir / "sewer_links7.shp"
    river_center_path = layers_dir / "river_center7.shp"
    river_polygon_path = layers_dir / "river_polygon7.shp"
    pump_path = layers_dir / "pump_station7.shp"   # 追加
    blocks_path = layers_dir / "city_blocks7.shp"
    river_gap_path = layers_dir / "river_gaps7.shp"

    xmin, xmax, ymin, ymax, dx, dy, crs = make_dem(dem_path, epsg=6677)
    print(f"DEM saved to: {dem_path}")
    print(f"DEM Extent X: {xmin} 〜 {xmax}")
    print(f"DEM Extent Y: {ymin} 〜 {ymax}")
    print(f"CRS: {crs.to_string()}")

    margin = 500.0
    xmin_u = xmin + margin
    xmax_u = xmax - margin
    ymin_u = ymin + margin
    ymax_u = ymax - margin
    city_bbox = (xmin_u, xmax_u, ymin_u, ymax_u)

    # 河川コリドー（縦方向の空白帯）
    x_river_c = 0.5 * (xmin_u + xmax_u)
    river_w = 100.0
    river_corridor = (x_river_c, river_w)

    # 河川：中心線＋30m 幅ポリゴン＋下流端ポンプ場
    make_river_rectangular(
        river_center_path,
        river_polygon_path,
        pump_path,
        city_bbox,
        x_river_c,
        river_attr_width=40.0,
        ymax_dem=ymax,
        crs=crs,      
    )
    print(f"River centerline saved to: {river_center_path}")
    print(f"River polygon (width 30m) saved to: {river_polygon_path}")
    print(f"Pump station saved to: {pump_path}")

    # 道路＋道路縁
    x_roads, y_roads = make_roads(
        roads_path,
        road_edges_path,
        city_bbox,
        river_corridor,
        crs,
        road_width=40.0,
    )


    # # 道路生成
    # x_roads, y_roads = make_roads(roads_path, city_bbox, river_corridor, crs)
    # print(f"Roads saved to: {roads_path}")
    # # 道路縁ポリゴン
    # make_road_edges(roads_path, road_edges_path, width=10.0)
    # print(f"Road edges saved to: {road_edges_path}")
    
    # 下水道ノード＆リンク生成
    make_sewer_nodes_and_links(
        nodes_path, links_path,
        x_roads, y_roads,
        city_bbox, river_corridor, crs
    )
    print(f"Sewer nodes saved to: {nodes_path}")
    print(f"Sewer links saved to: {links_path}")
    make_city_blocks_and_river_gaps(
    blocks_path=blocks_path,
    river_gap_path=river_gap_path,
    city_bbox=city_bbox,
    x_roads=x_roads,
    y_roads=y_roads,
    x_river_c=x_river_c,
    river_attr_width=40.0,
    road_width=40.0,
    crs=crs,
    )
    print(f"City blocks saved to: {blocks_path}")
    print(f"River-side gaps saved to: {river_gap_path}")


if __name__ == "__main__":
    main()
