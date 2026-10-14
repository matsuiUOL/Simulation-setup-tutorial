import numpy as np
import rasterio
from rasterio.transform import from_origin
from rasterio.crs import CRS
import geopandas as gpd
from shapely.geometry import LineString, Point, Polygon
from shapely.ops import unary_union
from pathlib import Path


def create_directories(base_dir: Path):
    dem_dir = base_dir / "01_DEM" / "city_confluence_v2"
    layers_dir = base_dir / "02_GIS_layers" / "city_confluence_v2"
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
    y_junc = ymin_u + 0.58 * (ymax_u - ymin_u)

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
    trib_gap_buffer: float = 30.0,
    trib_suppress_extra: float = 120.0,
):
    """
    従来コードベースの修正版

    修正点:
      1) 支川近傍の通常横道路を広めの帯で完全に消す
      2) 支川上下の専用道路だけ追加
      3) 橋なし: 河川位置で line / polygon を必ず分割
      4) 支川用道路は xmin_u ～ x_main のみ
    """

    xmin_u, xmax_u, ymin_u, ymax_u = city_bbox
    x_main = river_info["x_main"]
    y_junc = river_info["y_junc"]
    main_width = river_info["main_width"]
    trib_width = river_info["trib_width"]
    river_geom = river_info["river_geom"]

    half_w = road_width / 2.0

    x_vals = np.arange(xmin_u, xmax_u + 1e-6, road_spacing)
    y_vals = np.arange(ymin_u, ymax_u + 1e-6, road_spacing)

    roads_center = []
    roads_polygons = []
    x_used = []
    y_used = []

    # --------------------------------------------------
    # utility
    # --------------------------------------------------
    def explode_lines(geom):
        if geom.is_empty:
            return []
        if geom.geom_type == "LineString":
            return [geom]
        if geom.geom_type == "MultiLineString":
            return list(geom.geoms)
        if geom.geom_type == "GeometryCollection":
            out = []
            for g in geom.geoms:
                if g.geom_type == "LineString":
                    out.append(g)
                elif g.geom_type == "MultiLineString":
                    out.extend(list(g.geoms))
            return out
        return []

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

    def add_cut_road(full_line, full_poly, axis_value=None, axis_type=None):
        """
        河川をまたがないように line/polygon を切って追加
        axis_type: 'x' or 'y' or None
        """
        line_cut = full_line.difference(river_geom)
        poly_cut = full_poly.difference(river_geom).buffer(0)

        line_parts = [seg for seg in explode_lines(line_cut) if seg.length > 20.0]
        poly_parts = [pg for pg in explode_polygons(poly_cut) if pg.area > 10.0]

        if not line_parts or not poly_parts:
            return

        for seg in line_parts:
            roads_center.append(seg)
            if axis_type == "x" and axis_value is not None:
                x_used.append(axis_value)
            if axis_type == "y" and axis_value is not None:
                y_used.append(axis_value)

        for pg in poly_parts:
            roads_polygons.append(pg)

    # --------------------------------------------------
    # 本川の回避設定
    # --------------------------------------------------
    avoid_half_main = main_width / 2.0 + 30.0

    # 支川上下の専用道路位置
    y_trib_lower_road = y_junc - trib_width / 2.0 - trib_gap_buffer
    y_trib_upper_road = y_junc + trib_width / 2.0 + trib_gap_buffer

    # 支川近傍の通常横道路を消す帯
    # かなり広めに消す
    suppress_band_min = y_trib_lower_road - trib_suppress_extra
    suppress_band_max = y_trib_upper_road + trib_suppress_extra

    # --------------------------------------------------
    # 1) 通常の縦道路
    # --------------------------------------------------
    for x0 in x_vals:
        # 本川近傍の縦道路は従来どおり除去
        if abs(x0 - x_main) < avoid_half_main:
            continue

        full_line = LineString([(x0, ymin_u), (x0, ymax_u)])
        full_poly = Polygon([
            (x0 - half_w, ymin_u - half_w),
            (x0 + half_w, ymin_u - half_w),
            (x0 + half_w, ymax_u + half_w),
            (x0 - half_w, ymax_u + half_w),
        ])

        add_cut_road(full_line, full_poly, axis_value=x0, axis_type="x")

    # --------------------------------------------------
    # 2) 通常の横道路
    #    支川近傍は広めに全部消す
    # --------------------------------------------------
    for y0 in y_vals:
        # 支川周辺は通常横道路を完全に作らない
        if suppress_band_min < y0 < suppress_band_max:
            continue

        full_line = LineString([(xmin_u, y0), (xmax_u, y0)])
        full_poly = Polygon([
            (xmin_u - half_w, y0 - half_w),
            (xmax_u + half_w, y0 - half_w),
            (xmax_u + half_w, y0 + half_w),
            (xmin_u - half_w, y0 + half_w),
        ])

        add_cut_road(full_line, full_poly, axis_value=y0, axis_type="y")

    # --------------------------------------------------
    # 3) 本川両岸道路（従来）
    # --------------------------------------------------
    bank_offset = 20.0
    x_left_bank = max(x_main - (main_width / 2.0 + bank_offset), xmin_u)
    x_right_bank = min(x_main + (main_width / 2.0 + bank_offset), xmax_u)

    for x0 in [x_left_bank, x_right_bank]:
        full_line = LineString([(x0, ymin_u), (x0, ymax_u)])
        full_poly = Polygon([
            (x0 - half_w, ymin_u - half_w),
            (x0 + half_w, ymin_u - half_w),
            (x0 + half_w, ymax_u + half_w),
            (x0 - half_w, ymax_u + half_w),
        ])

        add_cut_road(full_line, full_poly, axis_value=x0, axis_type="x")

    # --------------------------------------------------
    # 4) 支川上下の専用道路
    #    左半分だけ作る
    # --------------------------------------------------
    for y0 in [y_trib_lower_road, y_trib_upper_road]:
        full_line = LineString([(xmin_u, y0), (x_main, y0)])
        full_poly = Polygon([
            (xmin_u - half_w, y0 - half_w),
            (x_main + half_w, y0 - half_w),
            (x_main + half_w, y0 + half_w),
            (xmin_u - half_w, y0 + half_w),
        ])

        add_cut_road(full_line, full_poly, axis_value=y0, axis_type="y")

    # --------------------------------------------------
    # 出力
    # --------------------------------------------------
    roads_center_gdf = gpd.GeoDataFrame(
        {"road_id": list(range(len(roads_center)))},
        geometry=roads_center,
        crs=crs,
    )
    roads_center_gdf.to_file(roads_path)

    roads_edges_gdf = gpd.GeoDataFrame(
        {"road_id": list(range(len(roads_polygons)))},
        geometry=roads_polygons,
        crs=crs,
    )
    roads_edges_gdf.to_file(road_edges_path)

    x_roads = np.array(sorted(set(np.round(x_used, 6))))
    y_roads = np.array(sorted(set(np.round(y_used, 6))))

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
    trib_gap_buffer: float = 30.0,
):
    """
    従来コードを拡張:
      - 本川周辺は従来通り左右に river_gap
      - 支川周辺は上下に river_gap
      - それ以外は city blocks
    """

    xmin_u, xmax_u, ymin_u, ymax_u = city_bbox
    x_main = river_info["x_main"]
    y_junc = river_info["y_junc"]
    main_width = river_info["main_width"]
    trib_width = river_info["trib_width"]

    x_list = np.array(sorted(set(x_roads)))
    y_list = np.array(sorted(set(y_roads)))
    half_w = road_width / 2.0

    x_main_l = x_main - main_width / 2.0
    x_main_r = x_main + main_width / 2.0
    y_trib_b = y_junc - trib_width / 2.0
    y_trib_t = y_junc + trib_width / 2.0

    # 支川用の道路位置
    y_trib_lower_road = y_junc - trib_width / 2.0 - trib_gap_buffer
    y_trib_upper_road = y_junc + trib_width / 2.0 + trib_gap_buffer

    # =========================
    # 1) 通常ブロック
    # =========================
    block_polys = []
    block_ids = []
    bid = 0

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

            # 本川と重なるなら除外
            if not (x_right <= x_main_l or x_left >= x_main_r):
                continue

            # 支川と重なるなら除外（左側だけ）
            if x_left < x_main and x_right > xmin_u:
                if not (y_top <= y_trib_b or y_bottom >= y_trib_t):
                    continue

            # 支川の river_gap 帯とも重ならないようにする
            if x_left < x_main and x_right > xmin_u:
                # 下側 gap 帯
                if not (y_top <= y_trib_lower_road + half_w or y_bottom >= y_trib_b):
                    continue
                # 上側 gap 帯
                if not (y_top <= y_trib_t or y_bottom >= y_trib_upper_road - half_w):
                    continue

            poly = Polygon([
                (x_left, y_bottom),
                (x_right, y_bottom),
                (x_right, y_top),
                (x_left, y_top),
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

    # =========================
    # 2) river_gap
    # =========================
    gap_polys = []
    gap_ids = []
    gap_type = []
    gid = 0

    # ---- 本川左右（従来通り）----
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
                if poly_left.area > 0.0:
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
                if poly_right.area > 0.0:
                    gap_polys.append(poly_right)
                    gap_ids.append(gid)
                    gap_type.append("main_right")
                    gid += 1

    # ---- 支川上下 ----
    # 下側: 支川下端 ～ 下側道路の川側端
    y1_low = y_trib_lower_road + half_w
    y2_low = y_trib_b

    # 上側: 支川上端 ～ 上側道路の川側端
    y1_up = y_trib_t
    y2_up = y_trib_upper_road - half_w

    for i in range(len(x_list) - 1):
        x_left = x_list[i] + half_w
        x_right = x_list[i + 1] - half_w
        if x_right <= x_left:
            continue

        # 支川区間は左側だけ
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
            if poly_low.area > 0.0:
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
            if poly_up.area > 0.0:
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
        trib_gap_buffer=30.0,
    )
    print(f"Roads saved to: {roads_path}")
    print(f"Road edges saved to: {road_edges_path}")

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
        trib_gap_buffer=30.0,
    )
    print(f"City blocks saved to: {blocks_path}")
    print(f"River gaps saved to: {river_gap_path}")


if __name__ == "__main__":
    main()