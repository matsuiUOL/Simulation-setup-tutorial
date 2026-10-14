from pathlib import Path

# =========================================================
# reachごとの初期条件
# ---------------------------------------------------------
# inds : このreachに属する断面番号
# h0   : 河床上の初期水深 [m]
# q0   : 初期流量 [m3/s]
# qlat0: 初期横流入 [m3/s]（まずは 0 でよい）
# =========================================================
REACH_CONDITIONS = [
    {
        "name": "main_up",
        "inds": range(1, 31),     # 1..30
        "h0": 0.8,
        "q0": 2.0,
        "qlat0": 0.0,
    },
    {
        "name": "main_down",
        "inds": range(31, 62),    # 31..61
        "h0": 0.8,
        "q0": 2.0,
        "qlat0": 0.0,
    },
    {
        "name": "trib",
        "inds": range(62, 93),    # 62..92
        "h0": 0.8,
        "q0": 1.0,
        "qlat0": 0.0,
    },
]

INPUT_KASHO = "kasho_v2.dat"
OUTPUT_SHOKI = "shoki_v2.dat"


def read_kasho_bed(path: Path):
    """
    kasho.dat から (IND, HB) のリストを読む
    """
    beds = []
    with open(path, "r") as f:
        nsec = int(f.readline().strip())
        _ = f.readline()  # header

        for _ in range(nsec):
            line = f.readline()
            if not line:
                break
            parts = line.split()
            if len(parts) < 5:
                continue

            ind = int(parts[0])
            hb = float(parts[4])
            beds.append((ind, hb))

    return beds


def build_initial_condition_map():
    """
    ind -> (h0, q0, qlat0) を作る
    """
    cond_map = {}

    for rc in REACH_CONDITIONS:
        for ind in rc["inds"]:
            if ind in cond_map:
                raise RuntimeError(f"Duplicate initial condition for section {ind}")
            cond_map[ind] = (rc["h0"], rc["q0"], rc["qlat0"])

    return cond_map


def write_shoki(path: Path, beds, cond_map):
    with open(path, "w", newline="\n") as f:
        for ind, hb in beds:
            if ind not in cond_map:
                raise RuntimeError(f"No initial condition defined for section {ind}")

            h0, q0, qlat0 = cond_map[ind]
            z_init = hb + h0

            f.write(f"{ind:5d} {z_init:12.8f} {q0:12.8f} {qlat0:12.8f}\n")


def main():
    base_dir = Path(__file__).resolve().parent

    kasho_path = base_dir / INPUT_KASHO
    shoki_path = base_dir / OUTPUT_SHOKI

    beds = read_kasho_bed(kasho_path)
    cond_map = build_initial_condition_map()
    write_shoki(shoki_path, beds, cond_map)

    print(f"Wrote {shoki_path}")
    for rc in REACH_CONDITIONS:
        inds = list(rc["inds"])
        print(
            f"{rc['name']}: {inds[0]}..{inds[-1]}, "
            f"h0={rc['h0']} m, q0={rc['q0']} m3/s, qlat0={rc['qlat0']} m3/s"
        )


if __name__ == "__main__":
    main()