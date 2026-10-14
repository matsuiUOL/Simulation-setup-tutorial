#!/usr/bin/env python3
from pathlib import Path

DX_CROSS = 5.0   # 横断方向点間隔 [m]

REACHES = [
    {
        "name": "main_up",
        "inds": list(range(1, 31)),
        "length_m": 1500.0,
        "z_up": -2.0,
        "z_down": -2.75,
        "width": 30.0,
        "levee_h": 4.0,
        "low_ch_w": 30.0,
    },
    {
        "name": "main_down",
        "inds": list(range(31, 62)),
        "length_m": 1500.0,
        "z_up": -2.75,
        "z_down": -3.5,
        "width": 30.0,
        "levee_h": 4.0,
        "low_ch_w": 30.0,
    },
    {
        "name": "trib",
        "inds": list(range(62, 93)),
        "length_m": 1500.0,
        "z_up": -1.75,
        "z_down": -2.75,
        "width": 20.0,
        "levee_h": 3.5,
        "low_ch_w": 20.0,
    },
]

OUT_FILE = "river_danmen_v2.dat"


def linspace_count(width, dx):
    n = int(round(width / dx))
    xs = [i * dx for i in range(n + 1)]
    if abs(xs[-1] - width) > 1e-9:
        xs.append(width)
    return xs


def bed_z_linear(j, n, z_up, z_down):
    if n <= 1:
        return z_up
    r = j / (n - 1)
    return z_up + (z_down - z_up) * r


def interp_piecewise(x, xp, yp):
    if x <= xp[0]:
        return yp[0]
    if x >= xp[-1]:
        return yp[-1]
    for i in range(len(xp) - 1):
        if xp[i] <= x <= xp[i + 1]:
            t = (x - xp[i]) / (xp[i + 1] - xp[i])
            return yp[i] + t * (yp[i + 1] - yp[i])
    return yp[-1]


def generate_cross_section(base_bed, width, levee_h, low_ch_w, dx_cross):
    xs = linspace_count(width, dx_cross)

    xc = width / 2.0
    half_low = low_ch_w / 2.0

    x0 = 0.0
    x1 = max(0.0, xc - half_low - 5.0)
    x2 = max(0.0, xc - half_low)
    x3 = xc
    x4 = min(width, xc + half_low)
    x5 = min(width, xc + half_low + 5.0)
    x6 = width

    z_top = base_bed + levee_h
    z_shoulder = base_bed + 0.55 * levee_h
    z_lowbank = base_bed + 0.20 * levee_h
    z_bottom = base_bed

    xp = [x0, x1, x2, x3, x4, x5, x6]
    yp = [z_top, z_shoulder, z_lowbank, z_bottom, z_lowbank, z_shoulder, z_top]

    ys = [interp_piecewise(x, xp, yp) for x in xs]
    return xs, ys


def build_sections():
    sections = []

    for reach in REACHES:
        inds = reach["inds"]
        n = len(inds)
        ds = reach["length_m"] / (n - 1) if n > 1 else 0.0

        for j, ind in enumerate(inds):
            s_local = j * ds
            base_bed = bed_z_linear(j, n, reach["z_up"], reach["z_down"])

            xs, ys = generate_cross_section(
                base_bed=base_bed,
                width=reach["width"],
                levee_h=reach["levee_h"],
                low_ch_w=reach["low_ch_w"],
                dx_cross=DX_CROSS,
            )

            sections.append({
                "ind": ind,
                "reach": reach["name"],
                "dd": s_local,
                "xs": xs,
                "ys": ys,
            })

    sections.sort(key=lambda d: d["ind"])
    return sections


def write_river_danmen(path: Path, sections):
    with open(path, "w", newline="\n") as f:
        f.write("Virtual river cross-sections for confluence case\n")

        for sec in sections:
            dd = sec["dd"]
            xs = sec["xs"]
            ys = sec["ys"]
            ko = len(xs)

            f.write(f"{dd:10.2f} {ko:4d}\n")
            for k, (x, y) in enumerate(zip(xs, ys), start=1):
                f.write(f"{k:4d} {x:10.3f} {y:10.3f}\n")
            f.write("\n")


def main():
    base_dir = Path(__file__).resolve().parent
    out_path = base_dir / OUT_FILE

    sections = build_sections()
    write_river_danmen(out_path, sections)

    print(f"written: {out_path}")
    print(f"number of sections = {len(sections)}")
    for reach in REACHES:
        print(
            f"{reach['name']}: inds {reach['inds'][0]}..{reach['inds'][-1]}, "
            f"width={reach['width']} m, levee_h={reach['levee_h']} m, "
            f"low_ch_w={reach['low_ch_w']} m"
        )


if __name__ == "__main__":
    main()