#!/usr/bin/env python3
from pathlib import Path
from collections import defaultdict
import math

RIVER_ATTR = 3  # inf.dat 上での河川属性

base_dir = Path(".")

def read_inf(path):
    mesh_attr = {}
    with open(path, "r") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            parts = line.split()
            if len(parts) < 2:
                continue
            mid = int(parts[0])
            attr = int(parts[1])
            mesh_attr[mid] = attr
    return mesh_attr

def read_mesh(path):
    mesh_links = {}   # mesh_id -> [l1, l2, l3]
    mesh_cent = {}    # mesh_id -> (xc, yc)
    with open(path, "r") as f:
        nmesh = int(f.readline().strip())
        for _ in range(nmesh):
            line1 = f.readline()
            if not line1:
                break
            parts1 = line1.split()
            mid = int(parts1[0])
            # parts1[1] は nnode=3 のはず
            # parts1[2:] は node ID だがここでは使わない

            line2 = f.readline()
            parts2 = line2.split()
            # 3つの edge link ID
            links = [int(x) for x in parts2[:3]]
            mesh_links[mid] = links

            line3 = f.readline()
            parts3 = line3.split()
            # 例: area, xc, yc
            area = float(parts3[0])
            xc = float(parts3[1])
            yc = float(parts3[2])
            mesh_cent[mid] = (xc, yc)

            line4 = f.readline()  # 重みなど。ここでは読み飛ばす

    return mesh_links, mesh_cent

def build_link_to_meshes(mesh_links):
    link_to_meshes = defaultdict(list)
    for mid, links in mesh_links.items():
        for li in links:
            link_to_meshes[li].append(mid)
    return link_to_meshes

def read_link_dir(path):
    link_dir = {}  # link_id -> (ux, uy)
    with open(path, "r") as f:
        nlink = int(f.readline().strip())
        for _ in range(nlink):
            line1 = f.readline()
            if not line1:
                break
            parts1 = line1.split()
            lid = int(parts1[0])

            _ = f.readline()  # 長さなどの行はスキップ
            line3 = f.readline()
            parts3 = line3.split()
            # 最後の2つを ux, uy とみなす
            ux = float(parts3[-2])
            uy = float(parts3[-1])
            link_dir[lid] = (ux, uy)
    return link_dir

def read_kasho_distance(path):
    station = []  # index=0..msctn-1 で河口からの距離[m]
    with open(path, "r") as f:
        nsec = int(f.readline().strip())
        header = f.readline()
        for _ in range(nsec):
            line = f.readline()
            if not line:
                break
            parts = line.split()
            if len(parts) < 2:
                continue
            dist = float(parts[1])  # 2列目が DISTANCE
            # 仮に km なら m に直す
            # dist_m = dist * 1000.0
            dist_m = dist
            station.append(dist_m)
    return station

def main():
    mesh_attr = read_inf(base_dir / "inf.dat")
    mesh_links, mesh_cent = read_mesh(base_dir / "mesh.dat")
    link_to_meshes = build_link_to_meshes(mesh_links)
    link_dir = read_link_dir(base_dir / "link.dat")
    station = read_kasho_distance(base_dir / "kasho.dat")
    msctn = len(station)

    # 河道メッシュの重心 x の平均 (河道の中心 x)
    river_mesh_ids = [mid for mid, attr in mesh_attr.items() if attr == RIVER_ATTR]
    x_c = sum(mesh_cent[mid][0] for mid in river_mesh_ids) / len(river_mesh_ids)

    # 縦断方向の y 範囲
    ys_river = [mesh_cent[mid][1] for mid in river_mesh_ids]
    y_min, y_max = min(ys_river), max(ys_river)

    # 総延長 L は kasho の最大距離とする
    L = max(station) if station else (y_max - y_min)

    # iごとの左岸/右岸のリンクリスト
    left_links = [[] for _ in range(msctn)]
    right_links = [[] for _ in range(msctn)]

    # すべてのリンクについて「河道メッシュと氾濫原メッシュを繋ぐもの」を探す
    for lid, mlist in link_to_meshes.items():
        if len(mlist) != 2:
            continue  # 内部でない/外周などは一旦無視
        m1, m2 = mlist
        a1 = mesh_attr.get(m1, 0)
        a2 = mesh_attr.get(m2, 0)

        # 片側が河道, 片側が非河道のときだけ接続リンクとみなす
        if (a1 == RIVER_ATTR and a2 != RIVER_ATTR):
            mesh_riv = m1
        elif (a2 == RIVER_ATTR and a1 != RIVER_ATTR):
            mesh_riv = m2
        else:
            continue

        xc, yc = mesh_cent[mesh_riv]

        # y座標を縦断距離にマッピング（上流 y_max → L, 下流 y_min → 0 の例）
        if y_max != y_min:
            s_link = L * (y_max - yc) / (y_max - y_min)
        else:
            s_link = 0.0

        # 最も近いkasho断面を探す
        i_best = min(range(msctn), key=lambda i: abs(station[i] - s_link))

        ux, uy = link_dir[lid]

        # 左岸/右岸の判定：河道中心 x_c と比較
        if xc < x_c:
            left_links[i_best].append((mesh_riv, lid, ux, uy))
        else:
            right_links[i_best].append((mesh_riv, lid, ux, uy))

    # riv_to_2d.dat の書き出し
    out_path = base_dir / "riv_to_2d.dat"
    with open(out_path, "w") as f:
        for i in range(msctn):
            i1 = i + 1  # 1-origin
            f.write(f"{i1:5d}\n")
            f.write(f"Left  {len(left_links[i]):7d}\n")
            f.write(f"Right {len(right_links[i]):7d}\n")
            for me, li, ux, uy in left_links[i]:
                f.write(f"{me:8d}{li:8d}{ux:12.6f}{uy:12.6f}\n")
            for me, li, ux, uy in right_links[i]:
                f.write(f"{me:8d}{li:8d}{ux:12.6f}{uy:12.6f}\n")
            f.write("------------------------\n")

    print("wrote", out_path)


if __name__ == "__main__":
    main()
