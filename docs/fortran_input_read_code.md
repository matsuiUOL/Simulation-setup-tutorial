# Fortran本体：入力ファイル読み込み部（抜粋）

元ファイル: `others/` 内のメモを整形したもの。Fortran本体がどの書式で各入力ファイルを読むかの参考。

## 5 drat_riv 

```fortran
       read(111, 1116) msctn
       read(111, *)
       do i = 1, msctn
         read(111, 1117) iptn(i), hb_riv(i), teibol(i), teibor(i), rn_riv(i), dx2_riv(i), grad_riv(i)
       1116 format(i5)
       1117 format(15x, i5, 4f11.3, f11.1, f10.1)
       close(111)
     !==============================
     !   h-a, h-r（河川の断面形状）
     !==============================
       do i = 1, msctn
         read(112, 1126) ihnum(i)
         read(112, 1127) (ha_riv(i, ii), ii = 1, ihnum(i))
         read(113, 1126) ihnum(i)
         read(113, 1127) (hr_riv(i, ii), ii = 1, ihnum(i))
       enddo
       1126 format(8x, i5)
       1127 format(10f10.3)
       close(112)
       close(113)
     !==============================
     !   knode_riv (河川ノードを形成している断面番号)
     !==============================
       read(114, 1146) knode_riv, knode1_riv, knode2_riv
       read(114, *)
       do inodek = 1, knode_riv
         read(114, 1147) mnd(inodek), (nd_riv(inodek, j), j = 1, mnd(inodek))
       enddo
       1146 format(3i5)
       1147 format(5x, i3, 10i5)
       close(114)
       read(115, *)
       read(115, *)
       read(115, 1156) iup, iqmax_riv
       do i = 1, iup
         read(115, *)
         do j = 1, iqmax_riv
           read(115, 1158) qhyd_riv(i, j)
         enddo
       enddo
     !==============================
     !   downstream boundary water level 下流端の水位データ
     !==============================
       read(115, *)
       read(115, *)
       read(115, 1156) idw, ihmax_riv
       do i = 1, idw
         read(115, *)
         do j = 1, ihmax_riv
           read(115, 1157) hhyd_riv(i, j)
         enddo
       enddo
       1156 format(2i5)
       1157 format(15x, f10.2)
       1158 format(15x, f14.6)
       close(115)
     !==============================
     !   connection river and flood plain 河川と氾濫原の接続データ
     !==============================
       do i = 1, msctn
         read(117, *)
         ! j = 1 は左岸側、 j = 2 は右岸側データ
         do j = 1, 2
           read(117, 1701) nm_rivtoli(i, j)
           ac_dl_rtl(i, j) = 0.0d0
           if(nm_rivtoli(i, j) == 0) cycle
           do k = 1, nm_rivtoli(i, j)
             read(117, 1702) rivtome(i, j, k), rivtoli(i, j, k), ux_rtm, uy_rtm
             ux(rivtoli(i, j, k)) = ux_rtm
             uy(rivtoli(i, j, k)) = uy_rtm
             dx = dnox(linode(rivtoli(i, j, k), 1)) - dnox(linode(rivtoli(i, j, k), 2))
             dy = dnoy(linode(rivtoli(i, j, k), 1)) - dnoy(linode(rivtoli(i, j, k), 2))
             dl_rtl(i, j, k) = sqrt(dx**2 + dy**2)
             ac_dl_rtl(i, j) = ac_dl_rtl(i, j) + dl_rtl(i, j, k)
             rbeta(rivtoli(i, j, k)) = 1.0d0
           enddo
         enddo
         read(117, *)
       enddo
       1701 format(8x, i3)
       1702 format(2i8, 2f12.6)
       close(117)
       return
     !==============================
     !   read flap gate フラップゲートのデータ読み込み
     !==============================
     ! ※inf2_node の調整をする必要があるため、rdat2よりも先にフラップゲートのデータ読み込みが必要
       entry rdat_flap
       aa = 5.0d0
       read(118, *) num_flap
       read(118, *)
       do i = 1, num_flap
         read(118, 1186) fltoriv(i), fltogai(i), bs_flp(i), w_flp(i), tate_flp(i), dst_flp(i)
         ! fltoriv : そのフラップゲートの排水先の河川断面番号
         ! fltogai : そのフラップゲートが接続している街渠ますの番号
         ! bs_flp  : そのフラップゲートの下端の標高値(水位がこの値に到達するとゲートが閉まる)
         ! w_flp   : フラップゲートの幅
         ! tate_flp: フラップゲートの高さ
         ! dst_flp : フラップゲートの位置と街渠ますの位置の水平距離
         !
         ! フラップゲートにつながる接続管の幅は、ゲートの幅-0.1m
         ! 接続管の高さは、ゲートの高さ-0.1m とする
         w_flp(i) = w_flp(i) - 0.1d0
         tate_flp(i) = tate_flp(i) - 0.1d0
         bsl_flp(i) = gg*(tate_flp(i) * w_flp(i))/aa**2
       enddo
       1186 format(5x, i5, i10, 4f10.3)
       close(118)
    end subroutine rdat_riv
```


## 7 riv_initial

```fortran
!=== RIVER INITIAL CONDITIONS ==== !松井が追加
 subroutine riv_initial
 use globals_conditions
 use globals_meshdata
 use globals_river
 implicit none
 integer i,j
 !==============================
 !   初期水位・流量
 !==============================
   do i = 1, msctn
     read(116, 1166) hs_riv(i), qs_riv(i), qys_riv(i)
   enddo
   1166 format(4x, 3f14.8)
   close(116)
```


## 9 connect_4

```fortran
 read(000, *, iostat=ios) n_conn
 if (ios /= 0 .or. n_conn <= 0) return
 allocate(sw_i(n_conn), sw_j(n_conn), riv_no(n_conn))
 do k = 1, n_conn
   read(10, *, iostat=ios) sw_i(k), sw_j(k), riv_no(k)
   if (ios /= 0) then
     n_conn = k-1
     exit
   end if
 end do
```
