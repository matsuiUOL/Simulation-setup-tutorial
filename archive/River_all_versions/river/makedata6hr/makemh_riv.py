#!/usr/bin/env python3
from pathlib import Path
from collections import defaultdict
import math

RIVER_ATTR = 3  # inf.dat 上での河川属性
base_dir = Path(".")

# ---- readers ----
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

def read_mesh_centroids(path):
    """mesh.dat から mesh_id -> (xc,yc) だけ読む"""
    mesh_cent = {}
    with open(path, "r") as f:
        nmesh = int(f.readline().strip())
        for _ in range(nmesh):
            line1 = f.readline()
            if not line1:
                break
            parts1 = line1.split()
            mid = int(parts1[0])

            _ = f.readline()  # link 3本行
            line3 = f.readline()
            parts3 = line3.split()
            xc = float(parts3[1])
            yc = float(parts3[2])
            mesh_cent[mid] = (xc, yc)

            _ = f.readline()  # 重み行
    return mesh_cent

def read_kasho_distance(path):
    station = []
    with open(path, "r") as f:
        nsec = int(f.readline().strip())
        _ = f.readline()  # header
        for _ in range(nsec):
            line = f.readline()
            if not line:
                break
            parts = line.split()
            if len(parts) < 2:
                continue
            dist = float(parts[1])
            station.append(dist)
    return station

def read_manhole_bshosei(path):
    """
    manhole_bshosei.dat:
    1行目: mh数
    2行目: header
    以降: id ... x_mh y_mh ...
    """
    manholes = []
    with open(path, "r") as f:
        n = int(f.readline().strip())
        _ = f.readline()  # header
        for _ in range(n):
            line = f.readline()
            if not line:
                break
            parts = line.split()
            if len(parts) < 6:
                continue
            mh_id = int(parts[0])
            x_mh = float(parts[3])
            y_mh = float(parts[4])
            manholes.append((mh_id, x_mh, y_mh))
    return manholes

# ---- main logic ----
def main():
    mesh_attr = read_inf(base_dir / "inf0125_v2.dat")
    mesh_cent = read_mesh_centroids(base_dir / "mesh0125_v2.dat")
    station = read_kasho_distance(base_dir / "kasho_v2.dat")
    msctn = len(station)

    # 河道メッシュ一覧
    river_mesh_ids = [mid for mid, attr in mesh_attr.items() if attr == RIVER_ATTR]
    if not river_mesh_ids:
        raise RuntimeError("No river meshes found (attr=3).")

    # 河道メッシュのy範囲（あなたの riv_to_2d と同じ縦断マッピング）
    ys_river = [mesh_cent[mid][1] for mid in river_mesh_ids]
    y_min, y_max = min(ys_river), max(ys_river)

    L = max(station) if station else (y_max - y_min)

    # 1) 河道メッシュ mid ごとに riv_no (= i_best+1) を付与
    mesh_to_rivno = {}
    for mid in river_mesh_ids:
        xc, yc = mesh_cent[mid]
        if y_max != y_min:
            s = L * (y_max - yc) / (y_max - y_min)
        else:
            s = 0.0
        i_best = min(range(msctn), key=lambda i: abs(station[i] - s))
        mesh_to_rivno[mid] = i_best + 1  # 1-origin

    # 2) マンホールを最近傍の河道メッシュに割り当て
    manholes = read_manhole_bshosei(base_dir / "manhole_bshosei3.dat")

    # 近傍探索（簡易：全探索。数千規模ならOK、もっと多いならKD-tree推奨）
    out = []
    for mh_id, x_mh, y_mh in manholes:
        best_mid = None
        best_d2 = None
        for mid in river_mesh_ids:
            xc, yc = mesh_cent[mid]
            dx = x_mh - xc
            dy = y_mh - yc
            d2 = dx*dx + dy*dy
            if best_d2 is None or d2 < best_d2:
                best_d2 = d2
                best_mid = mid

        riv_no = mesh_to_rivno[best_mid]
        dist = math.sqrt(best_d2)

        out.append((mh_id, riv_no, best_mid, dist))

    # 3) 距離でフィルタしたい場合（任意）
    # 例：河川から 50m 以上離れているマンホールは除外など
    # threshold = 50.0
    # out = [r for r in out if r[3] <= threshold]

    # 4) CSV 出力（mh_id,riv_no）
    out_path = base_dir / "mh_riv_v2.csv"
    with open(out_path, "w") as f:
        f.write("mh_id,riv_no\n")
        for mh_id, riv_no, _, _ in out:
            f.write(f"{mh_id},{riv_no}\n")

    # デバッグ用（どの河道メッシュに割り当てたか・距離も欲しければ）
    dbg_path = base_dir / "mh_riv_debug_v2.csv"
    with open(dbg_path, "w") as f:
        f.write("mh_id,riv_no,nearest_river_mesh_id,distance\n")
        for mh_id, riv_no, mid, dist in out:
            f.write(f"{mh_id},{riv_no},{mid},{dist:.3f}\n")

    print("wrote", out_path)
    print("wrote", dbg_path)

if __name__ == "__main__":
    main()
