import numpy as np
import rasterio
from rasterio.transform import from_origin

nx = ny = 400
dx = dy = 5.0  # 5m 格子
X, Y = np.meshgrid(np.arange(nx), np.arange(ny))

# 基本勾配（南→北へ0.5%）
dem = 0.005 * Y

# 中央に緩い谷：小河川が通る
valley = 1.5 * np.exp(-((X - nx/2)/80)**2)
dem -= valley

# 微地形
dem += 0.3 * (np.sin(X/20) * np.sin(Y/25))

transform = from_origin(0, ny*dy, dx, dy)

with rasterio.open(
    "artificial_dem.tif", "w",
    driver="GTiff", height=ny, width=nx,
    count=1, dtype="float32", transform=transform
) as dst:
    dst.write(dem.astype("float32"), 1)
