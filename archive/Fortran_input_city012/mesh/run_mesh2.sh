#!/bin/bash
set -e  # エラーが出たら即停止する

echo "Running mesh_attri..."
./mesh_attri.out

echo "Running pre..."
./pre.out

echo "Running bs..."
./bs.out

echo "Done."
