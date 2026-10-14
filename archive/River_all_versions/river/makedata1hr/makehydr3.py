#!/usr/bin/env python3
from pathlib import Path

# 時間条件
DT_HOURS = 0.5
T_TOTAL_HOURS = 6.0
N_STEPS = int(T_TOTAL_HOURS / DT_HOURS) + 1  # 0,0.5,...,6.0 -> 13

# 流量ハイドログラフのパラメータ
Q_BASE = 2.0     # [m3/s]
Q_PEAK = 80.0    # [m3/s]
T_PEAK = 2.0     # [h]
T_END  = 6.0     # [h]

# 下流水位ハイドログラフのパラメータ
H_BASE  = -3.5    # [m]
H_PEAK  = 0.5    # [m]
T_HPEAK = 4.0    # [h]
T_HEND  = 6.0    # [h]  # ★計算が6hなので、6hで戻すならここも6hに揃えるのが自然


def q_upstream(t_h: float) -> float:
    """上流流量 Q(t) [m3/s]（三角形）"""
    if t_h <= T_PEAK:
        return Q_BASE + (Q_PEAK - Q_BASE) * (t_h / T_PEAK)
    elif t_h <= T_END:
        return Q_BASE + (Q_PEAK - Q_BASE) * (T_END - t_h) / (T_END - T_PEAK)
    return Q_BASE


def h_downstream(t_h: float) -> float:
    """下流端水位 H(t) [m]（三角形）"""
    if t_h <= T_HPEAK:
        return H_BASE + (H_PEAK - H_BASE) * (t_h / T_HPEAK)
    elif t_h <= T_HEND:
        return H_BASE + (H_PEAK - H_BASE) * (T_HEND - t_h) / (T_HEND - T_HPEAK)
    return H_BASE


def main():
    out_path = Path("hydr3.dat")

    iup = 1  # 上流点の数
    idw = 1  # 下流点の数

    with open(out_path, "w", encoding="utf-8") as f:
        # ============
        # 上流流量データ
        # ============
        f.write("Q data for virtual river\n")
        f.write("mode something\n")
        f.write(f"{iup:5d}{N_STEPS:5d}\n")   # 1156 format(2i5) 想定
        f.write("Virtual river discharge\n")

        # i=1..iup ループに合わせるため、点ごとにブロックを書く
        for _ in range(iup):
            # 読み取り側で read(74,*) を1回挟むので、ここは「タイトル行」扱いの1行を入れておく
            f.write("Upstream point 1\n")
            for j in range(N_STEPS):
                t_h = j * DT_HOURS
                q = q_upstream(t_h)
                # 読み取り側：read(74,1158) qhyd_riv(i,j) で「floatだけ読む」想定
                # なので 15x + f14.6 に合うように、先頭に15スペース置く
                f.write(f"{'':15s}{q:14.6f}\n")

        # ============
        # 下流水位データ
        # ============
        f.write("H data for downstream\n")
        f.write("mode something\n")
        f.write(f"{idw:5d}{N_STEPS:5d}\n")   # 1156 format(2i5) 想定
        f.write("Water level at downstream\n")

        for _ in range(idw):
            f.write("Downstream point 1\n")
            for j in range(N_STEPS):
                t_h = j * DT_HOURS
                h = h_downstream(t_h)
                # 読み取り側：1157 format(15x, f10.2)
                f.write(f"{'':15s}{h:10.2f}\n")

    print(f"hydr.dat written: iup={iup}, idw={idw}, N_STEPS={N_STEPS} (DT={DT_HOURS}h, T={T_TOTAL_HOURS}h)")


if __name__ == "__main__":
    main()
