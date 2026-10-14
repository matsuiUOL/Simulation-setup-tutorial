#!/usr/bin/env python3
from pathlib import Path

# 時間条件
DT_HOURS = 0.5
T_TOTAL_HOURS = 6.0
N_STEPS = int(T_TOTAL_HOURS / DT_HOURS) + 1  

# 流量ハイドログラフのパラメータ
Q_BASE = 2.0     # [m3/s]
Q_PEAK = 80.0   # [m3/s]
T_PEAK = 2.0     # [h]
T_END  = 6.0    # [h]

# 下流水位ハイドログラフのパラメータ
H_BASE = 0.0     # [m] (相対値でもOK)
H_PEAK = 1.5     # [m]
T_HPEAK = 4.0   # [h]
T_HEND  = 8.0   # [h]


def q_upstream(t_h):
    """上流流量Q(t) [m3/s] (三角形ハイドログラフ)"""
    if t_h <= T_PEAK:
        return Q_BASE + (Q_PEAK - Q_BASE) * (t_h / T_PEAK)
    elif t_h <= T_END:
        return Q_BASE + (Q_PEAK - Q_BASE) * (T_END - t_h) / (T_END - T_PEAK)
    else:
        return Q_BASE


def h_downstream(t_h):
    """下流端水位H(t) [m] (三角形ハイドログラフ)"""
    if t_h <= T_HPEAK:
        return H_BASE + (H_PEAK - H_BASE) * (t_h / T_HPEAK)
    elif t_h <= T_HEND:
        return H_BASE + (H_PEAK - H_BASE) * (T_HEND - t_h) / (T_HEND - T_HPEAK)
    else:
        return H_BASE


def main():
    out_path = Path("hydr.dat")

    with open(out_path, "w") as f:
        # ============
        # 上流流量データ
        # ============
        f.write("Q data for virtual river\n")
        f.write("mode something\n")
        f.write(f"    2   {N_STEPS}\n")
        f.write("Virtual river discharge\n")

        for i in range(N_STEPS):
            t_h = i * DT_HOURS
            q = q_upstream(t_h)

            # 1行目：時刻インデックスと1つ目の流量
            f.write(f"{i:8d}{q:14.6f}\n")
            # 2行目：2つ目の流量（ここではとりあえず同じ値を入れておく）
            f.write(f"{'':12s}{q:14.6f}\n")

        # ============
        # 下流水位データ
        # ============
        f.write(f"    1   {N_STEPS}\n")
        f.write("Water level at downstream\n")

        for i in range(N_STEPS):
            t_h = i * DT_HOURS
            h = h_downstream(t_h)

            f.write(f"{i:8d}{h:10.2f}\n")
            f.write(f"{'':12s}{h:10.2f}\n")

    print(f"hydr.dat written with {N_STEPS} steps (0.5h interval for 24h).")


if __name__ == "__main__":
    main()
