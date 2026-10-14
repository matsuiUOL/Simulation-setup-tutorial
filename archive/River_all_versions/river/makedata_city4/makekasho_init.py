from pathlib import Path

# ==========================
# 共通パラメータ
# ==========================
H_BANK_L        = 4.0
H_BANK_R        = 4.0
N_MANNING       = 0.030
KAWA_ID         = 1
MIN_SLOPE_ABS   = 1.0e-12
END_INV_I       = 999999.0   # 下流端・合流端用
END_DX          = 0.0

# ==========================
# reach定義
# ==========================
REACHES = [
    {
        "name": "main_up",
        "inds": list(range(1, 31)),      # 1..30
        "total_length_m": 1500.0,
        "z_upstream": -1.5,
        "z_downstream": -3.0,
        "dist_down_end_km": 1.5,
    },
    {
        "name": "main_down",
        "inds": list(range(31, 62)),     # 31..61
        "total_length_m": 1500.0,
        "z_upstream": -3.0,
        "z_downstream": -4.5,
        "dist_down_end_km": 0.0,
    },
    {
        "name": "trib",
        "inds": list(range(62, 93)),     # 62..92
        "total_length_m": 1500.0,
        "z_upstream": -1.0,
        "z_downstream": -3.0,
        "dist_down_end_km": 1.5,
    },
]

OUT_FILE = "kasho_v2_ini_confluence.dat"


def build_reach_geometry(reach):
    inds = reach["inds"]
    n = len(inds)

    if n == 0:
        raise ValueError(f"reach {reach['name']} has no inds")

    if n == 1:
        ind = inds[0]
        hb_map = {ind: reach["z_upstream"]}
        inv_i_map = {ind: END_INV_I}
        dist_map = {ind: reach["dist_down_end_km"]}
        iptn_map = {ind: 1}
        dx_map = {ind: END_DX}
        end_ind = ind
        return hb_map, inv_i_map, dist_map, iptn_map, dx_map, end_ind

    total_length = reach["total_length_m"]
    dx = total_length / (n - 1)

    hb_list = []
    for j in range(n):
        r = j / (n - 1)
        z = reach["z_upstream"] + (reach["z_downstream"] - reach["z_upstream"]) * r
        hb_list.append(z)

    hb_map = {ind: hb_list[j] for j, ind in enumerate(inds)}

    inv_i_map = {}
    for j, ind in enumerate(inds):
        if j < n - 1:
            slope = (hb_list[j + 1] - hb_list[j]) / dx
        else:
            slope = (hb_list[j] - hb_list[j - 1]) / dx

        a = abs(slope)
        if a < MIN_SLOPE_ABS:
            a = MIN_SLOPE_ABS
        inv_i_map[ind] = 1.0 / a

    dist_map = {}
    for j, ind in enumerate(inds):
        s_m = j * dx
        dist_km = reach["dist_down_end_km"] + (total_length - s_m) / 1000.0
        dist_map[ind] = dist_km

    iptn_map = {}
    for j, ind in enumerate(inds):
        if j == 0:
            iptn_map[ind] = -1
        elif j == n - 1:
            iptn_map[ind] = 1
        else:
            iptn_map[ind] = 0

    dx_map = {ind: dx for ind in inds}

    end_ind = inds[-1]   # そのreachの下流端
    return hb_map, inv_i_map, dist_map, iptn_map, dx_map, end_ind


def main():
    base_dir = Path(__file__).resolve().parent
    out_path = base_dir / OUT_FILE

    all_inds = []
    for reach in REACHES:
        all_inds.extend(reach["inds"])

    if len(all_inds) != len(set(all_inds)):
        raise RuntimeError("REACHES 内で断面番号が重複しています。")

    msctn = max(all_inds)

    hb_all = {}
    inv_i_all = {}
    dist_all = {}
    iptn_all = {}
    dx_all = {}
    reach_end_inds = set()

    for reach in REACHES:
        hb_map, inv_i_map, dist_map, iptn_map, dx_map, end_ind = build_reach_geometry(reach)
        hb_all.update(hb_map)
        inv_i_all.update(inv_i_map)
        dist_all.update(dist_map)
        iptn_all.update(iptn_map)
        dx_all.update(dx_map)
        reach_end_inds.add(end_ind)

    missing = [ind for ind in range(1, msctn + 1) if ind not in hb_all]
    if missing:
        raise RuntimeError(f"断面番号が未定義です: {missing}")

    with open(out_path, "w", newline="\n") as f:
        f.write(f"{msctn:5d}\n")
        f.write("   IND  DIST   KAWA IPTN      HB(m)                               RN      DX(m) abs(1/i)\n")

        for ind in range(1, msctn + 1):
            bed = hb_all[ind]
            teibol = bed + H_BANK_L
            teibor = bed + H_BANK_R

            # 各reachの下流端を特別処理
            if ind in reach_end_inds:
                dx2 = END_DX
                inv_i = END_INV_I
            else:
                dx2 = dx_all[ind]
                inv_i = inv_i_all[ind]

            prefix15 = f"{ind:5d}{dist_all[ind]:5.2f}{KAWA_ID:3d}".ljust(15)

            f.write(
                f"{prefix15}"
                f"{iptn_all[ind]:5d}"
                f"{bed:11.3f}"
                f"{teibol:11.3f}"
                f"{teibor:11.3f}"
                f"{N_MANNING:11.3f}"
                f"{dx2:11.1f}"
                f"{inv_i:10.1f}\n"
            )

    print(f"wrote {out_path}")


if __name__ == "__main__":
    main()