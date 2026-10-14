# filter_inf_remove_3.py

inf_file = "inf0125_v2.dat"
out_file = "inf0125_v2_re.dat"

with open(inf_file, "r") as f, open(out_file, "w") as g:
    for line in f:
        if not line.strip():
            continue
        mid, inf = line.split()[:2]
        if int(inf) != 3:
            g.write(line)

print("Finished.")
print(f"Output file: {out_file}")
