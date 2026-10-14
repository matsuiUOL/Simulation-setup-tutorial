# 08 解析モデルへの入力一式

05〜07 で作ったファイルを、Fortran 氾濫解析モデルが読む名前で 1 か所に集めたものです（city4）。
解析を実行するときは、この中身を解析本体の入力フォルダにコピーします。

## 中身と作成元

```
08_fortran_input/city4/
├── mesh/
│   ├── mesh.dat              ← 05 pred.f90
│   ├── link.dat              ← 05 pred.f90
│   ├── node.dat              ← 05 mesh_attribution.f90
│   ├── inf.dat               ← 05 mesh_attribution.f90（土地利用属性）
│   └── bs_op_corrected.dat   ← 05 bsmake_corrected.f90（地盤高）
├── sewer/
│   ├── manhole_bshosei.dat   ← 06 makemanhole.py
│   └── conduit_bshosei.dat   ← 06 makeconduit.py
├── river/
│   ├── kasho.dat             ← 07 kasho_v2.dat をリネーム
│   ├── h-a.dat               ← 07 h-a_v2.dat をリネーム
│   ├── h-r.dat               ← 07 h-r_v2.dat をリネーム
│   ├── hydr.dat              ← 07 hydr_v2.dat をリネーム
│   ├── shoki.dat             ← 07 shoki_v2.dat をリネーム
│   ├── riv_to_2d.dat         ← 07 riv_to_2d_v2.dat をリネーム
│   ├── sw_riv.dat            ← 07 makesw_riv.py
│   └── sw_riv_gr.dat         ← 07 makesw_riv_gr.py
└── external/                 ← 外力条件（元の Fortran_input/external をそのままコピー）
    ├── rain_R125.dat, rain_R150.dat   ← 降雨
    └── Q1〜Q4.dat, Q*H*.dat           ← 流量・水位条件
```

## 集め直すときのコマンド例

```bash
cd 08_fortran_input/city4
cp ../../05_mesh_preprocess/city4/{mesh,link,node,inf,bs_op_corrected}.dat mesh/
cp ../../06_sewer/city4/{manhole_bshosei,conduit_bshosei}.dat sewer/
R=../../07_river/city4
cp $R/kasho_v2.dat river/kasho.dat
cp $R/h-a_v2.dat river/h-a.dat
cp $R/h-r_v2.dat river/h-r.dat
cp $R/hydr_v2.dat river/hydr.dat
cp $R/shoki_v2.dat river/shoki.dat
cp $R/riv_to_2d_v2.dat river/riv_to_2d.dat
cp $R/sw_riv.dat $R/sw_riv_gr.dat river/
```

## ⚠ 要確認
- リネーム後の名前は、元の `Fortran_input/river/`（city012 版）に合わせています。**解析本体の open 文・設定ファイル** のファイル名と一致しているか確認してください。
- `external/` の各ファイル（`Q1H1.dat` など）の使い分けは記録がありません。
- city012 の入力一式は `archive/Fortran_input_city012/` にあります。
