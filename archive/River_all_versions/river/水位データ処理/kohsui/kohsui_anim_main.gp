# gnuplotの設定

reset
set grid                # 格子を表示させる
set ytics nomirror      # y軸のメモリを左側のみ表示する



# x軸に断面番号をとる

set xr[54:92]
set xl "Sec No."



# y軸に東京湾基準の高さをとる

set yr[-5:10]
set ylabel "T.P."



# 出力をgifアニメに設定する

set term gif animate
set output "kohsui_suii_anim.gif"



# 変数を設定する
# n0 : ループ変数の初期値
# n1 : ループ変数の最大値
# dn : ループ変数の増加間隔
# 今回は suii100.dat ～ suii677.dat まであるので、

n0 = 100
n1 = 677
dn = 1

# と設定すればOK


# ループ処理の開始

load "kohsui_anim_sub.plt"
