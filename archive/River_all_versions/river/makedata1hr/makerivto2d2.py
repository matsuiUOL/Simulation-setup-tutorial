#!/usr/bin/env python3
from pathlib import Path
from collections import defaultdict

RIVER_ATTR = 3  # inf.dat 上での河川属性
base_dir = Path(".")

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
    mesh_links = {}   # mesh_id -> [l1, l2, l3]
    mesh_cent  = {}   # mesh_id -> (xc, yc)
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

            _ = f.readline()  # skip
    return mesh_links, mesh_cent

def build_link_to_meshes(mesh_links):
    link_to_meshes = defaultdict(list)
    for mid, links in mesh_links.items():
        for li in links:
            link_to_meshes[li].append(mid)
    return link_to_meshes

def read_link_dir(path: Path):
    link_dir = {}  # link_id -> (ux, uy)
    with path.open("r", encoding="utf-8") as f:
        nlink = int(f.readline().strip())
        for _ in range(nlink):
            line1 = f.readline()
            if not line1:
                break
            lid = int(line1.split()[0])
            _ = f.readline()          # skip length line
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
        _ = f.readline()  # header
        for _ in range(nsec):
            line = f.readline()
            if not line:
                break
            parts = line.split()
            if len(parts) < 2:
                continue
            # あなたの makekasho.py に合わせるなら DIST は parts[1] ではない可能性あり
            # ただし現行コード踏襲：2列目を距離として扱う
            station.append(float(parts[1]))
    return station

def main():
    mesh_attr = read_inf(base_dir / "inf.dat")
    mesh_links, mesh_cent = read_mesh(base_dir / "mesh.dat")
    link_to_meshes = build_link_to_meshes(mesh_links)
    link_dir = read_link_dir(base_dir / "link.dat")
    station = read_kasho_distance(base_dir / "kasho.dat")
    msctn = len(station)

    # 河道中心 x
    river_mesh_ids = [mid for mid, attr in mesh_attr.items() if attr == RIVER_ATTR]
    if not river_mesh_ids:
        raise RuntimeError("No river meshes found (attr==RIVER_ATTR). Check inf.dat / RIVER_ATTR.")

    x_c = sum(mesh_cent[mid][0] for mid in river_mesh_ids) / len(river_mesh_ids)

    ys_river = [mesh_cent[mid][1] for mid in river_mesh_ids]
    y_min, y_max = min(ys_river), max(ys_river)

    L = max(station) if station else (y_max - y_min)

    left_links  = [[] for _ in range(msctn)]
    right_links = [[] for _ in range(msctn)]

    for lid, mlist in link_to_meshes.items():
        if len(mlist) != 2:
            continue
        m1, m2 = mlist
        a1 = mesh_attr.get(m1, 0)
        a2 = mesh_attr.get(m2, 0)

        if (a1 == RIVER_ATTR and a2 != RIVER_ATTR):
            mesh_riv = m1
        elif (a2 == RIVER_ATTR and a1 != RIVER_ATTR):
            mesh_riv = m2
        else:
            continue

        xc, yc = mesh_cent[mesh_riv]

        if y_max != y_min:
            s_link = L * (yc - y_min) / (y_max - y_min)
        else:
            s_link = 0.0

        i_best = min(range(msctn), key=lambda i: abs(station[i] - s_link))

        ux, uy = link_dir[lid]

        if xc < x_c:
            left_links[i_best].append((mesh_riv, lid, ux, uy))
        else:
            right_links[i_best].append((mesh_riv, lid, ux, uy))

    out_path = base_dir / "riv_to_2d2.dat"
    with out_path.open("w", encoding="utf-8", newline="\n") as f:
        for i in range(msctn):
            i1 = i + 1
            f.write(f"{i1:5d}\n")

            # 1701 format(8x, i3) に合わせる：
            # 先頭8文字を捨てて i3 を読むので、8文字枠に "Left"/"Right" を詰めて、その後に3桁整数
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

