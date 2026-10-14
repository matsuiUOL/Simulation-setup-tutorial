#!/usr/bin/env python3
from pathlib import Path
from collections import defaultdict, Counter

BASE = Path(".")

CONDUIT = BASE / "conduit_bshosei.dat"
MH2RIV  = BASE / "mh_to_riv.dat"   # mh_id  riv_no  の2列（空白区切り）
OUT     = BASE / "sw_riv.dat"

def read_mh_to_riv(path: Path):
    """
    mh_to_riv.dat:
      mh_id  riv_no
    """
    mh2riv = {}
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split()
            if len(parts) < 2:
                continue
            mh = int(parts[0])
            riv = int(parts[1])
            mh2riv[mh] = riv
    return mh2riv

def parse_conduit(path: Path):
    """
    conduit_bshosei.dat:
      1行目: 本数
      2行目: ヘッダ
      以降: データ
    必要なのは
      branch_id, idd1, mhup, mhdw
    """
    pipes = []
    with path.open("r", encoding="utf-8") as f:
        first = f.readline()
        if not first:
            return pipes
        _n = int(first.strip())
        _hdr = f.readline()  # header

        for line in f:
            line = line.strip()
            if not line:
                continue

            parts = line.split()
            # 想定カラム:
            # 0:branch_id 1:inf 2:ngrp 3:shp 4:idd1 5:idd2 6:rn 7:slp
            # 8:bsup 9:bsdw 10:mhup 11:mhdw 12:ipt ...
            if len(parts) < 12:
                continue

            try:
                branch_id = int(parts[0])
                idd1 = float(parts[4])
                mhup = int(parts[10])
                mhdw = int(parts[11])
            except ValueError:
                continue

            pipes.append({
                "branch_id": branch_id,
                "idd1": idd1,
                "mhup": mhup,
                "mhdw": mhdw,
            })
    return pipes

def build_mh_candidates(pipes, mh_set):
    """
    mh_id -> list of candidate pipes (branch_id, idd1)
    """
    cand = defaultdict(list)
    for p in pipes:
        bid = p["branch_id"]
        idd1 = p["idd1"]
        if p["mhup"] in mh_set:
            cand[p["mhup"]].append((bid, idd1))
        if p["mhdw"] in mh_set:
            cand[p["mhdw"]].append((bid, idd1))
    return cand

def choose_representatives(mh2riv, mh_candidates):
    """
    1) 各mhで idd1 最大の候補集合を作る
    2) idd1 最大が複数のとき
       - 「他mhの最大候補にも出てくる branch_id を避ける」
         (= なるべく専属っぽい pipe を選ぶ)
    3) それでも同点なら branch_id 最小
    """
    # mhごとの「idd1最大候補リスト」
    mh_top = {}
    for mh, lst in mh_candidates.items():
        if not lst:
            continue
        max_idd1 = max(idd1 for _, idd1 in lst)
        top = [(bid, idd1) for bid, idd1 in lst if idd1 == max_idd1]
        mh_top[mh] = top

    # 「他mhの最大候補にも登場する branch_id」を数える
    appear = Counter()
    for mh, top in mh_top.items():
        for bid, _ in top:
            appear[bid] += 1

    reps = {}
    for mh, top in mh_top.items():
        # まず「appearが小さい(=他mhと競合しない)」を優先
        # 次に branch_id 最小で安定化
        top_sorted = sorted(top, key=lambda x: (appear[x[0]], x[0]))
        reps[mh] = top_sorted[0][0]  # branch_id
    return reps

def write_sw_riv(out_path: Path, mh2riv, reps):
    """
    sw_riv.dat:
      n_conn
      sw_i  mh_id  riv_no
      ...
    """
    rows = []
    for mh, riv in mh2riv.items():
        if mh not in reps:
            # 候補pipeが無いマンホールはスキップ
            continue
        sw_i = reps[mh]
        rows.append((sw_i, mh, riv))

    # 出力を安定化（mh順）
    rows.sort(key=lambda x: x[1])

    with out_path.open("w", encoding="utf-8") as f:
        f.write(f"{len(rows)}\n")
        for sw_i, mh, riv in rows:
            f.write(f"{sw_i} {mh} {riv}\n")

    print(f"wrote {out_path}  (n_conn={len(rows)})")

def main():
    mh2riv = read_mh_to_riv(MH2RIV)
    mh_set = set(mh2riv.keys())

    pipes = parse_conduit(CONDUIT)
    mh_candidates = build_mh_candidates(pipes, mh_set)

    reps = choose_representatives(mh2riv, mh_candidates)

    write_sw_riv(OUT, mh2riv, reps)

if __name__ == "__main__":
    main()
