#!/usr/bin/env python3
from pathlib import Path


# ======================
# パラメータ設定
# ======================

TOTAL_LENGTH = 2500.0   # 河川総延長 [m]
N_SECTIONS   = 51       # 断面数（= isctn に合わせる）
WIDTH        = 30.0     # 横断方向幅 [m]
DX_CROSS     = 5.0      # 横断方向の点間隔 [m] → 0,5,10,...,30
N_POINTS     = int(WIDTH / DX_CROSS) + 1  # = 7

Z_UPSTREAM   = 5.0      # 上流側の河床高 [m]
Z_DOWNSTREAM = 4.0      # 下流側の河床高 [m]

# 河床勾配（上流→下流で低くなる）
SLOPE = (Z_UPSTREAM - Z_DOWNSTREAM) / TOTAL_LENGTH  # ≒ 0.0004


def bed_elevation_along_river(s):
    """
    縦断距離 s [m]（上流=0, 下流=TOTAL_LENGTH）における河床高 z_b を返す。
    上流 5.0 m → 下流 4.0 m の直線勾配。
    """
    return Z_UPSTREAM - SLOPE * s


def generate_cross_section(base_bed, width=WIDTH):
    """
    1つの断面の x,y 配列を生成する。
    - x: 0, 5, 10, ..., 30 [m]
    - y: 左右が高く、中央が低い「谷＋堤防」形状
    """
    xs = [i * DX_CROSS for i in range(N_POINTS)]

    levee_height = 3.0
    mid_high = base_bed + 0.3 * levee_height   # 中央付近の地盤
    mid_mid  = base_bed + 0.5 * levee_height   # 斜面中間
    z_left   = base_bed + levee_height         # 左岸堤防
    z_right  = base_bed + levee_height         # 右岸堤防

    # ymin となる谷底を中央に置く
    ys = [
        z_left,         # x=0   左岸堤防
        mid_mid,        # x=5
        mid_high,       # x=10
        base_bed,       # x=15  谷底（最低標高）
        mid_high,       # x=20
        mid_mid,        # x=25
        z_right,        # x=30  右岸堤防
    ]

    return xs, ys


def write_river_danmen(path: Path):
    """
    river_danmen.dat を作成する。
    Fortran の読み方:
      read(10, *)        ! ヘッダ
      do i = 1, isctn
        read(10, *) dd, ko(i)
        do k = 1, ko(i)
          read(10, *) nn, x(i,k), y(i,k)
        enddo
        read(10, *)      ! 区切り行
      enddo
    に対応する形式で出力する。
    """
    with open(path, "w") as f:
        # 1行目ヘッダ（中身は何でもよい）
        f.write("Virtual river cross-sections for 2500m river\n")

        # 断面間隔（縦断方向）
        ds = TOTAL_LENGTH / (N_SECTIONS - 1)

        for i in range(N_SECTIONS):
            # 縦断距離（ここでは上流=0, 下流=TOTAL_LENGTH）
            s = i * ds
            # base_bed: この断面の谷底の標高
            base_bed = bed_elevation_along_river(s)

            # x, y 配列生成
            xs, ys = generate_cross_section(base_bed, width=WIDTH)

            # 断面 i の先頭行: dd, ko
            dd = s  # 縦断距離を入れておく（Fortran側では現状使っていない）
            ko = len(xs)
            f.write(f"{dd:10.2f} {ko:4d}\n")

            # 断面内の各点: nn, x, y
            for k, (x, y) in enumerate(zip(xs, ys), start=1):
                f.write(f"{k:4d} {x:10.3f} {y:10.3f}\n")

            # 区切り行（空行）
            f.write("\n")


def main():
    base_dir = Path(__file__).resolve().parent
    out_path = base_dir / "river_danmen.dat"

    write_river_danmen(out_path)

    print(f"river_danmen.dat written to: {out_path}")
    print(f"  TOTAL_LENGTH = {TOTAL_LENGTH} m")
    print(f"  N_SECTIONS   = {N_SECTIONS}")
    print(f"  N_POINTS per section = {N_POINTS}")
    print("Fortran側では isctn を N_SECTIONS に合わせてください。")


if __name__ == "__main__":
    main()
