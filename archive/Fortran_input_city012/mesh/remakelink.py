# remove_links_between_inf3_meshes.py

inf_file  = "inf0125_v2.dat"
link_file = "link0125_v2.dat"
out_file  = "link0125_v2_re.dat"

LINES_PER_LINK = 3

# -----------------------------
# 1) inf=3 のメッシュID集合を作る
# -----------------------------
inf3_mesh_ids = set()

with open(inf_file, "r") as f:
    for line in f:
        if not line.strip():
            continue
        mid, inf = line.split()[:2]
        if int(inf) == 3:
            inf3_mesh_ids.add(int(mid))

# -----------------------------
# 2) link.dat を読み込んで、両側meshがinf=3のリンクだけ除外
# -----------------------------
with open(link_file, "r") as f:
    lines = f.readlines()

# 先頭ヘッダー
header = lines[0].rstrip("\n")
data_lines = lines[1:]

# 安全チェック（ヘッダー以降が3の倍数か）
if len(data_lines) % LINES_PER_LINK != 0:
    raise ValueError(
        f"link.dat のヘッダー以降の行数が {LINES_PER_LINK} の倍数ではありません: "
        f"{len(data_lines)} lines"
    )

kept_blocks = []
removed_count = 0

i = 0
while i < len(data_lines):
    block = data_lines[i:i+LINES_PER_LINK]

    # ブロック1行目： link_id mesh1 mesh2 node1 node2
    first = block[0].strip()
    if not first:
        raise ValueError(f"Unexpected empty line at link block start (data line index {i}).")

    parts = first.split()
    if len(parts) < 5:
        raise ValueError(f"Link header line seems malformed: '{block[0].rstrip()}'")

    mesh1 = int(parts[1])
    mesh2 = int(parts[2])

    # 両方がinf=3のときだけ除外
    if (mesh1 in inf3_mesh_ids) and (mesh2 in inf3_mesh_ids):
        removed_count += 1
    else:
        kept_blocks.append(block)

    i += LINES_PER_LINK

# -----------------------------
# 3) 出力：ヘッダー(リンク数)を書き換えて保存
# -----------------------------
new_link_count = len(kept_blocks)

with open(out_file, "w") as f:
    f.write(f"{new_link_count}\n")
    for block in kept_blocks:
        f.writelines(block)

print("Finished.")
print(f"Original links : {int(header.split()[0]) if header.split() else 'unknown'}")
print(f"Removed links  : {removed_count}")
print(f"Remaining links: {new_link_count}")
print(f"Output file    : {out_file}")
