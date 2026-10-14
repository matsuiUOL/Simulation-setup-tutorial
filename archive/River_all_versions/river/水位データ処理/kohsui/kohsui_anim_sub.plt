# ループ処理
# ループ変数の初期化

if(exist("n")==0 || n<0) n = n0



# タイトルをつける
time = (n-100) * 300
title(n) = sprintf("t = %d", time)
unset label
set label title(n) at 73, 8


# プロットする

filename = sprintf("suii%03d.dat", n)
plot filename using 1:2 w l lw 2 title "kasyo",\
filename using 1:4 w l lw 2 title "suii"



# ループ処理

n = n + dn          # ループ変数の増加
if( n < n1) reread  # 最大値より小さいならループ
undefine n          # ループ変数の削除

