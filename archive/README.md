# archive（旧バージョン・試行錯誤の記録）

チュートリアル本体（01〜08）を整理する前の、元フォルダの内容をほぼそのまま保存しています。
**通常は見る必要はありません。** 過去の設定を確認したいときの参考用です。

| フォルダ | 元の場所 | 内容 |
|---|---|---|
| `Scripts_all_versions/` | `Scripts/` | city012・city4 の全バージョンの都市生成スクリプトと出力 |
| `Fortran_input_city012/` | `Fortran_input/` | city012 のメッシュ前処理（日付・版違いの出力多数）、下水道、河川、外力 |
| `River_all_versions/` | `River/` | 河川データ作成の全版（`makedata1hr`, `makedata6hr`, `makedata_city4`, `remakedata_2000`）、1 次元河道モデル `river.f90`、断面補正プログラム、水位アニメーション作成 |
| `GiD_old_projects/` | `GiD/` | GiD プロジェクト（`.gid`）と書き出した `.msh` の旧版 |
| `reference_inputs/` | `reference/input`, `reference/readfile` | 実河川（過去研究）の入力ファイル例。書式の参考 |

## コピー時に除外したもの
- 実行ファイル・中間生成物（`*.exe`, `*.obj`, `*.mod`, `*.out`, `a.out`）
- 地盤高内挿の確認ファイル（`check*.dat`）
- 5 MB を超えるファイル（DEM テキストや `link.dat` などの重複）→ 元の `tutorial` フォルダには残っています
