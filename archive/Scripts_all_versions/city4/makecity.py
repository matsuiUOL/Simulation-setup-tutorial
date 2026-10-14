import numpy as np
import rasterio
from rasterio.transform import from_origin
from rasterio.crs import CRS
import geopandas as gpd
from shapely.geometry import (
    LineString, Point, Polygon,
    MultiLineString, MultiPolygon, GeometryCollection
)
from shapely.ops import unary_union
from pathlib import Path


# =========================================================
# 0. ディレクトリ作成
# =========================================================
def create_directories(base_dir: Path):
    dem_dir = base_dir / "01_DEM" / "city_confluence"
    layers_dir = base_dir / "02_GIS_layers" / "city_confluence"
    dem_dir.mkdir(parents=True, exist_ok=True)
    layers_dir.mkdir(parents=True, exist_ok=True)
    return dem_dir, layers_dir


# =========================================================
# 1. DEM作成
# =========================================================
def make_dem(dem_path: Path, epsg: int = 6677):
    dx = 5.0
    dy = 5.0
    nx = 600
    ny = 600

    origin_x = 152000.0
    origin_y = 505000.0

    transform = from_origin(origin_x, origin_y, dx, dy)
    crs = CRS.from_epsg(epsg)

    dem = np.zeros((ny, nx), dtype=np.float32)

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


# =========================================================
# 2. 河川作成
# =========================================================
def make_river_confluence(
    river_center_path: Path,
    river_polygon_path: Path,
    pump_path: Path,
    city_bbox,
    dem_bbox,
    crs,
    main_width: float = 30.0,
    trib_width: float = 15.0,
    tributary_side: str = "west",
):
    xmin_u, xmax_u, ymin_u, ymax_u = city_bbox
    xmin_dem, xmax_dem, ymin_dem, ymax_dem = dem_bbox

    main_x = 0.5 * (xmin_u + xmax_u)
    junction_y = ymin_u + 0.60 * (ymax_u - ymin_u)

    main_line = LineString([(main_x, ymin_dem), (main_x, ymax_dem)])
    main_half = main_width / 2.0
    main_poly = Polygon([
        (main_x - main_half, ymin_dem),
        (main_x + main_half, ymin_dem),
        (main_x + main_half, ymax_dem),
        (main_x - main_half, ymax_dem),
    ])

    trib_half = trib_width / 2.0
    if tributary_side.lower() == "west":
        trib_line = LineString([(xmin_dem, junction_y), (main_x, junction_y)])
        trib_poly = Polygon([
            (xmin_dem, junction_y - trib_half),
            (main_x, junction_y - trib_half),
            (main_x, junction_y + trib_half),
            (xmin_dem, junction_y + trib_half),
        ])
    else:
        trib_line = LineString([(main_x, junction_y), (xmax_dem, junction_y)])
        trib_poly = Polygon([
            (main_x, junction_y - trib_half),
            (xmax_dem, junction_y - trib_half),
            (xmax_dem, junction_y + trib_half),
            (main_x, junction_y + trib_half),
        ])

    river_union = unary_union([main_poly, trib_poly])

    gpd.GeoDataFrame(
        {"river_id": [1, 2], "name": ["main", "tributary"], "width_m": [main_width, trib_width]},
        geometry=[main_line, trib_line],
        crs=crs,
    ).to_file(river_center_path)

    gpd.GeoDataFrame(
        {"river_id": [1], "landuse": ["river"]},
        geometry=[river_union],
        crs=crs,
    ).to_file(river_polygon_path)

    gpd.GeoDataFrame(
        {"pump_id": [1], "type": ["pump_station"]},
        geometry=[Point(main_x, ymax_dem)],
        crs=crs,
    ).to_file(pump_path)

    return {
        "river_geom": river_union,
        "main_x": main_x,
        "junction_y": junction_y,
        "main_width": main_width,
        "trib_width": trib_width,
        "tributary_side": tributary_side.lower(),
    }


# =========================================================
# 3. geometry utilities
# =========================================================
def explode_lines(geom):
    if geom.is_empty:
        return []
    if isinstance(geom, LineString):
        return [geom]
    if isinstance(geom, MultiLineString):
        return list(geom.geoms)
    if isinstance(geom, GeometryCollection):
        out = []
        for g in geom.geoms:
            out.extend(explode_lines(g))
        return out
    return []


def explode_polygons(geom):
    if geom.is_empty:
        return []
    if isinstance(geom, Polygon):
        return [geom]
    if isinstance(geom, MultiPolygon):
        return list(geom.geoms)
    if isinstance(geom, GeometryCollection):
        out = []
        for g in geom.geoms:
            out.extend(explode_polygons(g))
        return out
    return []


# =========================================================
# 4. その他ポリゴン
#    本川沿い左右帯 + 支川沿い上下帯
# =========================================================
def make_other_polygons(
    other_path: Path,
    city_bbox,
    river_info,
    river_geom,
    crs,
    main_side_band: float = 35.0,   # ← 120 → 35 に縮小
    trib_side_band: float = 80.0,
):
    xmin_u, xmax_u, ymin_u, ymax_u = city_bbox
    main_x = river_info["main_x"]
    junction_y = river_info["junction_y"]
    main_w = river_info["main_width"]
    trib_w = river_info["trib_width"]
    trib_side = river_info["tributary_side"]

    polys = []
    attrs = []

    # 本川沿い左右帯（細くする）
    x_main_l = main_x - main_w / 2.0
    x_main_r = main_x + main_w / 2.0

    left_band = Polygon([
        (x_main_l - main_side_band, ymin_u),
        (x_main_l, ymin_u),
        (x_main_l, ymax_u),
        (x_main_l - main_side_band, ymax_u),
    ])
    right_band = Polygon([
        (x_main_r, ymin_u),
        (x_main_r + main_side_band, ymin_u),
        (x_main_r + main_side_band, ymax_u),
        (x_main_r, ymax_u),
    ])
    polys.extend([left_band, right_band])
    attrs.extend(["main_left", "main_right"])

    # 支川沿い上下帯
    y_trib_b = junction_y - trib_w / 2.0
    y_trib_t = junction_y + trib_w / 2.0

    if trib_side == "west":
        x_trib0 = xmin_u
        x_trib1 = main_x
    else:
        x_trib0 = main_x
        x_trib1 = xmax_u

    trib_upper = Polygon([
        (x_trib0, y_trib_t),
        (x_trib1, y_trib_t),
        (x_trib1, y_trib_t + trib_side_band),
        (x_trib0, y_trib_t + trib_side_band),
    ])
    trib_lower = Polygon([
        (x_trib0, y_trib_b - trib_side_band),
        (x_trib1, y_trib_b - trib_side_band),
        (x_trib1, y_trib_b),
        (x_trib0, y_trib_b),
    ])
    polys.extend([trib_upper, trib_lower])
    attrs.extend(["trib_upper", "trib_lower"])

    city_poly = Polygon([
        (xmin_u, ymin_u), (xmax_u, ymin_u), (xmax_u, ymax_u), (xmin_u, ymax_u)
    ])

    clipped = []
    out_attrs = []
    for poly, name in zip(polys, attrs):
        g = poly.intersection(city_poly).difference(river_geom).buffer(0)
        for pg in explode_polygons(g):
            if pg.area > 50.0:
                clipped.append(pg)
                out_attrs.append(name)

    other_union = unary_union(clipped).buffer(0)

    gdf = gpd.GeoDataFrame(
        {"other_id": list(range(len(clipped))), "otype": out_attrs},
        geometry=clipped,
        crs=crs,
    )
    gdf.to_file(other_path)

    return gdf, other_union


# =========================================================
# 5. 道路作成
#    - 河川にもその他ポリゴンにも侵入しない
#    - ただしその他ポリゴンと建物の境界に道路を追加
#    - 道路縁が河道側にはみ出さないよう buffer後に再clip
# =========================================================
def make_roads(
    roads_path: Path,
    road_edges_path: Path,
    city_bbox,
    river_geom,
    other_union,
    river_info,
    crs,
    road_spacing: float = 200.0,
    road_width: float = 40.0,
):
    xmin_u, xmax_u, ymin_u, ymax_u = city_bbox
    half_w = road_width / 2.0

    city_poly = Polygon([
        (xmin_u, ymin_u), (xmax_u, ymin_u), (xmax_u, ymax_u), (xmin_u, ymax_u)
    ])

    forbidden_center = unary_union([river_geom, other_union]).buffer(1e-6)
    allowed_poly = city_poly.difference(unary_union([river_geom, other_union])).buffer(0)

    roads_center = []
    rtypes = []

    x_vals = np.arange(xmin_u, xmax_u + 1e-6, road_spacing)
    y_vals = np.arange(ymin_u, ymax_u + 1e-6, road_spacing)

    # 通常の縦道路
    for x0 in x_vals:
        line = LineString([(x0, ymin_u), (x0, ymax_u)])
        cut = line.difference(forbidden_center)
        for seg in explode_lines(cut):
            if seg.length >= 30.0:
                roads_center.append(seg)
                rtypes.append("grid_v")

    # 通常の横道路
    for y0 in y_vals:
        line = LineString([(xmin_u, y0), (xmax_u, y0)])
        cut = line.difference(forbidden_center)
        for seg in explode_lines(cut):
            if seg.length >= 30.0:
                roads_center.append(seg)
                rtypes.append("grid_h")

    # 本川側：other polygon と建物の境界道路
    main_x = river_info["main_x"]
    main_w = river_info["main_width"]
    main_side_band = 35.0

    x_left = main_x - main_w / 2.0 - main_side_band
    x_right = main_x + main_w / 2.0 + main_side_band

    for x0 in [x_left, x_right]:
        if xmin_u < x0 < xmax_u:
            line = LineString([(x0, ymin_u), (x0, ymax_u)])
            cut = line.difference(river_geom.buffer(1e-6))
            for seg in explode_lines(cut):
                if seg.length >= 30.0:
                    roads_center.append(seg)
                    rtypes.append("other_boundary_main")

    # 支川側：other polygon と建物の境界道路
    junction_y = river_info["junction_y"]
    trib_w = river_info["trib_width"]
    trib_side_band = 80.0

    y_up = junction_y + trib_w / 2.0 + trib_side_band
    y_low = junction_y - trib_w / 2.0 - trib_side_band

    for y0 in [y_up, y_low]:
        if ymin_u < y0 < ymax_u:
            line = LineString([(xmin_u, y0), (xmax_u, y0)])
            cut = line.difference(river_geom.buffer(1e-6))
            for seg in explode_lines(cut):
                if seg.length >= 30.0:
                    roads_center.append(seg)
                    rtypes.append("other_boundary_trib")

    # 道路面ポリゴン
    road_poly_list = []
    center_out = []
    rtype_out = []

    for geom, rtype in zip(roads_center, rtypes):
        poly = geom.buffer(half_w, cap_style=3, join_style=2)
        poly = poly.intersection(allowed_poly).buffer(0)

        polys = explode_polygons(poly)
        polys = [pg.buffer(0) for pg in polys if (not pg.is_empty and pg.area > 50.0)]

        if len(polys) == 0:
            continue

        road_poly_list.extend(polys)
        center_out.append(geom)
        rtype_out.append(rtype)

    roads_center_gdf = gpd.GeoDataFrame(
        {"road_id": list(range(len(center_out))), "rtype": rtype_out},
        geometry=center_out,
        crs=crs,
    )
    roads_center_gdf.to_file(roads_path)

    roads_edges_gdf = gpd.GeoDataFrame(
        {"road_id": list(range(len(road_poly_list)))},
        geometry=road_poly_list,
        crs=crs,
    )
    roads_edges_gdf.to_file(road_edges_path)

    return roads_center_gdf, roads_edges_gdf


# =========================================================
# 6. 建物群
#    右側欠損を減らすため、buildableを一度 union/clean してから分解
# =========================================================
def make_buildings(
    buildings_path: Path,
    city_bbox,
    river_geom,
    other_union,
    road_edges_gdf,
    crs,
    road_spacing: float = 200.0,
    road_width: float = 40.0,
):
    xmin_u, xmax_u, ymin_u, ymax_u = city_bbox
    half_w = road_width / 2.0

    city_poly = Polygon([
        (xmin_u, ymin_u), (xmax_u, ymin_u), (xmax_u, ymax_u), (xmin_u, ymax_u)
    ])

    road_union = unary_union(list(road_edges_gdf.geometry)).buffer(0) if len(road_edges_gdf) > 0 else GeometryCollection()
    occupied = unary_union([river_geom, other_union, road_union]).buffer(0)

    x_vals = np.arange(xmin_u, xmax_u + 1e-6, road_spacing)
    y_vals = np.arange(ymin_u, ymax_u + 1e-6, road_spacing)

    out = []
    ids = []
    areas = []
    bid = 0

    for i in range(len(x_vals) - 1):
        for j in range(len(y_vals) - 1):
            x1 = x_vals[i] + half_w
            x2 = x_vals[i + 1] - half_w
            y1 = y_vals[j] + half_w
            y2 = y_vals[j + 1] - half_w

            if x2 <= x1 or y2 <= y1:
                continue

            cell = Polygon([
                (x1, y1), (x2, y1), (x2, y2), (x1, y2)
            ])

            cell = cell.intersection(city_poly).difference(occupied).buffer(0)

            for pg in explode_polygons(cell):
                if pg.area < 300.0:
                    continue
                out.append(pg)
                ids.append(bid)
                areas.append(pg.area)
                bid += 1

    gdf = gpd.GeoDataFrame(
        {"bld_id": ids, "area_m2": areas},
        geometry=out,
        crs=crs,
    )
    gdf.to_file(buildings_path)

    return gdf


# =========================================================
# 7. sewer node / link
#    道路交点には必ずnodeを置く
# =========================================================
def make_sewer_nodes_and_links(
    nodes_path: Path,
    links_path: Path,
    roads_center_gdf,
    crs,
    tol: float = 1e-4,
):
    lines = [g for g in roads_center_gdf.geometry if isinstance(g, LineString)]

    pts = []

    # 端点
    for line in lines:
        coords = list(line.coords)
        pts.append(Point(coords[0]))
        pts.append(Point(coords[-1]))

    # 全交点
    for i in range(len(lines)):
        for j in range(i + 1, len(lines)):
            inter = lines[i].intersection(lines[j])
            if inter.is_empty:
                continue
            if inter.geom_type == "Point":
                pts.append(inter)
            elif inter.geom_type == "MultiPoint":
                pts.extend(list(inter.geoms))

    # 重複除去
    def key(p, nd=3):
        return (round(p.x, nd), round(p.y, nd))

    uniq = {}
    for p in pts:
        uniq[key(p)] = p

    node_points = list(uniq.values())
    node_ids = list(range(len(node_points)))

    nodes_gdf = gpd.GeoDataFrame(
        {"node_id": node_ids},
        geometry=node_points,
        crs=crs,
    )
    nodes_gdf.to_file(nodes_path)

    point_lookup = {key(p): i for i, p in enumerate(node_points)}

    link_geoms = []
    start_ids = []
    end_ids = []

    for line in lines:
        on_line = []
        for p in node_points:
            if line.distance(p) <= tol:
                # 念のためline上に投影し直す
                s = line.project(p)
                pp = line.interpolate(s)
                on_line.append(pp)

        # 同一路線上の重複除去
        tmp = {}
        for p in on_line:
            tmp[key(p)] = p
        on_line = list(tmp.values())

        if len(on_line) < 2:
            continue

        on_line = sorted(on_line, key=lambda p: line.project(p))

        for a, b in zip(on_line[:-1], on_line[1:]):
            if a.distance(b) < tol:
                continue

            ka = key(a)
            kb = key(b)

            # ノード辞書になければ追加
            if ka not in point_lookup:
                point_lookup[ka] = len(node_points)
                node_points.append(a)
            if kb not in point_lookup:
                point_lookup[kb] = len(node_points)
                node_points.append(b)

            seg = LineString([a, b])
            if seg.length < tol:
                continue

            link_geoms.append(seg)
            start_ids.append(point_lookup[ka])
            end_ids.append(point_lookup[kb])

    # nodes を再出力（投影点追加の可能性があるため）
    nodes_gdf = gpd.GeoDataFrame(
        {"node_id": list(range(len(node_points)))},
        geometry=node_points,
        crs=crs,
    )
    nodes_gdf.to_file(nodes_path)

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

    return nodes_gdf, links_gdf


# =========================================================
# 8. メイン
# =========================================================
def main():
    base_dir = Path(__file__).resolve().parent
    dem_dir, layers_dir = create_directories(base_dir)

    dem_path = dem_dir / "artificial_dem_confluence_epsg6677.tif"
    river_center_path = layers_dir / "river_center_confluence.shp"
    river_polygon_path = layers_dir / "river_polygon_confluence.shp"
    pump_path = layers_dir / "pump_station_confluence.shp"

    other_path = layers_dir / "other_polygon_confluence.shp"

    roads_path = layers_dir / "roads_confluence.shp"
    road_edges_path = layers_dir / "roads_edges_confluence.shp"

    buildings_path = layers_dir / "buildings_confluence.shp"
    sewer_nodes_path = layers_dir / "sewer_nodes_confluence.shp"
    sewer_links_path = layers_dir / "sewer_links_confluence.shp"

    xmin, xmax, ymin, ymax, dx, dy, crs = make_dem(dem_path, epsg=6677)
    dem_bbox = (xmin, xmax, ymin, ymax)

    margin = 500.0
    xmin_u = xmin + margin
    xmax_u = xmax - margin
    ymin_u = ymin + margin
    ymax_u = ymax - margin
    city_bbox = (xmin_u, xmax_u, ymin_u, ymax_u)

    river_info = make_river_confluence(
        river_center_path=river_center_path,
        river_polygon_path=river_polygon_path,
        pump_path=pump_path,
        city_bbox=city_bbox,
        dem_bbox=dem_bbox,
        crs=crs,
        main_width=30.0,
        trib_width=15.0,
        tributary_side="west",
    )
    river_geom = river_info["river_geom"]

    other_gdf, other_union = make_other_polygons(
        other_path=other_path,
        city_bbox=city_bbox,
        river_info=river_info,
        river_geom=river_geom,
        crs=crs,
        main_side_band=35.0,
        trib_side_band=80.0,
    )

    roads_center_gdf, roads_edges_gdf = make_roads(
        roads_path=roads_path,
        road_edges_path=road_edges_path,
        city_bbox=city_bbox,
        river_geom=river_geom,
        other_union=other_union,
        river_info=river_info,
        crs=crs,
        road_spacing=200.0,
        road_width=40.0,
        river_clearance=0.0,
    )

    buildings_gdf = make_buildings(
        buildings_path=buildings_path,
        city_bbox=city_bbox,
        river_geom=river_geom,
        other_union=other_union,
        road_edges_gdf=roads_edges_gdf,
        crs=crs,
    )

    nodes_gdf, links_gdf = make_sewer_nodes_and_links(
        nodes_path=sewer_nodes_path,
        links_path=sewer_links_path,
        roads_center_gdf=roads_center_gdf,
        crs=crs,
    )

    print("=== Finished ===")
    print(f"DEM: {dem_path}")
    print(f"River center: {river_center_path}")
    print(f"River polygon: {river_polygon_path}")
    print(f"Other polygon: {other_path}")
    print(f"Roads: {roads_path}")
    print(f"Road edges: {road_edges_path}")
    print(f"Buildings: {buildings_path}")
    print(f"Sewer nodes: {sewer_nodes_path}")
    print(f"Sewer links: {sewer_links_path}")
    print(f"n_other={len(other_gdf)}, n_roads={len(roads_center_gdf)}, n_buildings={len(buildings_gdf)}, n_nodes={len(nodes_gdf)}, n_links={len(links_gdf)}")


if __name__ == "__main__":
    main()