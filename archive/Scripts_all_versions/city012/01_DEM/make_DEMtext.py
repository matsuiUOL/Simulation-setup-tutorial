#!/usr/bin/env python3
import numpy as np
from pathlib import Path


def generate_dem_array(nx: int, ny: int):
    """
    いままでの make_dem と同じロジックで、
    numpy 配列 dem[ny, nx] を生成するだけの関数。
    """
    # 格子インデックス
    x = np.arange(nx)
    y = np.arange(ny)
    X, Y = np.meshgrid(x, y)

    # 緩い勾配（北が高く南が低い：Yが大きいほど値が小さくなる）
    dem = 0.004 * (ny - Y)

    # 中央付近に谷
    valley = 1.5 * np.exp(-((X - nx/2) / 100.0)**2)
    dem -= valley

    # 微地形を入れたければここでONにする
    # dem += 0.3 * (np.sin(X/25.0) * np.sin(Y/30.0))

    return dem.astype("float32")


def write_dem_as_xyz_txt(
    txt_path: Path,
    dem: np.ndarray,
    origin_x: float,
    origin_y: float,
    dx: float,
    dy: float,
):
    """
    dem 配列を (x y z) 形式のテキストに書き出す。
    x, y はセル中心座標。
    """
    ny, nx = dem.shape

    with open(txt_path, "w") as f:
        for row in range(ny):      # 0 = 北側
            for col in range(nx):  # 0 = 西側
                # セル中心座標
                x = origin_x + (col + 0.5) * dx
                y = origin_y - (row + 0.5) * dy  # 下へ行くほど y が減る

                z = dem[row, col]
                # x y z を空白区切りで
                f.write(f"{x:.3f} {y:.3f} {z:.3f}\n")


def main():
    # パラメータ（今までの make_dem と同じ）
    dx = 5.0
    dy = 5.0
    nx = 600   # 600 * 5m = 3000 m
    ny = 600

    origin_x = 152000.0  # 左上 x（西端）
    origin_y = 505000.0  # 左上 y（北端）

    # 出力ファイルパス
    base_dir = Path(__file__).resolve().parent
    out_dir = base_dir / "DEM_text"
    out_dir.mkdir(parents=True, exist_ok=True)
    txt_path = out_dir / "out5m.txt"

    # DEM 配列生成
    dem = generate_dem_array(nx, ny)

    # テキストとして書き出し
    write_dem_as_xyz_txt(
        txt_path=txt_path,
        dem=dem,
        origin_x=origin_x,
        origin_y=origin_y,
        dx=dx,
        dy=dy,
    )

    print(f"DEM text (x y z) written to: {txt_path}")


if __name__ == "__main__":
    main()
