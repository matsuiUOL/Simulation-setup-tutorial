# remove_attr3_mesh_4lines.py

mesh_file = "mesh.dat"
inf_file  = "inf.dat"
out_file  = "mesh2.dat"

LINES_PER_MESH = 4  # ★ここが重要

# -----------------------------
# 1) inf.dat から「残すメッシュID」を取得
# -----------------------------
keep_mesh_ids = set()

with open(inf_file, "r") as f:
    for line in f:
        if not line.strip():
            continue
        mid, attr = line.split()[:2]
        if int(attr) != 3:
            keep_mesh_ids.add(int(mid))

# -----------------------------
# 2) mesh.dat を読み込み & フィルタ
# -----------------------------
with open(mesh_file, "r") as f:
    lines = f.readlines()

original_mesh_count = int(lines[0].strip())

kept_blocks = []
i = 1  # ヘッダー1行の次から

# 安全チェック：残り行数が4の倍数か（多少の空行は除外したいなら別処理）
remaining = len(lines) - 1
if remaining % LINES_PER_MESH != 0:
    raise ValueError(
        f"mesh.dat のヘッダー以降の行数が {LINES_PER_MESH} の倍数ではありません: "
        f"{remaining} lines (expected multiple of {LINES_PER_MESH})."
    )

while i < len(lines):
    block = lines[i:i+LINES_PER_MESH]

    # ブロック1行目の先頭が mesh_id という前提
    first = block[0].strip()
    if not first:
        raise ValueError(f"Unexpected empty line at mesh block start (line {i+1}).")

    mesh_id = int(first.split()[0])

    if mesh_id in keep_mesh_ids:
        kept_blocks.append(block)

    i += LINES_PER_MESH

# -----------------------------
# 3) 出力（先頭行は新しいメッシュ数に更新）
# -----------------------------
with open(out_file, "w") as f:
    f.write(f"{len(kept_blocks)}\n")
    for block in kept_blocks:
        f.writelines(block)

print("Finished.")
print(f"Original mesh count : {original_mesh_count}")
print(f"Remaining mesh count: {len(kept_blocks)}")
print(f"Output file         : {out_file}")
