#!/usr/bin/env python3
from pathlib import Path
from collections import defaultdict

RIVER_ATTR = 3
base_dir = Path(".")

# -----------------------------
# readers
# -----------------------------
def read_inf(path):
    mesh_attr = {}
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            parts = line.split()
            if len(parts) < 2:
                continue
            mid = int(parts[0])
            attr = int(parts[1])
            mesh_attr[mid] = attr
    return mesh_attr


def read_mesh_centroids(path):
    """mesh.dat から mesh_id -> (xc, yc) を読む"""
    mesh_cent = {}
    with open(path, "r", encoding="utf-8") as f:
        nmesh = int(f.readline().strip())
        for _ in range(nmesh):
            line1 = f.readline()
            if not line1:
                break
            parts1 = line1.split()
            mid = int(parts1[0])

            _ = f.readline()  # link行
            line3 = f.readline()
            parts3 = line3.split()
            xc = float(parts3[1])
            yc = float(parts3[2])
            mesh_cent[mid] = (xc, yc)

            _ = f.readline()  # weight行
    return mesh_cent


def read_kasho_distance(path):
    """
    kasho_v2.dat:
      1行目: 断面数
      2行目: header
      以降: sec_id dist ...
    """
    station = []
    with open(path, "r", encoding="utf-8") as f:
        nsec = int(f.readline().strip())
        _ = f.readline()
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


def read_connect_riv(path):
    """
    既存の connect4 用データ:
      1行目: 接続数
      以降: sw_i mh_id riv_no
    """
    rows = []
    with open(path, "r", encoding="utf-8") as f:
        first = f.readline()
        if not first:
            return rows
        n = int(first.strip())
        for _ in range(n):
            line = f.readline()
            if not line:
                break
            parts = line.split()
            if len(parts) < 3:
                continue
            sw_i = int(parts[0])
            mh_id = int(parts[1])
            riv_no = int(parts[2])
            rows.append((sw_i, mh_id, riv_no))
    return rows


# -----------------------------
# main
# -----------------------------
def main():
    mesh_attr = read_inf(base_dir / "inf.dat")
    mesh_cent = read_mesh_centroids(base_dir / "mesh.dat")
    station = read_kasho_distance(base_dir / "kasho_v2.dat")
    connect_rows = read_connect_riv(base_dir / "sw_riv.dat")  # 既存ファイル名に合わせて変更可

    msctn = len(station)
    if msctn == 0:
        raise RuntimeError("No river sections found in kasho_v2.dat")

    river_mesh_ids = [mid for mid, attr in mesh_attr.items() if attr == RIVER_ATTR]
    if not river_mesh_ids:
        raise RuntimeError("No river meshes found (attr=3).")

    ys_river = [mesh_cent[mid][1] for mid in river_mesh_ids]
    y_min, y_max = min(ys_river), max(ys_river)

    L = max(station) if station else (y_max - y_min)

    # --------------------------------------
    # 1) 各河道メッシュ mid に対応する riv_no を決める
    # --------------------------------------
    mesh_to_rivno = {}
    for mid in river_mesh_ids:
        xc, yc = mesh_cent[mid]
        if y_max != y_min:
            s = L * (y_max - yc) / (y_max - y_min)
        else:
            s = 0.0

        i_best = min(range(msctn), key=lambda i: abs(station[i] - s))
        mesh_to_rivno[mid] = i_best + 1  # 1-origin

    # --------------------------------------
    # 2) riv_no ごとに対応する河道メッシュ候補を集める
    # --------------------------------------
    rivno_to_meshes = defaultdict(list)
    for mid, riv_no in mesh_to_rivno.items():
        rivno_to_meshes[riv_no].append(mid)

    # --------------------------------------
    # 3) 各 riv_no に対して代表 me_out を1つ決める
    #    ここでは y の中央値に最も近い河道メッシュを採用
    # --------------------------------------
    rivno_to_meout = {}
    for riv_no, mids in rivno_to_meshes.items():
        mids_sorted = sorted(mids, key=lambda m: mesh_cent[m][1])
        me_out = mids_sorted[len(mids_sorted) // 2]
        rivno_to_meout[riv_no] = me_out

    # --------------------------------------
    # 4) 既存 connect4.dat を me_out 版に変換
    # --------------------------------------
    out_rows = []
    missing_rivno = []

    for sw_i, mh_id, riv_no in connect_rows:
        me_out = rivno_to_meout.get(riv_no)
        if me_out is None:
            missing_rivno.append((sw_i, mh_id, riv_no))
            continue
        out_rows.append((sw_i, mh_id, me_out))

    # --------------------------------------
    # 5) 出力
    # --------------------------------------
    out_path = base_dir / "sw_riv_gr.dat"
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(f"{len(out_rows)}\n")
        for sw_i, mh_id, me_out in out_rows:
            f.write(f"{sw_i} {mh_id} {me_out}\n")

    dbg_path = base_dir / "connect4_mesh_debug.csv"
    with open(dbg_path, "w", encoding="utf-8") as f:
        f.write("sw_i,mh_id,riv_no,me_out\n")
        for sw_i, mh_id, riv_no in connect_rows:
            me_out = rivno_to_meout.get(riv_no, "")
            f.write(f"{sw_i},{mh_id},{riv_no},{me_out}\n")

    miss_path = base_dir / "connect4_mesh_missing_rivno.csv"
    with open(miss_path, "w", encoding="utf-8") as f:
        f.write("sw_i,mh_id,riv_no\n")
        for sw_i, mh_id, riv_no in missing_rivno:
            f.write(f"{sw_i},{mh_id},{riv_no}\n")

    print("wrote", out_path)
    print("wrote", dbg_path)
    print("wrote", miss_path)
    print("n_out =", len(out_rows))
    print("n_missing_rivno =", len(missing_rivno))


if __name__ == "__main__":
    main()