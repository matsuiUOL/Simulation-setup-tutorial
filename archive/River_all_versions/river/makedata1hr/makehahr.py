#!/usr/bin/env python3
import math
from pathlib import Path


def read_river_danmen(path, isctn=None):
    """
    river_danmen.dat を読み込む。
    形式:
      1行目: ヘッダ
      各断面ブロック:
        dd ko
        nn x y  (× ko 行)
        （区切り行：空行やコメント1行）

    戻り値:
      sections = [
        {"dd": float, "x": [..], "y": [..]},
        ...
      ]
    """
    sections = []
    with open(path, "r") as f:
        # 1行目ヘッダを読み飛ばす
        header = f.readline()

        while True:
            line = f.readline()
            if not line:
                break  # EOF
            line = line.strip()
            if line == "":
                continue  # 空行ならスキップ

            # 断面先頭: dd, ko
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
                # nn, x, y
                if len(pp) < 3:
                    raise RuntimeError("Line in river_danmen.dat has fewer than 3 columns")
                x = float(pp[1])
                y = float(pp[2])
                xs.append(x)
                ys.append(y)

            # 区切り行を1行読み飛ばす（なくても OK）
            _ = f.readline()

            sections.append({"dd": dd, "x": xs, "y": ys})

            if isctn is not None and len(sections) >= isctn:
                break

    return sections


def find_ymin_and_levees(xs, ys):
    """
    Fortran と同じロジック:
      - ymin: 最低標高
      - km: そのインデックス
      - kos: 左岸堤防（km より左側で最大の y）
      - koe: 右岸堤防（km より右側で最大の y）
    """
    n = len(xs)
    # 最低標高
    ymin = 1.0e9
    km = 0
    for k in range(n):
        if ys[k] < ymin:
            ymin = ys[k]
            km = k

    # 左岸堤防
    kos = 0
    ymax = ymin
    for k in range(0, km + 1):
        if ys[k] > ymax:
            ymax = ys[k]
            kos = k

    # 右岸堤防
    koe = km
    ymax = ymin
    for k in range(km, n):
        if ys[k] > ymax:
            ymax = ys[k]
            koe = k

    return ymin, km, kos, koe


def danmen_one_block(xs, ys, hh, ks, ke):
    """
    Fortran の subroutine danmen と同じ意味。
    1つの「連続した浸水区間」に対して、
    水位 hh での部分断面積 a と濡れ縁長 s を計算する。

    xs, ys: 断面の座標配列（全点）
    ks, ke: 浸水区間の先頭・末尾インデックス（0-based, ys[k] < hh）
    """
    n = len(xs)

    # 左側の水位交点 xs_int
    if ks == 0:
        xs_int = xs[0]
    else:
        x1, y1 = xs[ks - 1], ys[ks - 1]
        x2, y2 = xs[ks], ys[ks]
        xs_int = x1 + (y1 - hh) / (y1 - y2) * (x2 - x1)

    # 右側の水位交点 xe_int
    if ke == n - 1:
        xe_int = xs[-1]
    else:
        x1, y1 = xs[ke + 1], ys[ke + 1]
        x2, y2 = xs[ke], ys[ke]
        xe_int = x1 - (y1 - hh) / (y1 - y2) * (x2 - x1)

    # まず左端の三角形
    a = (hh - ys[ks]) * (xs[ks] - xs_int) / 2.0
    s = math.hypot(xs[ks] - xs_int, hh - ys[ks])

    # 中の台形と地盤縁長
    for k in range(ks, ke):
        a += ((hh - ys[k]) + (hh - ys[k + 1])) * (xs[k + 1] - xs[k]) / 2.0
        s += math.hypot(xs[k + 1] - xs[k], ys[k + 1] - ys[k])

    # 右端の三角形
    a += (hh - ys[ke]) * (xe_int - xs[ke]) / 2.0
    s += math.hypot(xe_int - xs[ke], hh - ys[ke])

    return a, s


def compute_ha_hr_for_section(xs, ys, dh=0.1, max_steps=200):
    """
    1つの断面について、
      h = ymin + dh, ymin + 2dh, ... と水位を上げながら
      A(h), R(h)=A/S を計算する。

    levee（堤防）を越えたら計算終了。
    戻り値:
      areas: [A(h1), A(h2), ...]
      radii: [R(h1), R(h2), ...]
    """
    ymin, km, kos, koe = find_ymin_and_levees(xs, ys)

    areas = []
    radii = []

    for ih in range(1, max_steps + 1):
        hh = ymin + ih * dh

        # 堤防を越えたら終了
        if ys[kos] < hh or ys[koe] < hh:
            break

        isw = 0  # 0: above, 1: below, -1: block complete
        a_sum = 0.0
        s_sum = 0.0

        # kos..koe 間で「y < hh」になる区間を見つけて、そのたびに danmen_one_block
        ks = None
        for k in range(kos, koe + 1):
            yk = ys[k]
            if isw == 0 and yk < hh:
                # ここから浸水区間
                isw = 1
                ks = k
            elif isw == 1 and yk >= hh:
                # 浸水区間が終わった直後
                isw = -1
                ke = k - 1

            if isw == -1:
                # 1ブロックについて a, s を計算
                a, s = danmen_one_block(xs, ys, hh, ks, ke)
                a_sum += a
                s_sum += s
                isw = 0

        if a_sum <= 0.0 or s_sum <= 0.0:
            # 面積がゼロ → この水位では有効な流積なし
            break

        areas.append(a_sum)
        radii.append(a_sum / s_sum)

    return areas, radii


def write_ha_hr(sections, out_ha, out_hr, dh=0.1, max_steps=200):
    """
    h-a.dat, h-r.dat を Fortran の期待フォーマットで出力する。
    各断面ごとに:

      i, num+1
      0.000 A(h1) A(h2) ...
      0.000 R(h1) R(h2) ...

    という感じで、0.0 を最初に1つ入れて「num+1」個にする。
    """
    with open(out_ha, "w") as f_a, open(out_hr, "w") as f_r:
        for i, sec in enumerate(sections, start=1):
            xs = sec["x"]
            ys = sec["y"]

            areas, radii = compute_ha_hr_for_section(xs, ys, dh=dh, max_steps=max_steps)
            num = len(areas)
            if num == 0:
                # 何も書かない or ゼロで埋めるなど、好きに処理
                continue

            # ヘッダ行: 断面番号, num+1
            f_a.write(f"{i:3d}{num+1:10d}\n")
            f_r.write(f"{i:3d}{num+1:10d}\n")

            # データ行: dummy(=0.0) + num 個分
            def write_values(f, vals):
                # 10 個ごとに改行
                line_vals = ["    0.000"]  # dummy
                for v in vals:
                    line_vals.append(f"{v:10.3f}")
                    if len(line_vals) == 10:
                        f.write("".join(line_vals) + "\n")
                        line_vals = []
                if line_vals:
                    f.write("".join(line_vals) + "\n")

            write_values(f_a, areas)
            write_values(f_r, radii)


def main():
    base_dir = Path(__file__).resolve().parent
    river_danmen_path = base_dir / "river_danmen.dat"
    ha_path = base_dir / "h-a.dat"
    hr_path = base_dir / "h-r.dat"

    # 断面数を決め打ちしたければ isctn=82 を渡す
    sections = read_river_danmen(river_danmen_path, isctn=None)

    print(f"Read {len(sections)} sections from {river_danmen_path}")

    write_ha_hr(sections, ha_path, hr_path, dh=0.1, max_steps=200)

    print(f"Wrote {ha_path} and {hr_path}")


if __name__ == "__main__":
    main()
