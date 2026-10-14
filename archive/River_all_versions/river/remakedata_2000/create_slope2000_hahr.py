#!/usr/bin/env python3
import math
from pathlib import Path

TOTAL_LENGTH = 3000.0
N_MAIN_SECTIONS = 60   # section 1..60 along 3000 m
N_SECTIONS = 61        # section 61 duplicates downstream boundary
WIDTH = 30.0
DX_CROSS = 5.0
N_POINTS = int(WIDTH / DX_CROSS) + 1
Z_UPSTREAM = -3.0
BED_SLOPE = 1.0 / 2000.0
Z_DOWNSTREAM = Z_UPSTREAM - BED_SLOPE * TOTAL_LENGTH  # -4.5
DH = 0.1
MAX_STEPS = 200


def bed_elevation(i):
    """section i: 1..61. section 60/61 have the downstream bed elevation."""
    if i <= N_MAIN_SECTIONS:
        s = (i - 1) * TOTAL_LENGTH / (N_MAIN_SECTIONS - 1)
        return Z_UPSTREAM - BED_SLOPE * s, s
    else:
        return Z_DOWNSTREAM, TOTAL_LENGTH


def generate_cross_section(base_bed):
    xs = [k * DX_CROSS for k in range(N_POINTS)]
    levee_height = 4.0
    ys = [
        base_bed + levee_height,
        base_bed + 0.5 * levee_height,
        base_bed + 0.3 * levee_height,
        base_bed,
        base_bed + 0.3 * levee_height,
        base_bed + 0.5 * levee_height,
        base_bed + levee_height,
    ]
    return xs, ys


def write_river_danmen(path):
    with open(path, 'w') as f:
        f.write('Virtual river cross-sections, bed slope 1/2000, upstream bed fixed at -3.0 m\n')
        for i in range(1, N_SECTIONS + 1):
            zb, s = bed_elevation(i)
            xs, ys = generate_cross_section(zb)
            f.write(f'{s:10.2f} {len(xs):4d}\n')
            for k, (x, y) in enumerate(zip(xs, ys), start=1):
                f.write(f'{k:4d} {x:10.3f} {y:10.3f}\n')
            f.write('\n')


def find_ymin_and_levees(xs, ys):
    ymin = min(ys)
    km = ys.index(ymin)
    kos = max(range(0, km + 1), key=lambda k: ys[k])
    koe = max(range(km, len(ys)), key=lambda k: ys[k])
    return ymin, km, kos, koe


def danmen_one_block(xs, ys, hh, ks, ke):
    n = len(xs)
    if ks == 0:
        xs_int = xs[0]
    else:
        x1, y1 = xs[ks - 1], ys[ks - 1]
        x2, y2 = xs[ks], ys[ks]
        xs_int = x1 + (y1 - hh) / (y1 - y2) * (x2 - x1)

    if ke == n - 1:
        xe_int = xs[-1]
    else:
        x1, y1 = xs[ke + 1], ys[ke + 1]
        x2, y2 = xs[ke], ys[ke]
        xe_int = x1 - (y1 - hh) / (y1 - y2) * (x2 - x1)

    a = (hh - ys[ks]) * (xs[ks] - xs_int) / 2.0
    s = math.hypot(xs[ks] - xs_int, hh - ys[ks])
    for k in range(ks, ke):
        a += ((hh - ys[k]) + (hh - ys[k + 1])) * (xs[k + 1] - xs[k]) / 2.0
        s += math.hypot(xs[k + 1] - xs[k], ys[k + 1] - ys[k])
    a += (hh - ys[ke]) * (xe_int - xs[ke]) / 2.0
    s += math.hypot(xe_int - xs[ke], hh - ys[ke])
    return a, s


def compute_ha_hr_for_section(xs, ys, dh=DH, max_steps=MAX_STEPS):
    ymin, km, kos, koe = find_ymin_and_levees(xs, ys)
    crest = max(ys[kos], ys[koe])
    h_stop = crest + 3.0
    areas, radii = [], []
    for ih in range(1, max_steps + 1):
        hh = ymin + ih * dh
        if hh > h_stop + 1.0e-12:
            break
        a_sum = 0.0
        s_sum = 0.0
        isw = 0
        ks = None
        for k in range(kos, koe + 1):
            if isw == 0 and ys[k] < hh:
                isw = 1
                ks = k
            elif isw == 1 and ys[k] >= hh:
                ke = k - 1
                a, s = danmen_one_block(xs, ys, hh, ks, ke)
                a_sum += a
                s_sum += s
                isw = 0
                ks = None
        if isw == 1 and ks is not None:
            ke = koe
            a, s = danmen_one_block(xs, ys, hh, ks, ke)
            a_sum += a
            s_sum += s
        if a_sum <= 0.0 or s_sum <= 0.0:
            break
        areas.append(a_sum)
        radii.append(a_sum / s_sum)
    return areas, radii


def write_values(f, vals):
    line_vals = ['    0.000']
    for v in vals:
        line_vals.append(f'{v:10.3f}')
        if len(line_vals) == 10:
            f.write(''.join(line_vals) + '\n')
            line_vals = []
    if line_vals:
        f.write(''.join(line_vals) + '\n')


def write_ha_hr(out_ha, out_hr):
    with open(out_ha, 'w') as fa, open(out_hr, 'w') as fr:
        for i in range(1, N_SECTIONS + 1):
            zb, _ = bed_elevation(i)
            xs, ys = generate_cross_section(zb)
            areas, radii = compute_ha_hr_for_section(xs, ys)
            n = len(areas)
            fa.write(f'{i:3d}{n+1:10d}\n')
            fr.write(f'{i:3d}{n+1:10d}\n')
            write_values(fa, areas)
            write_values(fr, radii)


def main():
    base = Path('/mnt/data')
    river = base / 'river_danmen_v2_slope2000.dat'
    ha = base / 'h-a_v2_slope2000.dat'
    hr = base / 'h-r_v2_slope2000.dat'
    write_river_danmen(river)
    write_ha_hr(ha, hr)
    print('Wrote', river)
    print('Wrote', ha)
    print('Wrote', hr)
    print('Z_UPSTREAM', Z_UPSTREAM, 'Z_DOWNSTREAM', Z_DOWNSTREAM, 'N_SECTIONS', N_SECTIONS)

if __name__ == '__main__':
    main()
