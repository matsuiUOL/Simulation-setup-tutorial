from pathlib import Path

# ==========================
# パラメータ
# ==========================
TOTAL_LENGTH_M = 2500.0   # 総延長 [m]
MSCTN          = 92       # 断面数（msctn）
Z_DOWNSTREAM   = -4.5      # 下流端の河床高 [m]
Z_UPSTREAM     = -1.5      # 上流端の河床高 [m]
H_BANK_L       = 4.0      # 左岸：河床から堤防天端までの高さ [m]
H_BANK_R       = 4.0      # 右岸：河床から堤防天端までの高さ [m]
N_MANNING      = 0.030    # 粗度係数
KAWA_ID        = 1        # 表示用（先頭15文字に入れるだけ）

LAST_DX_IS_ZERO = False   # 最終断面の dx2 を 0 にしたければ True
MIN_SLOPE_ABS   = 1.0e-12 # 0除算回避

def main():
    base_dir = Path(__file__).resolve().parent
    out_path = base_dir / "kasho3.dat"

    dx = TOTAL_LENGTH_M / (MSCTN - 1) if MSCTN > 1 else 0.0

    # ind=1 を上流、ind=MSCTN を下流（線形）
    def hb(ind: int) -> float:
        if MSCTN <= 1:
            return Z_UPSTREAM
        r = (ind - 1) / (MSCTN - 1)
        return Z_UPSTREAM + (Z_DOWNSTREAM - Z_UPSTREAM) * r

    # hb配列
    hb_list = [hb(i) for i in range(1, MSCTN + 1)]

    # abs(1/i)（局所勾配 i = Δhb/Δx）
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

    with open(out_path, "w", newline="\n") as f:
        # 1116 format(i5)
        f.write(f"{MSCTN:5d}\n")

        # read(70,*) で読み捨て
        f.write("   IND  DIST   KAWA IPTN      HB(m)                               RN      DX(m) abs(1/i)\n")

        for ind in range(1, MSCTN + 1):
            bed = hb_list[ind - 1]
            teibol = bed + H_BANK_L
            teibor = bed + H_BANK_R

            if ind == 1:
                iptn = -1
            elif ind == MSCTN:
                iptn = 1
            else:
                iptn = 0

            dx2 = 0.0 if (LAST_DX_IS_ZERO and ind == MSCTN) else dx

            # 先頭15文字（15xで読み捨てられる表示部）
            # 例に合わせて DIST を下流からの距離[km]っぽく減少させる
            s_m = (ind - 1) * dx
            dist_km = (TOTAL_LENGTH_M - s_m) / 1000.0
            prefix15 = f"{ind:5d}{dist_km:5.2f}{KAWA_ID:3d}".ljust(15)

            # 1117: (15x, i5, 4f11.3, f11.1, f10.1)
            # 最後列は abs(1/i) を入れる
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
