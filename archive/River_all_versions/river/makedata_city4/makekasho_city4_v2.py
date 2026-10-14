from pathlib import Path

# =========================================================
# 入出力ファイル
# =========================================================
FILE_KASHO_IN = "kasho_v2_ini_confluence.dat"
FILE_RIV2D    = "riv_to_2d_v2.dat"
FILE_LINK     = "link.dat"
FILE_BASEO    = "bs_op_corrected.dat"

FILE_KASHO_OUT = "kasho_v2.dat"

# =========================================================
# riv_to_2d の1列目の意味
#   "ground" : 1列目が地上メッシュID（あなたの新しい makerivto2d.py 想定）
#   "river"  : 1列目が河道メッシュID（旧 makekasho_city0.py 想定）
# =========================================================
RIV2D_FIRST_COL = "ground"   # ←必要に応じて "river" に変更

# =========================================================
# 代表値の取り方
# =========================================================
BANK_MODE = "mean"           # "mean" / "max" / "min"

# 左右を同じ高さに揃えるか
FORCE_LR_EQUAL = False
FORCE_MODE = "max"           # FORCE_LR_EQUAL=True のとき "max" / "mean"

# 天端が河床より低くならないための微小量
EPS_BED = 1.0e-3


def read_baseo(path: Path):
    """
    bs_op_corrected.dat:
      mesh_id  baseo
    """
    baseo = {}
    with open(path, "r") as f:
        for line in f:
            s = line.strip().split()
            if len(s) < 2:
                continue
            baseo[int(s[0])] = float(s[1])
    return baseo


def read_link_meshpair_3lines(path: Path):
    """
    link.dat:
      1行ヘッダ
      各リンク3行
        1行目: link_id mesh1 mesh2 node1 node2
        2行目: ...
        3行目: ...
    return:
      pair[link_id] = (mesh1, mesh2)
    """
    pair = {}
    with open(path, "r") as f:
        _ = f.readline()  # header

        while True:
            line1 = f.readline()
            if not line1:
                break
            if not line1.strip():
                continue

            s = line1.strip().split()
            if len(s) < 3:
                break

            link_id = int(s[0])
            mesh1   = int(s[1])
            mesh2   = int(s[2])
            pair[link_id] = (mesh1, mesh2)

            _ = f.readline()
            _ = f.readline()

    return pair


def read_riv_to_2d(path: Path):
    """
    riv_to_2d.dat:
      ind
      Left nL
        mesh_id link_id dummy dummy
        ...
      Right nR
        mesh_id link_id dummy dummy
        ...
      ------------------------

    return:
      sec[ind]["L"] = [(mesh_id, link_id), ...]
      sec[ind]["R"] = [(mesh_id, link_id), ...]
    """
    sec = {}
    with open(path, "r") as f:
        while True:
            line = f.readline()
            if not line:
                break
            line = line.strip()
            if not line:
                continue

            try:
                ind = int(line.split()[0])
            except Exception:
                continue

            # Left
            left_line = f.readline()
            if not left_line:
                break
            t = left_line.strip().split()
            nL = int(t[1]) if len(t) >= 2 else 0
            L = []
            for _ in range(nL):
                s = f.readline().strip().split()
                if len(s) < 2:
                    continue
                mesh_id = int(s[0])
                link_id = int(s[1])
                L.append((mesh_id, link_id))

            # Right
            right_line = f.readline()
            if not right_line:
                break
            t = right_line.strip().split()
            nR = int(t[1]) if len(t) >= 2 else 0
            R = []
            for _ in range(nR):
                s = f.readline().strip().split()
                if len(s) < 2:
                    continue
                mesh_id = int(s[0])
                link_id = int(s[1])
                R.append((mesh_id, link_id))

            # separator
            _ = f.readline()

            sec[ind] = {"L": L, "R": R}

    return sec


def read_kasho(path: Path):
    """
    kasho_ini.dat を読む
    戻り値:
      nsec, header_line, rows
    rows は各断面について dict を持つ
    """
    rows = []
    with open(path, "r") as f:
        first = f.readline()
        if not first:
            raise RuntimeError(f"Empty file: {path}")
        nsec = int(first.strip())

        header_line = f.readline()
        if not header_line:
            raise RuntimeError(f"Header missing in: {path}")

        for _ in range(nsec):
            line = f.readline()
            if not line:
                break
            s = line.split()
            if len(s) < 10:
                continue

            row = {
                "ind":    int(s[0]),
                "dist":   float(s[1]),
                "kawa":   int(s[2]),
                "iptn":   int(s[3]),
                "hb":     float(s[4]),
                "teibol": float(s[5]),
                "teibor": float(s[6]),
                "rn":     float(s[7]),
                "dx":     float(s[8]),
                "inv_i":  float(s[9]),
            }
            rows.append(row)

    if len(rows) != nsec:
        raise RuntimeError(f"kasho rows mismatch: header says {nsec}, read {len(rows)}")

    return nsec, header_line, rows


def _reduce(zs, mode: str):
    if not zs:
        return None
    if mode == "max":
        return max(zs)
    if mode == "min":
        return min(zs)
    return sum(zs) / len(zs)


def choose_bank_z(pairs, link_pair, baseo, first_col_mode="ground", mode="mean"):
    """
    pairs: [(mesh_id, link_id), ...]

    first_col_mode="ground":
      riv_to_2d の1列目は地上メッシュID
      → そのまま baseo[mesh_id] を使う

    first_col_mode="river":
      riv_to_2d の1列目は河道メッシュID
      → link.dat の相手側メッシュを地上メッシュとして baseo を使う
    """
    zs = []

    for mesh_id, lk in pairs:
        if first_col_mode == "ground":
            if mesh_id in baseo:
                zs.append(baseo[mesh_id])

        elif first_col_mode == "river":
            if lk not in link_pair:
                continue
            m1, m2 = link_pair[lk]

            if m1 == mesh_id and m2 in baseo:
                zs.append(baseo[m2])
            elif m2 == mesh_id and m1 in baseo:
                zs.append(baseo[m1])

        else:
            raise ValueError(f"Unknown RIV2D_FIRST_COL mode: {first_col_mode}")

    return _reduce(zs, mode)


def find_reach_segments(rows):
    """
    iptn=-1 から iptn=1 までを1 reach とみなす
    戻り値:
      [(start_ind, end_ind), ...]   ここで ind は rows の添字ではなく断面番号
    """
    segments = []
    start = None

    for row in rows:
        ind = row["ind"]
        iptn = row["iptn"]

        if iptn == -1:
            start = ind

        if iptn == 1:
            if start is None:
                start = ind
            segments.append((start, ind))
            start = None

    if not segments:
        raise RuntimeError("No reach segments found from IPTN values.")

    return segments


def fill_linear_on_segment(raw_dict, start_ind, end_ind):
    """
    raw_dict[ind] = value or None
    start_ind..end_ind の範囲だけ補間
    """
    inds = list(range(start_ind, end_ind + 1))
    out = {ind: raw_dict.get(ind, None) for ind in inds}

    known = [ind for ind in inds if out[ind] is not None]
    if not known:
        return out

    # 前方埋め
    first = known[0]
    for ind in inds:
        if ind < first:
            out[ind] = out[first]

    # 後方埋め
    last = known[-1]
    for ind in inds:
        if ind > last:
            out[ind] = out[last]

    # 線形補間
    for a, b in zip(known[:-1], known[1:]):
        za = out[a]
        zb = out[b]
        gap = b - a
        if gap <= 1:
            continue
        for ind in range(a + 1, b):
            r = (ind - a) / gap
            out[ind] = za + (zb - za) * r

    return out


def main():
    base_dir = Path(__file__).resolve().parent

    # 読み込み
    nsec, header_line, rows = read_kasho(base_dir / FILE_KASHO_IN)
    sec = read_riv_to_2d(base_dir / FILE_RIV2D)
    link_pair = read_link_meshpair_3lines(base_dir / FILE_LINK)
    baseo = read_baseo(base_dir / FILE_BASEO)

    # 生の左右岸高
    zL_raw = {row["ind"]: None for row in rows}
    zR_raw = {row["ind"]: None for row in rows}

    for row in rows:
        ind = row["ind"]
        lr = sec.get(ind, {"L": [], "R": []})

        zL_raw[ind] = choose_bank_z(
            lr["L"], link_pair, baseo,
            first_col_mode=RIV2D_FIRST_COL,
            mode=BANK_MODE
        )
        zR_raw[ind] = choose_bank_z(
            lr["R"], link_pair, baseo,
            first_col_mode=RIV2D_FIRST_COL,
            mode=BANK_MODE
        )

    # reach ごとに補間
    zL = {}
    zR = {}
    segments = find_reach_segments(rows)

    for start_ind, end_ind in segments:
        zL_seg = fill_linear_on_segment(zL_raw, start_ind, end_ind)
        zR_seg = fill_linear_on_segment(zR_raw, start_ind, end_ind)
        zL.update(zL_seg)
        zR.update(zR_seg)

    # 全reachで全欠損なら危険
    if all(zL.get(row["ind"]) is None for row in rows):
        raise RuntimeError("All left-bank elevations are None. Check inputs.")
    if all(zR.get(row["ind"]) is None for row in rows):
        raise RuntimeError("All right-bank elevations are None. Check inputs.")

    # 出力
    out_path = base_dir / FILE_KASHO_OUT
    with open(out_path, "w", newline="\n") as f:
        f.write(f"{nsec:5d}\n")
        f.write(header_line if header_line.endswith("\n") else header_line + "\n")

        for row in rows:
            ind   = row["ind"]
            dist  = row["dist"]
            kawa  = row["kawa"]
            iptn  = row["iptn"]
            bed   = row["hb"]
            rn    = row["rn"]
            dx    = row["dx"]
            inv_i = row["inv_i"]

            zl = zL.get(ind)
            zr = zR.get(ind)

            # 断面に接続がまったく無く、補間もできなかった場合は元値を維持
            if zl is None:
                zl = row["teibol"]
            if zr is None:
                zr = row["teibor"]

            # 左右を揃える場合
            if FORCE_LR_EQUAL:
                if FORCE_MODE == "mean":
                    z = 0.5 * (zl + zr)
                else:
                    z = max(zl, zr)
                zl = zr = z

            # 河床より低くしない
            teibol = max(zl, bed + EPS_BED)
            teibor = max(zr, bed + EPS_BED)

            prefix15 = f"{ind:5d}{dist:5.2f}{kawa:3d}".ljust(15)

            f.write(
                f"{prefix15}"
                f"{iptn:5d}"
                f"{bed:11.3f}"
                f"{teibol:11.3f}"
                f"{teibor:11.3f}"
                f"{rn:11.3f}"
                f"{dx:11.1f}"
                f"{inv_i:10.1f}\n"
            )

    print(f"wrote {out_path}")


if __name__ == "__main__":
    main()