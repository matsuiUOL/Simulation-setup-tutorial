import numpy as np
import rasterio
import pandas as pd
from rasterio.transform import from_origin
from rasterio.crs import CRS
import geopandas as gpd
from shapely.geometry import LineString, Point, Polygon
from shapely.ops import unary_union
from pathlib import Path


def create_directories(base_dir: Path):
    dem_dir = base_dir / "01_DEM" / "city_confluence_v3"
    layers_dir = base_dir / "02_GIS_layers" / "city_confluence_v3"
    dem_dir.mkdir(parents=True, exist_ok=True)
    layers_dir.mkdir(parents=True, exist_ok=True)
    return dem_dir, layers_dir


def make_dem(dem_path: Path, epsg: int = 6677):
    dx = 5.0
    dy = 5.0
    nx = 600
    ny = 600

    origin_x = 152000.0
    origin_y = 505000.0

    transform = from_origin(origin_x, origin_y, dx, dy)
    crs = CRS.from_epsg(epsg)

    dem = np.full((ny, nx), 0.0, dtype="float32")

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


def make_river_confluence_rectangular(
    river_center_path: Path,
    river_polygon_path: Path,
    pump_path: Path,
    city_bbox,
    dem_bbox,
    crs,
    main_width: float = 30.0,
    trib_width: float = 15.0,
):
    """
    本川:
      - 中央を南北に流れる長方形
      - 河道ポリゴン端は DEM 領域端と一致
    支川:
      - 左端から本川へ水平に接続する長方形
      - 河道ポリゴン端は DEM 左端と一致
    """

    xmin_u, xmax_u, ymin_u, ymax_u = city_bbox
    xmin_dem, xmax_dem, ymin_dem, ymax_dem = dem_bbox

    x_main = 0.5 * (xmin_u + xmax_u)
    y_junc = ymin_u + 0.50 * (ymax_u - ymin_u)

    # 本川
    hw_main = main_width / 2.0
    main_line = LineString([(x_main, ymin_dem), (x_main, ymax_dem)])
    main_poly = Polygon([
        (x_main - hw_main, ymin_dem),
        (x_main + hw_main, ymin_dem),
        (x_main + hw_main, ymax_dem),
        (x_main - hw_main, ymax_dem),
    ])

    # 支川（左端から）
    hw_trib = trib_width / 2.0
    trib_line = LineString([(xmin_dem, y_junc), (x_main, y_junc)])
    trib_poly = Polygon([
        (xmin_dem, y_junc - hw_trib),
        (x_main,   y_junc - hw_trib),
        (x_main,   y_junc + hw_trib),
        (xmin_dem, y_junc + hw_trib),
    ])

    river_poly = unary_union([main_poly, trib_poly])

    river_center_gdf = gpd.GeoDataFrame(
        {
            "river_id": [0, 1],
            "name": ["main", "trib"],
            "width_m": [main_width, trib_width],
        },
        geometry=[main_line, trib_line],
        crs=crs,
    )
    river_center_gdf.to_file(river_center_path)

    river_poly_gdf = gpd.GeoDataFrame(
        {
            "river_id": [0],
            "landuse": ["river"],
        },
        geometry=[river_poly],
        crs=crs,
    )
    river_poly_gdf.to_file(river_polygon_path)

    pump_point = Point(x_main, ymax_dem)
    pump_gdf = gpd.GeoDataFrame(
        {
            "pump_id": [0],
            "type": ["pump_station"],
        },
        geometry=[pump_point],
        crs=crs,
    )
    pump_gdf.to_file(pump_path)

    return {
        "x_main": x_main,
        "y_junc": y_junc,
        "main_width": main_width,
        "trib_width": trib_width,
        "river_geom": river_poly,
    }


def make_roads_confluence(
    roads_path: Path,
    road_edges_path: Path,
    city_bbox,
    river_info,
    crs,
    road_width: float = 40.0,
    road_spacing: float = 200.0,
    main_gap_width: float = 20.0,
):
    """
    道路中心線は交差点-交差点区間で生成。
    道路縁は各区間buffer後に dissolve。

    追加:
      - 支川最近傍の半分建物ブロックの外周に対応する横道路を追加
    """

    from shapely.ops import unary_union

    xmin_u, xmax_u, ymin_u, ymax_u = city_bbox
    x_main = river_info["x_main"]
    y_junc = river_info["y_junc"]
    main_width = river_info["main_width"]
    trib_width = river_info["trib_width"]
    river_geom = river_info["river_geom"]

    half_w = road_width / 2.0

    x_vals = np.arange(xmin_u, xmax_u + 1e-6, road_spacing)
    y_vals = np.arange(ymin_u, ymax_u + 1e-6, road_spacing)

    def explode_polygons(geom):
        if geom.is_empty:
            return []
        if geom.geom_type == "Polygon":
            return [geom]
        if geom.geom_type == "MultiPolygon":
            return list(geom.geoms)
        if geom.geom_type == "GeometryCollection":
            out = []
            for g in geom.geoms:
                if g.geom_type == "Polygon":
                    out.append(g)
                elif g.geom_type == "MultiPolygon":
                    out.extend(list(g.geoms))
            return out
        return []

    # -----------------------------
    # 本川両岸道路の中心位置
    # -----------------------------
    x_left_bank = x_main - (main_width / 2.0 + main_gap_width + half_w)
    x_right_bank = x_main + (main_width / 2.0 + main_gap_width + half_w)

    avoid_half_main = main_width / 2.0 + main_gap_width + road_width

    x_regular = [x for x in x_vals if abs(x - x_main) >= avoid_half_main]
    x_axes = sorted(set([round(x, 6) for x in x_regular] +
                        [round(x_left_bank, 6), round(x_right_bank, 6)]))
    y_axes = sorted(set([round(y, 6) for y in y_vals]))

    roads_center = []

    def add_segment(line):
        if line.buffer(1e-6).intersects(river_geom):
            return
        roads_center.append(line)

    # --------------------------------
    # 縦道路
    # --------------------------------
    for x0 in x_axes:
        for j in range(len(y_axes) - 1):
            y1 = y_axes[j]
            y2 = y_axes[j + 1]
            line = LineString([(x0, y1), (x0, y2)])
            add_segment(line)

    # --------------------------------
    # 横道路
    # --------------------------------
    for y0 in y_axes:
        for i in range(len(x_axes) - 1):
            x1 = x_axes[i]
            x2 = x_axes[i + 1]
            line = LineString([(x1, y0), (x2, y0)])
            add_segment(line)

    # --------------------------------
    # 支川最近傍半分ブロックの外周用の道路を追加
    #   - 横方向
    #   - 縦方向
    # --------------------------------
    y_trib_b = y_junc - trib_width / 2.0
    y_trib_t = y_junc + trib_width / 2.0

    y_lower_candidates = [y for y in y_axes if y < y_trib_b]
    y_upper_candidates = [y for y in y_axes if y > y_trib_t]

    y_lower_road = max(y_lower_candidates) if y_lower_candidates else None
    y_upper_road = min(y_upper_candidates) if y_upper_candidates else None

    if (y_lower_road is not None) and (y_upper_road is not None):
        # 支川最近傍の帯の中央
        y_lower_mid = 0.5 * ((y_lower_road + half_w) + y_trib_b)
        y_upper_mid = 0.5 * (y_trib_t + (y_upper_road - half_w))

        # 左側（支川区間）のみ
        x_sub_axes = [x for x in x_axes if x < x_main] + [x_main]
        x_sub_axes = sorted(set([round(x, 6) for x in x_sub_axes]))

        # ---- 横方向の補助道路 ----
        for y0 in [y_lower_mid, y_upper_mid]:
            for i in range(len(x_sub_axes) - 1):
                x1 = x_sub_axes[i]
                x2 = x_sub_axes[i + 1]
                line = LineString([(x1, y0), (x2, y0)])
                add_segment(line)

        # ---- 縦方向の補助道路 ----
        # 各 x 軸位置で、最近傍帯の上下それぞれに縦線を入れる
        for x0 in x_sub_axes:
            # 下側帯
            line_low = LineString([(x0, y_lower_road), (x0, y_lower_mid)])
            add_segment(line_low)

            # 上側帯
            line_up = LineString([(x0, y_upper_mid), (x0, y_upper_road)])
            add_segment(line_up)

    # --------------------------------
    # 中心線出力
    # --------------------------------
    roads_center_gdf = gpd.GeoDataFrame(
        {"road_id": list(range(len(roads_center)))},
        geometry=roads_center,
        crs=crs,
    )
    roads_center_gdf.to_file(roads_path)

    # --------------------------------
    # 道路縁ポリゴン
    # --------------------------------
    road_buffers = []
    for ln in roads_center:
        pg = ln.buffer(half_w, cap_style=3, join_style=2)
        if not pg.is_empty and pg.area > 1.0:
            road_buffers.append(pg)

    road_union = unary_union(road_buffers).buffer(0)
    road_polys = [pg for pg in explode_polygons(road_union) if pg.area > 1.0]

    roads_edges_gdf = gpd.GeoDataFrame(
        {"road_id": list(range(len(road_polys)))},
        geometry=road_polys,
        crs=crs,
    )
    roads_edges_gdf.to_file(road_edges_path)

    x_roads = np.array(x_axes)
    y_roads = np.array(y_axes)

    return x_roads, y_roads, roads_center_gdf, roads_edges_gdf


def make_sewer_nodes_and_links_from_intersections(
    nodes_path: Path,
    links_path: Path,
    roads_center_gdf,
    crs,
    tol=1e-8,
):
    """
    道路交点と端点に必ず node を置く
    """
    lines = list(roads_center_gdf.geometry)

    pts = []

    # 端点
    for ln in lines:
        coords = list(ln.coords)
        pts.append(Point(coords[0]))
        pts.append(Point(coords[-1]))

    # 交点
    for i in range(len(lines)):
        for j in range(i + 1, len(lines)):
            inter = lines[i].intersection(lines[j])
            if inter.is_empty:
                continue
            if inter.geom_type == "Point":
                pts.append(inter)
            elif inter.geom_type == "MultiPoint":
                pts.extend(list(inter.geoms))

    def pkey(p):
        return (round(p.x, 6), round(p.y, 6))

    uniq = {}
    for p in pts:
        uniq[pkey(p)] = p

    node_points = list(uniq.values())
    node_ids = list(range(len(node_points)))

    nodes_gdf = gpd.GeoDataFrame(
        {"node_id": node_ids},
        geometry=node_points,
        crs=crs,
    )
    nodes_gdf.to_file(nodes_path)

    point_lookup = {pkey(p): i for i, p in enumerate(node_points)}

    link_geoms = []
    start_ids = []
    end_ids = []

    for ln in lines:
        pts_on_line = []
        for p in node_points:
            if ln.distance(p) < tol:
                pts_on_line.append(p)

        if len(pts_on_line) < 2:
            continue

        pts_on_line = sorted(pts_on_line, key=lambda p: ln.project(p))

        for p1, p2 in zip(pts_on_line[:-1], pts_on_line[1:]):
            if p1.distance(p2) < tol:
                continue
            link_geoms.append(LineString([p1, p2]))
            start_ids.append(point_lookup[pkey(p1)])
            end_ids.append(point_lookup[pkey(p2)])

    links_gdf = gpd.GeoDataFrame(
        {
            "link_id": list(range(len(link_geoms))),
            "start_id": start_ids,
            "end_id": end_ids,
        },
        geometry=link_geoms,
        crs=crs,
    )
    links_gdf.to_file(links_path)


def make_city_blocks_and_river_gaps_confluence(
    blocks_path: Path,
    river_gap_path: Path,
    city_bbox,
    x_roads,
    y_roads,
    river_info,
    road_width: float,
    crs,
):
    """
    従来コードの拡張版。
    - 本川周辺: 左右に river_gap
    - 支川周辺: 上下に river_gap
    - 支川最近傍の建物ブロックのみ y方向半分サイズ
    """

    xmin_u, xmax_u, ymin_u, ymax_u = city_bbox
    x_main = river_info["x_main"]
    y_junc = river_info["y_junc"]
    main_width = river_info["main_width"]
    trib_width = river_info["trib_width"]
    river_geom = river_info["river_geom"]

    x_list = np.array(sorted(set(x_roads)))
    y_list = np.array(sorted(set(y_roads)))
    half_w = road_width / 2.0

    # 河川端
    x_main_l = x_main - main_width / 2.0
    x_main_r = x_main + main_width / 2.0
    y_trib_b = y_junc - trib_width / 2.0
    y_trib_t = y_junc + trib_width / 2.0

    # 支川のすぐ上下にある既存道路を採用
    y_lower_candidates = [y for y in y_list if y < y_trib_b]
    y_upper_candidates = [y for y in y_list if y > y_trib_t]

    y_lower_road = max(y_lower_candidates) if y_lower_candidates else None
    y_upper_road = min(y_upper_candidates) if y_upper_candidates else None

    # 支川最近傍ブロックの上下境界
    # 下側: [y_lower_road, y_trib_b] の間
    # 上側: [y_trib_t, y_upper_road] の間
    lower_band_exists = (y_lower_road is not None)
    upper_band_exists = (y_upper_road is not None)

    # --------------------------------------------------
    # 1) 通常ブロック
    # --------------------------------------------------
    block_polys = []
    block_ids = []
    btype = []
    bid = 0

    def add_block(poly, kind="normal"):
        nonlocal bid
        if poly.is_empty:
            return
        if poly.area <= 1.0:
            return
        block_polys.append(poly)
        block_ids.append(bid)
        btype.append(kind)
        bid += 1

    for i in range(len(x_list) - 1):
        x_left = x_list[i] + half_w
        x_right = x_list[i + 1] - half_w
        if x_right <= x_left:
            continue

        for j in range(len(y_list) - 1):
            y_bottom = y_list[j] + half_w
            y_top = y_list[j + 1] - half_w
            if y_top <= y_bottom:
                continue

            # 本川と重なるものは除外
            if not (x_right <= x_main_l or x_left >= x_main_r):
                continue

            # 支川本体と重なるものは除外
            if x_left < x_main:
                if not (y_top <= y_trib_b or y_bottom >= y_trib_t):
                    continue

            # ---- 支川最近傍の上下バンドを特別処理 ----
            # 左側（支川区間）だけ、最近傍ブロックを y方向半分サイズにする
            if x_left < x_main:
                # 下側最近傍帯
                if lower_band_exists and (y_bottom >= y_lower_road + half_w - 1e-9) and (y_top <= y_trib_b + 1e-9):
                    h = y_top - y_bottom
                    if h > 0:
                        y_mid = 0.5 * (y_bottom + y_top)
                        # 下側帯では、支川から遠い側（下側）に半分サイズの建物
                        y1 = y_bottom
                        y2 = y_mid
                        if y2 > y1:
                            poly = Polygon([
                                (x_left, y1),
                                (x_right, y1),
                                (x_right, y2),
                                (x_left, y2),
                            ])
                            add_block(poly, kind="trib_near_lower_half")
                    continue

                # 上側最近傍帯
                if upper_band_exists and (y_bottom >= y_trib_t - 1e-9) and (y_top <= y_upper_road - half_w + 1e-9):
                    h = y_top - y_bottom
                    if h > 0:
                        y_mid = 0.5 * (y_bottom + y_top)
                        # 上側帯では、支川から遠い側（上側）に半分サイズの建物
                        y1 = y_mid
                        y2 = y_top
                        if y2 > y1:
                            poly = Polygon([
                                (x_left, y1),
                                (x_right, y1),
                                (x_right, y2),
                                (x_left, y2),
                            ])
                            add_block(poly, kind="trib_near_upper_half")
                    continue

            # ---- 通常ブロック ----
            poly = Polygon([
                (x_left, y_bottom),
                (x_right, y_bottom),
                (x_right, y_top),
                (x_left, y_top),
            ])
            add_block(poly, kind="normal")

    blocks_gdf = gpd.GeoDataFrame(
        {"block_id": block_ids, "btype": btype},
        geometry=block_polys,
        crs=crs,
    )
    blocks_gdf.to_file(blocks_path)

    # --------------------------------------------------
    # 2) river_gap
    # --------------------------------------------------
    gap_polys = []
    gap_ids = []
    gap_type = []
    gid = 0

    # ---- 本川左右 ----
    x_left_candidates = [x for x in x_list if x < x_main]
    x_right_candidates = [x for x in x_list if x > x_main]

    if x_left_candidates and x_right_candidates:
        x_left_bank = max(x_left_candidates)
        x_right_bank = min(x_right_candidates)

        x1_left = x_left_bank + half_w
        x2_left = x_main_l

        x1_right = x_main_r
        x2_right = x_right_bank - half_w

        for j in range(len(y_list) - 1):
            y_bottom = y_list[j] + half_w
            y_top = y_list[j + 1] - half_w
            if y_top <= y_bottom:
                continue

            if x2_left > x1_left:
                poly_left = Polygon([
                    (x1_left, y_bottom),
                    (x2_left, y_bottom),
                    (x2_left, y_top),
                    (x1_left, y_top),
                ])
                if poly_left.area > 1.0:
                    gap_polys.append(poly_left)
                    gap_ids.append(gid)
                    gap_type.append("main_left")
                    gid += 1

            if x2_right > x1_right:
                poly_right = Polygon([
                    (x1_right, y_bottom),
                    (x2_right, y_bottom),
                    (x2_right, y_top),
                    (x1_right, y_top),
                ])
                if poly_right.area > 1.0:
                    gap_polys.append(poly_right)
                    gap_ids.append(gid)
                    gap_type.append("main_right")
                    gid += 1

    # ---- 支川上下 ----
    if (y_lower_road is not None) and (y_upper_road is not None):
        y1_low = y_lower_road + half_w
        y2_low = y_trib_b

        y1_up = y_trib_t
        y2_up = y_upper_road - half_w

        for i in range(len(x_list) - 1):
            x_left = x_list[i] + half_w
            x_right = x_list[i + 1] - half_w
            if x_right <= x_left:
                continue

            if x_left >= x_main:
                continue

            xL = max(x_left, xmin_u)
            xR = min(x_right, x_main)
            if xR <= xL:
                continue

            if y2_low > y1_low:
                poly_low = Polygon([
                    (xL, y1_low),
                    (xR, y1_low),
                    (xR, y2_low),
                    (xL, y2_low),
                ])
                if poly_low.area > 1.0:
                    gap_polys.append(poly_low)
                    gap_ids.append(gid)
                    gap_type.append("trib_lower")
                    gid += 1

            if y2_up > y1_up:
                poly_up = Polygon([
                    (xL, y1_up),
                    (xR, y1_up),
                    (xR, y2_up),
                    (xL, y2_up),
                ])
                if poly_up.area > 1.0:
                    gap_polys.append(poly_up)
                    gap_ids.append(gid)
                    gap_type.append("trib_upper")
                    gid += 1

    river_gap_gdf = gpd.GeoDataFrame(
        {
            "gap_id": gap_ids,
            "gtype": gap_type,
        },
        geometry=gap_polys,
        crs=crs,
    )
    river_gap_gdf.to_file(river_gap_path)

    return blocks_gdf, river_gap_gdf

def make_river_side_gap_polygons(
    gap_path: Path,
    city_bbox,
    x_roads,
    y_roads,
    river_info,
    crs,
    road_width: float = 40.0,
):
    """
    河川と最近傍道路の間の river_gap を、街区ごとの長方形として明示的に作る。
    端部は road_width/2 だけ延長する。
    """

    xmin_u, xmax_u, ymin_u, ymax_u = city_bbox
    x_main = river_info["x_main"]
    y_junc = river_info["y_junc"]
    main_width = river_info["main_width"]
    trib_width = river_info["trib_width"]

    x_list = np.array(sorted(set(x_roads)))
    y_list = np.array(sorted(set(y_roads)))

    half_w = road_width / 2.0

    # 河川端
    x_main_l = x_main - main_width / 2.0
    x_main_r = x_main + main_width / 2.0
    y_trib_b = y_junc - trib_width / 2.0
    y_trib_t = y_junc + trib_width / 2.0

    gap_polys = []
    gap_ids = []
    gap_type = []
    gid = 0

    # ==================================================
    # 1) 本川左右の gap
    # ==================================================
    x_left_candidates = [x for x in x_list if x < x_main]
    x_right_candidates = [x for x in x_list if x > x_main]

    if x_left_candidates and x_right_candidates:
        x_left_bank = max(x_left_candidates)
        x_right_bank = min(x_right_candidates)

        # 道路の川側端
        x1_left = x_left_bank + half_w
        x2_left = x_main_l

        x1_right = x_main_r
        x2_right = x_right_bank - half_w

        for j in range(len(y_list) - 1):
            # 端部を half_w だけ延長
            y_bottom = y_list[j] - half_w
            y_top = y_list[j + 1] + half_w

            if y_top <= y_bottom:
                continue

            if x2_left > x1_left:
                poly_left = Polygon([
                    (x1_left, y_bottom),
                    (x2_left, y_bottom),
                    (x2_left, y_top),
                    (x1_left, y_top),
                ])
                if poly_left.area > 1.0:
                    gap_polys.append(poly_left)
                    gap_ids.append(gid)
                    gap_type.append("main_left_gap")
                    gid += 1

            if x2_right > x1_right:
                poly_right = Polygon([
                    (x1_right, y_bottom),
                    (x2_right, y_bottom),
                    (x2_right, y_top),
                    (x1_right, y_top),
                ])
                if poly_right.area > 1.0:
                    gap_polys.append(poly_right)
                    gap_ids.append(gid)
                    gap_type.append("main_right_gap")
                    gid += 1

    # ==================================================
    # 2) 支川上下の gap
    # ==================================================
    y_lower_candidates = [y for y in y_list if y < y_trib_b]
    y_upper_candidates = [y for y in y_list if y > y_trib_t]

    if y_lower_candidates and y_upper_candidates:
        y_lower_road = max(y_lower_candidates)
        y_upper_road = min(y_upper_candidates)

        # 道路の川側端
        y1_low = y_lower_road + half_w
        y2_low = y_trib_b

        y1_up = y_trib_t
        y2_up = y_upper_road - half_w

        for i in range(len(x_list) - 1):
            # 支川区間は左半分のみ
            if x_list[i] >= x_main:
                continue

            # 端部を half_w だけ延長
            x_left = x_list[i] - half_w
            x_right = x_list[i + 1] + half_w

            xL = max(x_left, xmin_u)
            xR = min(x_right, x_main)

            if xR <= xL:
                continue

            if y2_low > y1_low:
                poly_low = Polygon([
                    (xL, y1_low),
                    (xR, y1_low),
                    (xR, y2_low),
                    (xL, y2_low),
                ])
                if poly_low.area > 1.0:
                    gap_polys.append(poly_low)
                    gap_ids.append(gid)
                    gap_type.append("trib_lower_gap")
                    gid += 1

            if y2_up > y1_up:
                poly_up = Polygon([
                    (xL, y1_up),
                    (xR, y1_up),
                    (xR, y2_up),
                    (xL, y2_up),
                ])
                if poly_up.area > 1.0:
                    gap_polys.append(poly_up)
                    gap_ids.append(gid)
                    gap_type.append("trib_upper_gap")
                    gid += 1

    gap_gdf = gpd.GeoDataFrame(
        {
            "gap_id": gap_ids,
            "gtype": gap_type,
        },
        geometry=gap_polys,
        crs=crs,
    )
    gap_gdf.to_file(gap_path)

    return gap_gdf
def make_gap_corner_points(
    csv_path,
    x_roads,
    y_roads,
    river_info,
    road_width=40.0,
):

    x_main = river_info["x_main"]
    y_junc = river_info["y_junc"]
    main_width = river_info["main_width"]
    trib_width = river_info["trib_width"]

    half = road_width/2

    # 本川両岸道路
    x_left = max([x for x in x_roads if x < x_main])
    x_right = min([x for x in x_roads if x > x_main])

    # 支川上下道路
    y_low = max([y for y in y_roads if y < y_junc])
    y_up = min([y for y in y_roads if y > y_junc])

    pts = []

    # ---- 本川周辺8点 ----
    for x in [x_left-half, x_left+half, x_right-half, x_right+half]:
        for y in [y_low-half, y_low+half]:
            pts.append((x,y,"main_lower"))

        for y in [y_up-half, y_up+half]:
            pts.append((x,y,"main_upper"))

    # ---- 支川4点 ----
    for x in [x_left-half, x_left+half]:
        pts.append((x,y_junc,"trib_left"))

    for x in [x_right-half, x_right+half]:
        pts.append((x,y_junc,"trib_right"))

    df = pd.DataFrame(pts,columns=["x","y","type"])
    df.to_csv(csv_path,index=False)

    return df

def main():
    base_dir = Path(__file__).resolve().parent
    dem_dir, layers_dir = create_directories(base_dir)

    dem_path = dem_dir / "artificial_dem_confluence_v2_epsg6677.tif"
    roads_path = layers_dir / "roads_confluence_v2.shp"
    road_edges_path = layers_dir / "roads_edges_confluence_v2.shp"
    nodes_path = layers_dir / "sewer_nodes_confluence_v2.shp"
    links_path = layers_dir / "sewer_links_confluence_v2.shp"
    river_center_path = layers_dir / "river_center_confluence_v2.shp"
    river_polygon_path = layers_dir / "river_polygon_confluence_v2.shp"
    pump_path = layers_dir / "pump_station_confluence_v2.shp"
    blocks_path = layers_dir / "city_blocks_confluence_v2.shp"
    river_gap_path = layers_dir / "river_gaps_confluence_v2.shp"
    gap_path = layers_dir / "river_side_gap_polygons.shp"

    xmin, xmax, ymin, ymax, dx, dy, crs = make_dem(dem_path, epsg=6677)
    dem_bbox = (xmin, xmax, ymin, ymax)

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

    river_info = make_river_confluence_rectangular(
        river_center_path=river_center_path,
        river_polygon_path=river_polygon_path,
        pump_path=pump_path,
        city_bbox=city_bbox,
        dem_bbox=dem_bbox,
        crs=crs,
        main_width=30.0,
        trib_width=15.0,
    )
    print(f"River centerline saved to: {river_center_path}")
    print(f"River polygon saved to: {river_polygon_path}")
    print(f"Pump station saved to: {pump_path}")

    x_roads, y_roads, roads_center_gdf, roads_edges_gdf = make_roads_confluence(
        roads_path=roads_path,
        road_edges_path=road_edges_path,
        city_bbox=city_bbox,
        river_info=river_info,
        crs=crs,
        road_width=40.0,
        road_spacing=200.0,
        # trib_gap_buffer=30.0,
    )
    print(f"Roads saved to: {roads_path}")
    print(f"Road edges saved to: {road_edges_path}")

    gap_gdf = make_river_side_gap_polygons(
        gap_path=gap_path,
        city_bbox=city_bbox,
        x_roads=x_roads,
        y_roads=y_roads,
        river_info=river_info,
        crs=crs,
        road_width=40.0,
    )
    print(f"River-side gap polygons saved to: {gap_path}")

    make_sewer_nodes_and_links_from_intersections(
        nodes_path=nodes_path,
        links_path=links_path,
        roads_center_gdf=roads_center_gdf,
        crs=crs,
    )
    print(f"Sewer nodes saved to: {nodes_path}")
    print(f"Sewer links saved to: {links_path}")

    blocks_gdf, river_gap_gdf = make_city_blocks_and_river_gaps_confluence(
        blocks_path=blocks_path,
        river_gap_path=river_gap_path,
        city_bbox=city_bbox,
        x_roads=x_roads,
        y_roads=y_roads,
        river_info=river_info,
        road_width=40.0,
        crs=crs,
        # trib_gap_buffer=30.0,
    )
    print(f"City blocks saved to: {blocks_path}")
    print(f"River gaps saved to: {river_gap_path}")
    
    csv_path = layers_dir / "gap_points.csv"

    df = make_gap_corner_points(
        csv_path,
        x_roads,
        y_roads,
        river_info,
        road_width=40.0
    )

    print(df)
    print("saved:",csv_path)

if __name__ == "__main__":
    main()