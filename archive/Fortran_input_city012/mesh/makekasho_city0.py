from pathlib import Path

# ==========================
# パラメータ（河床高など）
# ==========================
TOTAL_LENGTH_M = 3000.0    # 総延長 [m]
MSCTN          = 60        # 断面数
Z_DOWNSTREAM   = -6.0      # 下流端の河床高 [m]
Z_UPSTREAM     = -3.0      # 上流端の河床高 [m]

N_MANNING      = 0.030     # 粗度係数
KAWA_ID        = 1         # 表示用（先頭15文字に入れるだけ）

LAST_DX_IS_ZERO = False
MIN_SLOPE_ABS   = 1.0e-12

# 堤防高の代表値の取り方（1断面の複数リンクから1値へ）
BANK_MODE = "mean"   # "mean" / "max" / "min"

# 左右が本来同一にしたい場合の処理
FORCE_LR_EQUAL = True
FORCE_MODE = "max"   # FORCE_LR_EQUAL=True のとき "max" or "mean"

# 天端が河床より低くならないための微小量
EPS_BED = 1.0e-3

# ==========================
# 入力ファイル名（同一フォルダ想定）
# ==========================
FILE_BASEO = "bs_op_corrected_city0.dat"   # mesh_id, baseo
FILE_LINK  = "link0129_v2.dat"              # 3行/リンク形式（1行目に link_id, mesh1, mesh2 ...）
FILE_RIV2D = "riv_to_2d_v2_re.dat"         # indごとに Left/Right の (river_mesh_id, link_id, dummy, dummy)

OUT_KASHO  = "kasho_v2_city0.dat"


def read_baseo(path: Path):
    baseo = {}
    with open(path, "r") as f:
        for line in f:
            s = line.strip().split()
            if len(s) < 2:
                continue
            m = int(s[0])
            z = float(s[1])
            baseo[m] = z
    return baseo


def read_link_meshpair_3lines(linkdat: Path):
    """
    link.dat:
      header(1行)のあと、各リンクが3行
      1行目: link_id mesh1 mesh2 node1 node2
      2行目: dummy3(real)
      3行目: dummy2(real)
    return: dict[link_id] = (mesh1, mesh2)
    """
    pair = {}
    with open(linkdat, "r") as f:
        _ = f.readline()  # 5504 など

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

            # 2行目・3行目は読み捨て
            _ = f.readline()
            _ = f.readline()

    return pair


def read_riv_to_2d3(path: Path):
    """
    riv_to_2d3.dat の見方（ユーザー定義）：
      ind
      Left nL
        river_mesh_id  link_id  dummy dummy
        ...
      Right nR
        river_mesh_id  link_id  dummy dummy
        ...
      ------------------------

    return:
      sec[ind]["L"] = [(river_mesh_id, link_id), ...]
      sec[ind]["R"] = [(river_mesh_id, link_id), ...]
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
            except:
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
                river_mesh = int(s[0])
                link_id    = int(s[1])
                L.append((river_mesh, link_id))

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
                river_mesh = int(s[0])
                link_id    = int(s[1])
                R.append((river_mesh, link_id))

            # separator
            _ = f.readline()

            sec[ind] = {"L": L, "R": R}

    return sec


def _reduce(zs, mode: str):
    if not zs:
        return None
    if mode == "max":
        return max(zs)
    if mode == "min":
        return min(zs)
    return sum(zs) / len(zs)


def choose_bank_z_using_rivmesh(pairs, link_pair, baseo, mode="mean"):
    """
    pairs: [(river_mesh_id, link_id), ...]
    link_pair[link_id] = (m1, m2)

    riv_to_2d3 に入っている river_mesh_id を「河道側メッシュ」とみなし、
    link.dat の (m1,m2) のうち river_mesh と反対側を「地上側」として baseo を拾う。
    """
    zs = []
    for river_mesh, lk in pairs:
        if lk not in link_pair:
            continue
        m1, m2 = link_pair[lk]

        if m1 == river_mesh and m2 in baseo:
            zs.append(baseo[m2])
        elif m2 == river_mesh and m1 in baseo:
            zs.append(baseo[m1])
        else:
            # link.dat の隣接メッシュに river_mesh が無い等：不整合の可能性
            pass

    return _reduce(zs, mode)


def fill_linear(series_dict, n):
    """
    series_dict: dict[ind] = value or None  (indは1..n)
    戻り: list out (1-indexで out[ind] を使う)
      - 両側に既知点がある None は線形補間
      - 片側しかない None は最近傍で埋める（前方/後方埋め）
    """
    out = [None] * (n + 1)
    for i in range(1, n + 1):
        out[i] = series_dict.get(i, None)

    known = [i for i in range(1, n + 1) if out[i] is not None]
    if not known:
        return out

    # 前方埋め
    first = known[0]
    for i in range(1, first):
        out[i] = out[first]

    # 後方埋め
    last = known[-1]
    for i in range(last + 1, n + 1):
        out[i] = out[last]

    # 線形補間
    for a, b in zip(known[:-1], known[1:]):
        za = out[a]
        zb = out[b]
        gap = b - a
        if gap <= 1:
            continue
        for i in range(a + 1, b):
            r = (i - a) / gap
            out[i] = za + (zb - za) * r

    return out


def main():
    base_dir = Path(__file__).resolve().parent

    # ---- 入力読み込み
    baseo = read_baseo(base_dir / FILE_BASEO)
    link_pair = read_link_meshpair_3lines(base_dir / FILE_LINK)
    sec = read_riv_to_2d3(base_dir / FILE_RIV2D)

    # ---- 河床高：線形
    dx = TOTAL_LENGTH_M / (MSCTN - 1) if MSCTN > 1 else 0.0

    def hb(ind: int) -> float:
        if MSCTN <= 1:
            return Z_UPSTREAM
        r = (ind - 1) / (MSCTN - 1)
        return Z_UPSTREAM + (Z_DOWNSTREAM - Z_UPSTREAM) * r

    hb_list = [hb(i) for i in range(1, MSCTN + 1)]

    # abs(1/i)
    inv_i_list = []
    if MSCTN <= 1:
        inv_i_list = [1.0 / MIN_SLOPE_ABS]
    else:
        for idx in range(MSCTN):
            if idx < MSCTN - 1:
                slope = (hb_list[idx + 1] - hb_list[idx]) / dx
            else:
                slope = (hb_list[idx] - hb_list[idx - 1]) / dx
            a = abs(slope)
            if a < MIN_SLOPE_ABS:
                a = MIN_SLOPE_ABS
            inv_i_list.append(1.0 / a)

    # ---- まずは「取れる断面だけ」左右堤防高を作る（取れない断面は None）
    zL_raw = {i: None for i in range(1, MSCTN + 1)}
    zR_raw = {i: None for i in range(1, MSCTN + 1)}

    for ind in range(1, MSCTN + 1):
        lr = sec.get(ind, {"L": [], "R": []})
        zL_raw[ind] = choose_bank_z_using_rivmesh(lr["L"], link_pair, baseo, mode=BANK_MODE)
        zR_raw[ind] = choose_bank_z_using_rivmesh(lr["R"], link_pair, baseo, mode=BANK_MODE)

    # ---- 欠損断面は前後断面から線形補間
    zL = fill_linear(zL_raw, MSCTN)
    zR = fill_linear(zR_raw, MSCTN)

    # もし全断面欠損なら危険（この場合は baseo が読めてない等）
    if all(zL[i] is None for i in range(1, MSCTN + 1)) or all(zR[i] is None for i in range(1, MSCTN + 1)):
        raise RuntimeError("All bank elevations are None. Check riv_to_2d3.dat / link.dat / baseo file consistency.")

    # ---- 出力
    out_path = base_dir / OUT_KASHO
    with open(out_path, "w", newline="\n") as f:
        f.write(f"{MSCTN:5d}\n")
        f.write("   IND  DIST   KAWA IPTN      HB(m)                               RN      DX(m) abs(1/i)\n")

        for ind in range(1, MSCTN + 1):
            bed = hb_list[ind - 1]

            zl = zL[ind]
            zr = zR[ind]

            # 念のため None ガード（通常ここには来ない）
            if zl is None:
                zl = bed + 1.0
            if zr is None:
                zr = bed + 1.0

            # 左右を同じに揃える（比較のための“フラット化”）
            if FORCE_LR_EQUAL:
                if FORCE_MODE == "mean":
                    z = 0.5 * (zl + zr)
                else:
                    z = max(zl, zr)
                zl = zr = z

            # 天端 >= 河床
            teibol = max(zl, bed + EPS_BED)
            teibor = max(zr, bed + EPS_BED)

            # iptn
            if ind == 1:
                iptn = -1
            elif ind == MSCTN:
                iptn = 1
            else:
                iptn = 0

            dx2 = 0.0 if (LAST_DX_IS_ZERO and ind == MSCTN) else dx

            # 先頭15文字（表示部）
            s_m = (ind - 1) * dx
            dist_km = (TOTAL_LENGTH_M - s_m) / 1000.0
            prefix15 = f"{ind:5d}{dist_km:5.2f}{KAWA_ID:3d}".ljust(15)

            f.write(
                f"{prefix15}"
                f"{iptn:5d}"
                f"{bed:11.3f}"
                f"{teibol:11.3f}"
                f"{teibor:11.3f}"
                f"{N_MANNING:11.3f}"
                f"{dx2:11.1f}"
                f"{inv_i_list[ind-1]:10.1f}\n"
            )

    print(f"wrote {out_path}")


if __name__ == "__main__":
    main()
