#!/usr/bin/env python3
from pathlib import Path

# ==========================
# パラメータ
# ==========================

TOTAL_LENGTH_M = 2500.0   # 総延長 [m]
NSEC           = 92       # 断面数
Z_DOWNSTREAM   = -4.5      # 河口（下流端）の河床高 [m]
Z_UPSTREAM     = -1.5      # 上流端の河床高 [m]
H_BANK         = 4.0      # 河床から堤防天端までの高さ [m]
N_MANNING      = 0.030    # 粗度係数
KAWA_ID        = 1        # 河川番号

def main():
    base_dir = Path(__file__).resolve().parent
    out_path = base_dir / "kasho3.dat"

    # 河床勾配（上流→下流で低くなる想定）
    slope = (Z_UPSTREAM - Z_DOWNSTREAM) / TOTAL_LENGTH_M  # > 0

    # 断面間距離（m）
    if NSEC > 1:
        dx = TOTAL_LENGTH_M / (NSEC - 1)
    else:
        dx = 0.0

    with open(out_path, "w") as f:
        # 1 行目：断面数
        f.write(f"{NSEC:5d}\n")
        # 2 行目：ヘッダ（フォーマットはあなたの例に合わせる）
        f.write("   IND DISTANCE KAWA IPTN      HB(m)                               RN      DX(m) \n")

        for ind in range(1, NSEC + 1):
            # 河口からの縦断距離 [m]
            s_m = (ind - 1) * dx  # ind=1で0m, ind=NSECでTOTAL_LENGTH_M

            # 河床高（上流が高く下流が低い）
            # ここでは上流=TOTAL_LENGTH_M, 下流=0 として、
            # bed(s)=Z_DOWNSTREAM + slope*(TOTAL_LENGTH_M - s)
            bed = Z_DOWNSTREAM + slope * (TOTAL_LENGTH_M - s_m)

            # 左右堤防高
            z_left  = bed + H_BANK
            z_right = bed + H_BANK

            # DISTANCE は「河口からの距離 [km]」と仮定
            dist_km = s_m / 1000.0

            # IPTN の設定
            if ind == 1:
                iptn = -1   # 上流端 or 下流端は好みだが、例と合わせるなら端でフラグ
            elif ind == NSEC:
                iptn = 1    # もう一方の端
            else:
                iptn = 0    # 中間

            # DX は一様 dx（最後の断面だけ 0.0 にする場合は条件分岐してもOK）
            dx_loc = dx if ind < NSEC else dx  # とりあえず全区間同じとする

            # 1 行分を書き出し
            f.write(
                f"{ind:5d} "
                f"{dist_km:4.2f}   "
                f"{KAWA_ID:1d}   "
                f"{iptn:2d}  "
                f"{bed:10.3f}  "
                f"{z_left:10.3f}  "
                f"{z_right:10.3f}  "
                f"{N_MANNING:7.3f}  "
                f"{dx_loc:9.1f}\n"
            )

    print(f"wrote {out_path}")


if __name__ == "__main__":
    main()
