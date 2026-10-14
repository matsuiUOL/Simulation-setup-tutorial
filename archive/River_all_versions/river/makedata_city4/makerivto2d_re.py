#!/usr/bin/env python3
from pathlib import Path
from collections import defaultdict
import math

RIVER_ATTR = 3
base_dir = Path(".")

# -----------------------------
# 断面番号の reach 定義
# -----------------------------
MAIN_UP_RANGE   = range(1, 31)    # 1..30
MAIN_DOWN_RANGE = range(31, 62)   # 31..61
TRIB_RANGE      = range(62, 93)   # 62..92

# 合流点付近の断面は接続を作らない
EXCLUDED_SECTIONS = {28, 29, 30, 31, 32, 33, 90, 91, 92}

# 各断面・各岸で残す最大リンク数
MAX_LINKS_PER_SIDE = 1

# 支川中心yを手で与える場合（Noneなら自動）
TRIB_Y_CENTER = None

# 本川中心xを手で与える場合（Noneなら自動）
MAIN_X_CENTER = None


def read_inf(path: Path):
    mesh_attr = {}
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            parts = line.split()
            if len(parts) < 2:
                continue
            mesh_attr[int(parts[0])] = int(parts[1])
    return mesh_attr


def read_mesh(path: Path):
    mesh_links = {}
    mesh_cent = {}
    with path.open("r", encoding="utf-8") as f:
        nmesh = int(f.readline().strip())
        for _ in range(nmesh):
            line1 = f.readline()
            if not line1:
                break
            parts1 = line1.split()
            mid = int(parts1[0])

            line2 = f.readline()
            parts2 = line2.split()
            links = [int(x) for x in parts2[:3]]
            mesh_links[mid] = links

            line3 = f.readline()
            parts3 = line3.split()
            xc = float(parts3[1])
            yc = float(parts3[2])
            mesh_cent[mid] = (xc, yc)

            _ = f.readline()
    return mesh_links, mesh_cent


def build_link_to_meshes(mesh_links):
    link_to_meshes = defaultdict(list)
    for mid, links in mesh_links.items():
        for li in links:
            link_to_meshes[li].append(mid)
    return link_to_meshes


def read_link_dir(path: Path):
    link_dir = {}
    with path.open("r", encoding="utf-8") as f:
        nlink = int(f.readline().strip())
        for _ in range(nlink):
            line1 = f.readline()
            if not line1:
                break
            lid = int(line1.split()[0])
            _ = f.readline()
            line3 = f.readline()
            parts3 = line3.split()
            ux = float(parts3[-2])
            uy = float(parts3[-1])
            link_dir[lid] = (ux, uy)
    return link_dir


def read_kasho_distance(path: Path):
    station = []
    with path.open("r", encoding="utf-8") as f:
        nsec = int(f.readline().strip())
        _ = f.readline()
        for _ in range(nsec):
            line = f.readline()
            if not line:
                break
            parts = line.split()
            if len(parts) < 2:
                continue
            station.append(float(parts[1]))
    return station


def classify_river_meshes(river_mesh_ids, mesh_cent):
    """
    河川メッシュを main / trib にざっくり分類
    仮想都市では
      - 本川: 縦に長い
      - 支川: 横に長い
    ので、まず y が高めの横枝を支川とみなす簡易版
    """
    xs = [mesh_cent[mid][0] for mid in river_mesh_ids]
    ys = [mesh_cent[mid][1] for mid in river_mesh_ids]

    x_mean = sum(xs) / len(xs)
    y_mean = sum(ys) / len(ys)

    # 支川候補: 本川中心xから少し離れた横枝
    # ここは必要なら後で閾値調整
    main_ids = []
    trib_ids = []

    x_span = max(xs) - min(xs) if xs else 0.0
    threshold = 0.15 * x_span

    for mid in river_mesh_ids:
        xc, yc = mesh_cent[mid]
        if abs(xc - x_mean) > threshold:
            trib_ids.append(mid)
        else:
            main_ids.append(mid)

    return main_ids, trib_ids


def nearest_section_by_dist(target_dist, section_ids, station):
    """
    section_ids: 1-based section indices
    station    : 0-based list, station[ind-1]
    """
    return min(section_ids, key=lambda ind: abs(station[ind - 1] - target_dist))


def trim_links(records, max_n):
    """
    同じ断面・同じ岸に候補が多すぎるとき、max_n個だけ残す。
    ここでは単純に link_id 昇順。
    """
    records = sorted(records, key=lambda x: x[1])
    return records[:max_n]


def main():
    mesh_attr = read_inf(base_dir / "inf.dat")
    mesh_links, mesh_cent = read_mesh(base_dir / "mesh.dat")
    link_to_meshes = build_link_to_meshes(mesh_links)
    link_dir = read_link_dir(base_dir / "link.dat")
    station = read_kasho_distance(base_dir / "kasho_ini.dat")

    msctn = len(station)

    river_mesh_ids = [mid for mid, attr in mesh_attr.items() if attr == RIVER_ATTR]
    if not river_mesh_ids:
        raise RuntimeError("No river meshes found (attr==RIVER_ATTR).")

    main_river_ids, trib_river_ids = classify_river_meshes(river_mesh_ids, mesh_cent)

    if not main_river_ids:
        raise RuntimeError("No main-river meshes classified.")
    if not trib_river_ids:
        raise RuntimeError("No tributary meshes classified.")

    x_c_main = MAIN_X_CENTER
    if x_c_main is None:
        x_c_main = sum(mesh_cent[mid][0] for mid in main_river_ids) / len(main_river_ids)

    y_c_trib = TRIB_Y_CENTER
    if y_c_trib is None:
        y_c_trib = sum(mesh_cent[mid][1] for mid in trib_river_ids) / len(trib_river_ids)

    ys_main = [mesh_cent[mid][1] for mid in main_river_ids]
    y_main_min, y_main_max = min(ys_main), max(ys_main)

    xs_trib = [mesh_cent[mid][0] for mid in trib_river_ids]
    x_trib_min, x_trib_max = min(xs_trib), max(xs_trib)

    # 断面ごとの接続候補
    left_links  = [[] for _ in range(msctn)]
    right_links = [[] for _ in range(msctn)]

    for lid, mlist in link_to_meshes.items():
        if len(mlist) != 2:
            continue

        m1, m2 = mlist
        a1 = mesh_attr.get(m1, 0)
        a2 = mesh_attr.get(m2, 0)

        if a1 == RIVER_ATTR and a2 != RIVER_ATTR:
            mesh_riv = m1
            mesh_grd = m2
        elif a2 == RIVER_ATTR and a1 != RIVER_ATTR:
            mesh_riv = m2
            mesh_grd = m1
        else:
            continue

        xc_riv, yc_riv = mesh_cent[mesh_riv]
        xc_grd, yc_grd = mesh_cent[mesh_grd]
        ux, uy = link_dir.get(lid, (0.0, 0.0))
        rec = (mesh_grd, lid, ux, uy)

        # -----------------------------
        # どの reach か判定
        # -----------------------------
        if mesh_riv in trib_river_ids:
            # 支川: x を距離軸に使う
            if x_trib_max != x_trib_min:
                # 左→右流れを想定: 左端が上流, 右端が下流
                s_link = 1.5 * (xc_riv - x_trib_min) / (x_trib_max - x_trib_min) + 1.5
            else:
                s_link = 1.5

            i_best = nearest_section_by_dist(s_link, list(TRIB_RANGE), station)

            # 合流点近傍除外
            if i_best in EXCLUDED_SECTIONS:
                continue

            # 支川は y で左右判定
            if yc_grd > y_c_trib:
                left_links[i_best - 1].append(rec)
            else:
                right_links[i_best - 1].append(rec)

        else:
            # 本川: y を距離軸に使う
            if y_main_max != y_main_min:
                s_main = 3.0 * (y_main_max - yc_riv) / (y_main_max - y_main_min)
            else:
                s_main = 0.0

            # 合流点より上流/下流で振り分け
            if s_main >= 1.5:
                i_best = nearest_section_by_dist(s_main, list(MAIN_UP_RANGE), station)
            else:
                i_best = nearest_section_by_dist(s_main, list(MAIN_DOWN_RANGE), station)

            if i_best in EXCLUDED_SECTIONS:
                continue

            # 本川は x で左右判定
            if xc_grd < x_c_main:
                left_links[i_best - 1].append(rec)
            else:
                right_links[i_best - 1].append(rec)

    # 接続数を絞る
    for i in range(msctn):
        left_links[i] = trim_links(left_links[i], MAX_LINKS_PER_SIDE)
        right_links[i] = trim_links(right_links[i], MAX_LINKS_PER_SIDE)

    out_path = base_dir / "riv_to_2d_v2.dat"
    with out_path.open("w", encoding="utf-8", newline="\n") as f:
        for i in range(msctn):
            i1 = i + 1
            f.write(f"{i1:5d}\n")

            nl = len(left_links[i])
            nr = len(right_links[i])

            f.write(f"{'Left':<8}{nl:3d}\n")
            for me, li, ux, uy in left_links[i]:
                f.write(f"{me:8d}{li:8d}{ux:12.6f}{uy:12.6f}\n")

            f.write(f"{'Right':<8}{nr:3d}\n")
            for me, li, ux, uy in right_links[i]:
                f.write(f"{me:8d}{li:8d}{ux:12.6f}{uy:12.6f}\n")

            f.write("------------------------\n")

    print("wrote", out_path, f"(msctn={msctn})")


if __name__ == "__main__":
    main()