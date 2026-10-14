#!/usr/bin/env python3
import math
from pathlib import Path


# =========================================================
# 設定
# =========================================================
INPUT_RIVER_DANMEN = "river_danmen_v2.dat"
OUTPUT_HA = "h-a_v2.dat"
OUTPUT_HR = "h-r_v2.dat"

DH = 0.1
MAX_STEPS = 400


def read_river_danmen(path, isctn=None):
    """
    river_danmen_confluence.dat を読み込む。

    形式:
      1行目: ヘッダ
      各断面ブロック:
        dd ko
        nn x y   (× ko 行)
        空行

    戻り値:
      sections = [
        {"dd": float, "x": [..], "y": [..]},
        ...
      ]
    """
    sections = []

    with open(path, "r") as f:
        _ = f.readline()  # ヘッダ読み飛ばし

        while True:
            line = f.readline()
            if not line:
                break

            line = line.strip()
            if line == "":
                continue

            parts = line.split()
            if len(parts) < 2:
                continue

            dd = float(parts[0])
            ko = int(parts[1])

            xs = []
            ys = []
            for _ in range(ko):
                l = f.readline()
                if not l:
                    raise RuntimeError("Unexpected EOF while reading cross-section points")

                pp = l.split()
                if len(pp) < 3:
                    raise RuntimeError("Line in river_danmen has fewer than 3 columns")

                x = float(pp[1])
                y = float(pp[2])
                xs.append(x)
                ys.append(y)

            # 区切り行（空行）を1行読み飛ばし
            _ = f.readline()

            sections.append({"dd": dd, "x": xs, "y": ys})

            if isctn is not None and len(sections) >= isctn:
                break

    return sections


def find_ymin_and_levees(xs, ys):
    """
    Fortran と同じ考え方:
      - ymin: 最低標高
      - km:   最低標高点のインデックス
      - kos:  左岸堤防候補（kmより左で最大 y）
      - koe:  右岸堤防候補（kmより右で最大 y）
    """
    n = len(xs)

    ymin = 1.0e30
    km = 0
    for k in range(n):
        if ys[k] < ymin:
            ymin = ys[k]
            km = k

    kos = 0
    ymax = ymin
    for k in range(0, km + 1):
        if ys[k] > ymax:
            ymax = ys[k]
            kos = k

    koe = km
    ymax = ymin
    for k in range(km, n):
        if ys[k] > ymax:
            ymax = ys[k]
            koe = k

    return ymin, km, kos, koe


def danmen_one_block(xs, ys, hh, ks, ke):
    """
    1つの連続浸水区間 ks..ke について、
    水位 hh における流積 a と潤辺 s を計算する。
    """
    n = len(xs)

    # 左側交点
    if ks == 0:
        xs_int = xs[0]
    else:
        x1, y1 = xs[ks - 1], ys[ks - 1]
        x2, y2 = xs[ks], ys[ks]
        if abs(y1 - y2) < 1.0e-12:
            xs_int = xs[ks]
        else:
            xs_int = x1 + (y1 - hh) / (y1 - y2) * (x2 - x1)

    # 右側交点
    if ke == n - 1:
        xe_int = xs[-1]
    else:
        x1, y1 = xs[ke + 1], ys[ke + 1]
        x2, y2 = xs[ke], ys[ke]
        if abs(y1 - y2) < 1.0e-12:
            xe_int = xs[ke]
        else:
            xe_int = x1 - (y1 - hh) / (y1 - y2) * (x2 - x1)

    # 左端三角形
    a = (hh - ys[ks]) * (xs[ks] - xs_int) / 2.0
    s = math.hypot(xs[ks] - xs_int, hh - ys[ks])

    # 中間台形 + 地盤縁長
    for k in range(ks, ke):
        a += ((hh - ys[k]) + (hh - ys[k + 1])) * (xs[k + 1] - xs[k]) / 2.0
        s += math.hypot(xs[k + 1] - xs[k], ys[k + 1] - ys[k])

    # 右端三角形
    a += (hh - ys[ke]) * (xe_int - xs[ke]) / 2.0
    s += math.hypot(xe_int - xs[ke], hh - ys[ke])

    return a, s


def compute_ha_hr_for_section(xs, ys, dh=0.1, max_steps=400):
    """
    1断面について A(h), R(h)=A/S を計算する。
    水位は ymin + dh, ymin + 2dh, ... と増やしていく。
    """
    ymin, km, kos, koe = find_ymin_and_levees(xs, ys)

    areas = []
    radii = []

    crest = max(ys[kos], ys[koe])
    h_stop = crest + 3.0  # 余裕高

    for ih in range(1, max_steps + 1):
        hh = ymin + ih * dh

        if hh > h_stop:
            break

        a_sum = 0.0
        s_sum = 0.0

        in_block = False
        ks = None

        for k in range(kos, koe + 1):
            if ys[k] < hh:
                if not in_block:
                    in_block = True
                    ks = k
            else:
                if in_block:
                    ke = k - 1
                    a, s = danmen_one_block(xs, ys, hh, ks, ke)
                    a_sum += a
                    s_sum += s
                    in_block = False
                    ks = None

        # 最後まで水没区間が続いた場合
        if in_block and ks is not None:
            ke = koe
            a, s = danmen_one_block(xs, ys, hh, ks, ke)
            a_sum += a
            s_sum += s

        if a_sum <= 0.0 or s_sum <= 0.0:
            break

        areas.append(a_sum)
        radii.append(a_sum / s_sum)

    return areas, radii


def write_one_series(f, vals):
    """
    Fortran想定の形式に合わせて、
    先頭に dummy=0.000 を入れて書き出す。
    1行あたり最大10個（dummy込み）程度で改行。
    """
    line_vals = ["    0.000"]
    for v in vals:
        line_vals.append(f"{v:10.3f}")
        if len(line_vals) == 10:
            f.write("".join(line_vals) + "\n")
            line_vals = []

    if line_vals:
        f.write("".join(line_vals) + "\n")


def write_ha_hr(sections, out_ha, out_hr, dh=0.1, max_steps=400):
    """
    h-a.dat, h-r.dat を出力する。

    各断面ごとに:
      i, num+1
      0.000 A1 A2 ...
      0.000 R1 R2 ...
    """
    with open(out_ha, "w") as f_a, open(out_hr, "w") as f_r:
        for i, sec in enumerate(sections, start=1):
            xs = sec["x"]
            ys = sec["y"]

            areas, radii = compute_ha_hr_for_section(xs, ys, dh=dh, max_steps=max_steps)
            num = len(areas)

            if num == 0:
                # 何も計算できない断面はスキップせず、最低限1点だけ入れる
                areas = [0.0]
                radii = [0.0]
                num = 1

            f_a.write(f"{i:3d}{num+1:10d}\n")
            f_r.write(f"{i:3d}{num+1:10d}\n")

            write_one_series(f_a, areas)
            write_one_series(f_r, radii)


def main():
    base_dir = Path(__file__).resolve().parent

    river_danmen_path = base_dir / INPUT_RIVER_DANMEN
    ha_path = base_dir / OUTPUT_HA
    hr_path = base_dir / OUTPUT_HR

    sections = read_river_danmen(river_danmen_path, isctn=None)

    print(f"Read {len(sections)} sections from {river_danmen_path}")
    if sections:
        print(f"First section points = {len(sections[0]['x'])}")
        areas, radii = compute_ha_hr_for_section(
            sections[0]["x"], sections[0]["y"],
            dh=DH, max_steps=MAX_STEPS
        )
        print(f"First section num(h levels) = {len(areas)}")

    write_ha_hr(sections, ha_path, hr_path, dh=DH, max_steps=MAX_STEPS)

    print(f"Wrote {ha_path}")
    print(f"Wrote {hr_path}")


if __name__ == "__main__":
    main()