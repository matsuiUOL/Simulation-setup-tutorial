#!/usr/bin/env python3
from pathlib import Path

H0 = 1.0        # 河床上の初期水深 [m]
Q0 = 1.0        # 全区間の初期流量 [m3/s]
QLAT0 = 0.0     # 初期横流入 [m3/s]

def read_kasho_bed(path):
    """
    kasho.dat から (IND, HB) のリストを読む。
    フォーマット例:
      92
       IND DISTANCE KAWA IPTN      HB(m) ...
        1  5.30   1   -1      4.400 ...
        2  5.25   1    0      4.150 ...
        ...
    """
    beds = []
    with open(path, "r") as f:
        # 1行目: 断面数
        nsec = int(f.readline().strip())
        # 2行目: ヘッダ
        header = f.readline()

        for _ in range(nsec):
            line = f.readline()
            if not line:
                break
            parts = line.split()
            if len(parts) < 5:
                continue
            ind = int(parts[0])
            hb = float(parts[4])  # HB(m) の列（例の5番目）に合わせる
            beds.append((ind, hb))
    return beds


def write_shoki(path, beds):
    with open(path, "w") as f:
        for ind, hb in beds:
            z_init = hb + H0
            q_init = Q0
            qlat_init = QLAT0
            f.write(f"{ind:5d} {z_init:12.8f} {q_init:12.8f} {qlat_init:12.8f}\n")


def main():
    base_dir = Path(__file__).resolve().parent
    kasho_path = base_dir / "kasho.dat"
    shoki_path = base_dir / "shoki.dat"

    beds = read_kasho_bed(kasho_path)
    write_shoki(shoki_path, beds)

    print(f"Wrote {shoki_path} with H0={H0}, Q0={Q0}, QLAT0={QLAT0}")


if __name__ == "__main__":
    main()
