#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
make_hahr_from_kasho.py

kasho.dat の HB（河床高）を使って、堤防なし・地盤高0.0m接続の台形河道断面を仮定し、
h-a.dat（水深-断面積）と h-r.dat（水深-径深）を作成するスクリプト。

想定する kasho.dat の主な列：
  1列目: 断面番号
  5列目: HB（河床高）
  6列目: TEIBOL（左岸高）※本スクリプトでは使わない
  7列目: TEIBOR（右岸高）※本スクリプトでは使わない

断面形状：
  x=0               y=GROUND_ELEV
  x=(TOP-BED)/2     y=HB
  x=(TOP+BED)/2     y=HB
  x=TOP_WIDTH       y=GROUND_ELEV

つまり、河道は地表面 y=0.0 m に幅 TOP_WIDTH で接続する台形断面。
"""

import math
from pathlib import Path


# =========================
# 設定
# =========================
KASHO_PATH = Path("kasho_v2_city0.dat")

OUT_HA = Path("h-a_test.dat")
OUT_HR = Path("h-r_test.dat")
OUT_DANMEN = Path("river_danmen_from_kasho_test.dat")

# 地表面標高 [m]
GROUND_ELEV = 0.0

# 河道上端幅 [m]：地表面と接続する幅
TOP_WIDTH = 30.0

# 河床幅 [m]：台形底面の幅
# 例：15 mなら、x=7.5〜22.5 m が平坦な河床
BED_WIDTH = 30.0

# h-a, h-r の水位刻み [m]
DH = 0.1

# 地表面よりどこまで上の水位まで表を作るか [m]
# 旧スクリプトの h_stop = crest + 3.0 に相当
FREEBOARD_EXTRA = 3.0

# 出力時の1行あたりの値数
VALUES_PER_LINE = 10


def read_kasho(path: Path):
    """
    kasho.dat を読み込み、数値行から断面番号と HB を取得する。
    5列目（0-based index=4）を HB として扱う。
    """
    sections = []

    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            stripped = line.strip()
            if not stripped:
                continue

            parts = stripped.split()

            # 数値行だけ処理
            try:
                vals = [float(p) for p in parts]
            except ValueError:
                continue

            if len(vals) < 5:
                continue

            sec_id = int(vals[0])
            hb = vals[4]

            sections.append({
                "id": sec_id,
                "hb": hb,
                "raw": vals,
            })

    if not sections:
        raise RuntimeError("kasho.dat から断面データを読み取れませんでした。列構造を確認してください。")

    return sections


def make_trapezoid_points(hb: float,
                          top_width: float = TOP_WIDTH,
                          bed_width: float = BED_WIDTH,
                          ground: float = GROUND_ELEV):
    """
    台形断面の点列を作る。
    両岸は ground、河床は hb。
    """
    if bed_width <= 0.0:
        raise ValueError("BED_WIDTH は正の値にしてください。")
    if bed_width > top_width:
        raise ValueError("BED_WIDTH は TOP_WIDTH より小さくしてください。")

    x_left_top = 0.0
    x_left_bed = (top_width - bed_width) / 2.0
    x_right_bed = (top_width + bed_width) / 2.0
    x_right_top = top_width

    xs = [x_left_top, x_left_bed, x_right_bed, x_right_top]
    ys = [ground, hb, hb, ground]

    return xs, ys


def compute_area_wetted_perimeter(xs, ys, water_level):
    """
    任意の多角線断面について、水位 water_level 以下の断面積 A と濡れ縁長 P を計算する。
    点列 xs, ys は左から右に並んでいる前提。

    今回は単純な台形なので、この汎用処理で十分。
    """
    area = 0.0
    wetted_perimeter = 0.0

    n = len(xs)

    for i in range(n - 1):
        x1, y1 = xs[i], ys[i]
        x2, y2 = xs[i + 1], ys[i + 1]

        d1 = water_level - y1
        d2 = water_level - y2
        dx = x2 - x1

        # 両端とも水面以上
        if d1 <= 0.0 and d2 <= 0.0:
            continue

        # 両端とも水没
        if d1 > 0.0 and d2 > 0.0:
            area += 0.5 * (d1 + d2) * dx
            wetted_perimeter += math.hypot(dx, y2 - y1)
            continue

        # 一部だけ水没：交点を求める
        # y = y1 + t*(y2-y1), water_level となる t
        if y2 != y1:
            t = (water_level - y1) / (y2 - y1)
        else:
            # 水平線分で片側だけ水没は通常起きない
            t = 0.0

        t = max(0.0, min(1.0, t))
        x_int = x1 + t * dx

        if d1 > 0.0 and d2 <= 0.0:
            # 左側だけ水没
            submerged_dx = x_int - x1
            area += 0.5 * d1 * submerged_dx
            wetted_perimeter += math.hypot(submerged_dx, water_level - y1)

        elif d1 <= 0.0 and d2 > 0.0:
            # 右側だけ水没
            submerged_dx = x2 - x_int
            area += 0.5 * d2 * submerged_dx
            wetted_perimeter += math.hypot(submerged_dx, y2 - water_level)

    return area, wetted_perimeter


def compute_ha_hr_for_section(hb: float):
    """
    1断面について、h-a, h-r 用の配列を作る。
    ここでは water_level = HB + depth として、depth を DH 刻みで増やす。
    """
    xs, ys = make_trapezoid_points(hb)

    max_depth = (GROUND_ELEV - hb) + FREEBOARD_EXTRA
    n_steps = int(math.floor(max_depth / DH + 1.0e-9))

    areas = []
    radii = []

    for ih in range(1, n_steps + 1):
        water_level = hb + ih * DH

        a, p = compute_area_wetted_perimeter(xs, ys, water_level)

        if a <= 0.0 or p <= 0.0:
            areas.append(0.0)
            radii.append(0.0)
        else:
            areas.append(a)
            radii.append(a / p)

    return areas, radii


def write_values(f, vals):
    """
    Fortranで読みやすいように、旧スクリプトと同様に
    最初に dummy 0.000 を入れて出力。
    """
    line_vals = ["    0.000"]

    for v in vals:
        line_vals.append(f"{v:10.3f}")

        if len(line_vals) == VALUES_PER_LINE:
            f.write("".join(line_vals) + "\n")
            line_vals = []

    if line_vals:
        f.write("".join(line_vals) + "\n")


def write_ha_hr(sections, out_ha: Path, out_hr: Path):
    with open(out_ha, "w") as f_a, open(out_hr, "w") as f_r:
        for idx, sec in enumerate(sections, start=1):
            hb = sec["hb"]
            areas, radii = compute_ha_hr_for_section(hb)

            num = len(areas)

            # 旧スクリプトと同じく、dummy 0.0 を含めるので num+1
            f_a.write(f"{idx:3d}{num+1:10d}\n")
            f_r.write(f"{idx:3d}{num+1:10d}\n")

            write_values(f_a, areas)
            write_values(f_r, radii)


def write_river_danmen(sections, out_path: Path):
    """
    確認用に、生成した台形断面を river_danmen 形式でも出力する。
    """
    with open(out_path, "w") as f:
        f.write("Trapezoidal cross-sections generated from kasho.dat\n")

        for idx, sec in enumerate(sections, start=1):
            hb = sec["hb"]
            xs, ys = make_trapezoid_points(hb)

            # dd はここでは断面番号相当として出力
            dd = float(idx)
            ko = len(xs)

            f.write(f"{dd:10.2f} {ko:4d}\n")
            for k, (x, y) in enumerate(zip(xs, ys), start=1):
                f.write(f"{k:4d} {x:10.3f} {y:10.3f}\n")
            f.write("\n")


def main():
    sections = read_kasho(KASHO_PATH)

    print(f"Read {len(sections)} sections from {KASHO_PATH}")
    print(f"First HB = {sections[0]['hb']:.3f}")
    print(f"Last  HB = {sections[-1]['hb']:.3f}")
    print(f"TOP_WIDTH = {TOP_WIDTH:.3f} m")
    print(f"BED_WIDTH = {BED_WIDTH:.3f} m")
    print(f"GROUND_ELEV = {GROUND_ELEV:.3f} m")

    write_ha_hr(sections, OUT_HA, OUT_HR)
    write_river_danmen(sections, OUT_DANMEN)

    print(f"Wrote {OUT_HA}")
    print(f"Wrote {OUT_HR}")
    print(f"Wrote {OUT_DANMEN}")


if __name__ == "__main__":
    main()
