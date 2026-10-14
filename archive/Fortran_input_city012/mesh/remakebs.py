# filter_bs_op_by_inf.py

inf_file = "inf0125_v2.dat"
bs_file  = "bs_op_corrected0125.dat"
out_file = "bs_op_corrected0125_re.dat"

# -----------------------------
# 1) inf != 3 の mesh_id を取得
# -----------------------------
keep_mesh_ids = set()

with open(inf_file, "r") as f:
    for line in f:
        if not line.strip():
            continue
        mid, inf = line.split()[:2]
        if int(inf) != 3:
            keep_mesh_ids.add(int(mid))

# -----------------------------
# 2) bs_op_corrected2.dat をフィルタ
# -----------------------------
with open(bs_file, "r") as f, open(out_file, "w") as g:
    for line in f:
        if not line.strip():
            continue
        mid = int(line.split()[0])
        if mid in keep_mesh_ids:
            g.write(line)

print("Finished.")
print(f"Output file: {out_file}")
