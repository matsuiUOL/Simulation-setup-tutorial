#!/usr/bin/env python3
from pathlib import Path

# =========================================================
# 時間条件
# =========================================================
DT_HOURS = 0.5
T_TOTAL_HOURS = 6.0
N_STEPS = int(T_TOTAL_HOURS / DT_HOURS) + 1   # 0,0.5,...,6.0

# =========================================================
# 本川上流ハイドログラフ
# =========================================================
Q_MAIN_BASE = 2.0
Q_MAIN_PEAK = 2.0
T_MAIN_PEAK = 2.0
T_MAIN_END  = 2.0

# =========================================================
# 支川上流ハイドログラフ
# =========================================================
Q_TRIB_BASE = 1.0
Q_TRIB_PEAK = 1.0
T_TRIB_PEAK = 2.5
T_TRIB_END  = 6.0

# =========================================================
# 下流端水位ハイドログラフ
# =========================================================
H_BASE  = -3.0
H_PEAK  = -3.0
T_HPEAK = 4.0
T_HEND  = 6.0

OUT_FILE = "hydr_v2.dat"


def triangle_hydrograph(t_h, q_base, q_peak, t_peak, t_end):
    """三角形ハイドログラフ"""
    if t_h <= t_peak:
        return q_base + (q_peak - q_base) * (t_h / t_peak)
    elif t_h <= t_end:
        return q_base + (q_peak - q_base) * (t_end - t_h) / (t_end - t_peak)
    else:
        return q_base


def q_main_upstream(t_h):
    return triangle_hydrograph(
        t_h,
        Q_MAIN_BASE, Q_MAIN_PEAK,
        T_MAIN_PEAK, T_MAIN_END
    )


def q_trib_upstream(t_h):
    return triangle_hydrograph(
        t_h,
        Q_TRIB_BASE, Q_TRIB_PEAK,
        T_TRIB_PEAK, T_TRIB_END
    )


def h_downstream(t_h):
    if t_h <= T_HPEAK:
        return H_BASE + (H_PEAK - H_BASE) * (t_h / T_HPEAK)
    elif t_h <= T_HEND:
        return H_BASE + (H_PEAK - H_BASE) * (T_HEND - t_h) / (T_HEND - T_HPEAK)
    return H_BASE


def main():
    out_path = Path(OUT_FILE)

    iup = 2   # 本川上流 + 支川上流
    idw = 1   # 最下流水位

    with open(out_path, "w", encoding="utf-8", newline="\n") as f:
        # =====================================================
        # 上流流量データ
        # =====================================================
        f.write("Q data for confluence river\n")
        f.write("mode something\n")
        f.write(f"{iup:5d}{N_STEPS:5d}\n")
        f.write("Confluence river discharge\n")

        # ---- 上流点1: 本川上流 ----
        f.write("Main upstream point\n")
        for j in range(N_STEPS):
            t_h = j * DT_HOURS
            q = q_main_upstream(t_h)
            f.write(f"{'':15s}{q:14.6f}\n")

        # ---- 上流点2: 支川上流 ----
        f.write("Tributary upstream point\n")
        for j in range(N_STEPS):
            t_h = j * DT_HOURS
            q = q_trib_upstream(t_h)
            f.write(f"{'':15s}{q:14.6f}\n")

        # =====================================================
        # 下流水位データ
        # =====================================================
        f.write("H data for downstream\n")
        f.write("mode something\n")
        f.write(f"{idw:5d}{N_STEPS:5d}\n")
        f.write("Water level at downstream end\n")

        f.write("Downstream point 1\n")
        for j in range(N_STEPS):
            t_h = j * DT_HOURS
            h = h_downstream(t_h)
            f.write(f"{'':15s}{h:10.2f}\n")

    print(f"written: {out_path}")
    print(f"  iup={iup}, idw={idw}, N_STEPS={N_STEPS}")
    print(f"  DT={DT_HOURS} h, T_TOTAL={T_TOTAL_HOURS} h")


if __name__ == "__main__":
    main()