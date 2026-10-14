set -e

# ===== コンパイル =====
ifx mesh_attribution.f90 -o mesh_attri.out
ifx pred.f90 -o pre.out
ifx bsmake_corrected.f90 -o bs.out

# ===== 実行 =====
echo "Running mesh_attri..."
./mesh_attri.out

echo "Running pre..."
./pre.out

echo "Running bs..."
./bs.out

echo "Done."
