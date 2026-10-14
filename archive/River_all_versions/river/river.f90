!     ##########################################################
!     ##                                                      ##
!     ##       流域モデル  氾濫解析プログラム(本明川)         ##
!     ##                                                      ##
!     ##       2002.01                   by k.kawaike         ##
!     ##                                                      ##
!     ##########################################################
!
!
!     %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
!
!      cslmd          : λcosθ
!      hn,hs          : 各断面での新旧の水位
!      qn,qs          : 各断面での新旧の流量
!      us             : 流速
!      as             : 断面積
!      b              : 水面での川幅
!      htes           : 全水頭
!      fs             : エネルギー勾配
!      qys            : 横流入流量(単位幅)
!
!      msctn          : 全断面数
!      iptn           : 各断面のタイプ
!                       （-1:上流端, 1:下流端, 0:それ以外）
!
!      hb             : 河床高
!      rn             : 粗度係数
!
!      knode          : ノード総数
!      knode1         : 内部ノード数
!      knode2         : 境界ノード数
!      mnd            : ノードのもつ断面数
!      nd             : ノードのもつ断面no.
!
!      ha             : 水深と断面積の関係（10cm刻み）
!      hr             : 水深と径深の関係（10cm刻み）
!
!      kchk           : 画面表示step間隔
!      kout           : ファイル書き込みstep間隔
!
!     %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
!
module globals
      integer, parameter :: irv = 500, irv2 = 250
      real(8) gg, dt, dt2, time, dtrain, alpha, beta, cslmd, th
      real(8) hn(irv), qn(irv), hs(irv), qs(irv), us(irv), as(irv), bs(irv), htes(irv), fs(irv), cap(irv), cbm(irv), qys(irv), sap(irv), sbm(irv)
      real(8) qhyd(6, 2000), hhyd(6, 2000)
      real(8) hb(irv), rn(irv), dx2(irv), teibol(irv), teibor(irv)
      real(8) ha(irv, irv2), hr(irv, irv2)
      integer msctn, iptn(irv), ihnum(irv)
      integer knode, knode1, knode2, mnd(40), nd(40, 8)
      integer mesh, link, node, mstep
end module globals
!
!
!
!     #######################################################
!     ##                                                   ##
!     ##                   sub programs                    ##
!     ##                                                   ##
!     #######################################################
!
module subprogs
  use globals
  implicit none
contains
!
!     =======================================================
!                     デ－タの読み込み
!     =======================================================
      subroutine rdat
      real(8) dist, dst, den
      integer no, me, li, k, i, j, ii, ksw, jst, jen, inodek
      integer n, nn, nst, nen
!     ===========================
!       河道断面 
!          msctn：全断面数,
!          iptn ：断面のタイプ,
!          hb   ：河床高,
!          rn   ：粗度係数,
!          dx2  ：Δx
!     ===========================
       read(10, 1101) msctn
       read(10, *)
      do j = 1, msctn
       read(10, 1102) iptn(j), hb(j), teibol(j), teibor(j), rn(j), dx2(j)
      enddo
 1101 format(i5)
 1102 format(15x, i5, 4f11.3, f11.1)
      close(10)
!     ===========================
!              h-a, h-r
!     ===========================
      do j = 1, msctn
       read(11, 1110) ihnum(j)
       read(11, 1111) (ha(j, ii), ii = 1, ihnum(j))
       read(12, 1110) ihnum(j)
       read(12, 1111) (hr(j, ii), ii = 1, ihnum(j))
      enddo
 1110 format(3x, i10)
 1111 format(10f10.3)
      close(11)
      close(12)
!     ================================
!     河川ノードを形成している断面番号
!          knode  ：ノード数
!          knode1 ：内部ノード数
!          knode2 ：外部ノード数
!     ================================
       read(13, 1131) knode, knode1, knode2
       read(13, *)
      do inodek = 1, knode
       read(13, 1132) mnd(inodek), (nd(inodek, j), j = 1, mnd(inodek))
      enddo
 1131 format(3i5)
 1132 format(5x, i3, 10i5)
      close(13)
!
      end subroutine rdat
!
!     *********************************************************
!           上流端･下流端境界条件（ハイドログラフ） read
!     *********************************************************
      subroutine bndry(iqmax, ihmax)
      real(8) b0
      integer i, j, iup, iqmax, idw, ihmax
!     =========================================================
!           qhyd ：上流端流入流量
!     =========================================================
      read(14, 1141) iup, iqmax
      do i = 1, iup
       read(14, *)
      do j = 1, iqmax
       read(14, 1142) qhyd(i, j)
      enddo
      enddo
!     =========================================================
!           hhyd ：下流端水位
!     =========================================================
       read(14, 1141) idw, ihmax
      do i = 1, idw
       read(14, *)
      do j = 1, ihmax
       read(14, 1143) hhyd(i, j)
      enddo
      enddo
 1141 format(//2i5)
 1142 format( 9x, f20.6)
 1143 format(15x, f10.2)
      close(14)
!
      end subroutine bndry
!
!     *********************************************************
!                      ハイドログラフの内挿
!     *********************************************************
      subroutine hydro
      real(8) dtp, qqq, hhh
      integer iqhy, ihhy, iqmax, ihmax, it2
!     =========================================================
!                    流量ハイドログラフの内挿
!     =========================================================
      entry qhydr(qqq, iqhy, iqmax)
      dtp = time/1800.0d0
      it2 = int(dtp) + 1
      if(it2 >= iqmax) it2 = iqmax - 1
      dtp = dtp - dble(it2 - 1)
      qqq = (qhyd(iqhy, it2 + 1) - qhyd(iqhy, it2))*dtp + qhyd(iqhy, it2)
      return
!
!     =========================================================
!                    水位ハイドログラフの内挿
!     =========================================================
      entry hhydr(hhh, ihhy, ihmax)
      dtp = time/1800.0d0
      it2 = int(dtp) + 1
      if(it2 >= ihmax) it2 = ihmax - 1
      dtp = dtp - dble(it2 - 1)
      hhh = (hhyd(ihhy, it2 + 1) - hhyd(ihhy, it2))*dtp + hhyd(ihhy, it2)
      return
!
      end subroutine hydro
!
!     ***************************************************************** 
!     =======================================================
!                           初期条件
!     =======================================================
      subroutine initiald
      integer i, j, me, li, n, np
!     ===========================
!         初期水位、流量 read
!     ===========================
      do i = 1, msctn
        read(15, 1151) hs(i), qs(i), qys(i)
      enddo
 1151 format(4x, 3f14.8)
      close(15)
!     ===========================
!                河川
!     ===========================
      do i = 1, msctn
        hn(i) = hs(i)
        qn(i) = qs(i)
        sap(i) = 0.0d0
        sbm(i) = 0.0d0
      enddo
!
      end subroutine initiald
!
!     ***************************************************************
      subroutine soltn
      real(8) cpm, a, v, r, b, an
      real(8) qcs, bvc, dh
      integer i, iqhy, ihhy, iqmax, ihmax, inodek, inode, id
!     *********************************************************
!                ノードをもたない断面の水位・流量
!     *********************************************************
      entry links
      do i = 1, msctn
       if(iptn(i) /= 0) goto 10
       cpm = cap(i) - cbm(i)
       a = as(i) + (cap(i)*sbm(i) - cbm(i)*sap(i))/cpm
       v = us(i) - cap(i)*cbm(i)/as(i)*(sap(i) - sbm(i))/cpm
       call invaz(i, a, hn(i))
       qn(i) = a*v
   10 enddo
      return
!
!     *********************************************************
!                   外部ノードに与える境界条件
!     *********************************************************
      entry bnodes(iqmax, ihmax)
      iqhy = 0
      ihhy = 0
      do inodek = knode1 + 1, knode
      i = nd(inodek, 1)
!
      if(inodek == knode1 + 1 .and. iptn(i) == -1) goto 32   ! 上流端流量（久万川）
      if(inodek == knode1 + 2 .and. iptn(i) == -1) goto 32   ! 上流端流量（紅水川）
      if(inodek == knode1 + 3 .and. iptn(i) ==  1) goto 36   ! 下流端水位
      goto 30
!     ===========================
!           上流端：水位
!     ===========================
   31 ihhy = ihhy + 1
      call hhydr(hn(i), ihhy, ihmax)
      call abrz(i, hn(i), a, r , b)
      qn(i) = a*(us(i) + cap(i)/as(i)*(a - as(i) - sbm(i)))
       goto 30
!     ===========================
!           上流端：流量
!     ===========================
   32 iqhy = iqhy + 1
      call qhydr(qn(i), iqhy, iqmax)
      an = as(i) + (qn(i) - qs(i) + cap(i)*sbm(i))/(us(i) + cap(i))
      call invaz(i, an, hn(i))
       goto 30
!     ===========================
!        上流端：水位-流量曲線
!     ===========================
   33 continue
!      call uphq( time, inode, hs(i), qq, dqdh )
!      hn(i)=hs(i)+(qq-qs(i)+sbm(i)*cs(i))/((us(i)+cs(i))*bs(i)-dqdh)
!      call uphq( time, inode, hn(i), qn(i), dqdh)
       goto 30
!     ===========================
!           下流端：水位
!     ===========================
   36 ihhy = ihhy + 1
      call hhydr(hn(i), ihhy, ihmax)
      call abrz(i, hn(i), a, r, b)
      qn(i) = a*(us(i) + cbm(i)/as(i)*(a - as(i) - sap(i)))
       goto 30
!     ===========================
!           下流端：流量
!     ===========================
   37 iqhy = iqhy + 1
      call qhydr(qn(i), iqhy, iqmax)
      an = as(i) + (qn(i) - qs(i) + cbm(i)*sap(i))/(us(i) + cbm(i))
      call invaz(i, an, hn(i))
       goto 30
!     ===========================
!        下流端：水位-流量曲線
!     ===========================
   38 continue
!      call dnhq( time, inode, hs(i), qq, dqdh )
!      hn(i)=hs(i)+(qq-qs(i)-sap(i)*cs(i))/((us(i)-cs(i))*bs(i)-dqdh)
!      call dnhq( time, inode, hn(i), qn(i), dqdh)
       goto 30
   30 enddo
      return
!
!     *********************************************************
!               内部ノード（分・合流点）の水位・流量
!     *********************************************************
      entry inodes
      if(knode1 == 0) goto 40
      do inode = 1, knode1
       qcs = 0.0d0
       bvc = 0.0d0
       do id=1, mnd(inode)
        i = nd(inode, id)
!     ------- 下流端ノード -------
        if(iptn(i) == 1) then
         qcs = qcs + (qs(i) - cbm(i)*sap(i))
         bvc = bvc + (bs(i)*(us(i) + cbm(i)))
!     ------- 上流端ノード -------
        elseif(iptn(i) == -1) then
         qcs = qcs - (qs(i) - cap(i)*sbm(i))
         bvc = bvc - (bs(i)*(us(i) + cap(i)))
        endif
       enddo
!
       dh = -qcs/bvc
!
       do id = 1, mnd(inode)
        i = nd(inode, id)
        hn(i) = hs(i) + dh
        call abrz(i, hn(i), a, r, b)
!     ------- 下流端ノード -------
        if(iptn(i) == 1) then
         qn(i) = (qs(i) - cbm(i)*sap(i)) + (us(i) + cbm(i))*(a - as(i))
!     ------- 上流端ノード -------
        elseif(iptn(i) == -1) then
         qn(i) = (qs(i) - cap(i)*sbm(i)) + (us(i) + cap(i))*(a-as(i))
        endif
       enddo
      enddo
!
   40 return
      end subroutine soltn
!
!     ==================================================================
      subroutine elm(alpg2, alpbet, cslgb)
      real(8) alpg2, alpbet, cslgb, a, r, b, cs
      real(8) hh
      integer i, j
!
      do i = 1, msctn
        call abrz(i, hn(i), a, r, b)
        if(hn(i) - hb(i) <= 0.0d0) hn(i) = hb(i) + 1.0d-3
        us(i) = qn(i)/a
!        if(us(i)/sqrt(gg*(hn(i) - hb(i))) > 1.0d0) hn(i) = ((qn(i)/b)**2/gg)**0.333333333 + hb(i)   ! 流れが射流の場合、水深を限界水深に置き換え
        hs(i) = hn(i)
        as(i) = a
        qs(i) = qn(i)
        bs(i) = b
        htes(i) = us(i)**2*alpg2+hn(i)
        fs(i) = rn(i)**2*us(i)*abs(us(i))/r**1.3333333
        cs = sqrt((alpbet*us(i))**2 + cslgb*a/b)  
        cap(i) = alpbet*us(i) + cs
        cbm(i) = alpbet*us(i) - cs

      enddo
!
      do i = 1, msctn
!     ------------------------- 左岸側越水
         hh = max(0.0d0, hn(i) - teibol(i))
         qys(i) = qys(i) - 0.35d0*hh*sqrt(2.0d0*gg*hh)
!     ------------------------- 右岸側越水
         hh = max(0.0d0, hn(i) - teibor(i))
         qys(i) = qys(i) - 0.35d0*hh*sqrt(2.0d0*gg*hh)
      enddo
!
      do i = 1, msctn
!     ------------------------- upstream side
       if(iptn(i) == -1) goto 16
       sap(i) = -dt2*((qs(i) - qs(i - 1))/dx2(i - 1) - qys(i - 1) &
                     + bs(i)*cap(i)/cslmd*((htes(i) - htes(i - 1))/dx2(i - 1) + (fs(i - 1) + fs(i))*0.5d0))
!     ------------------------- downstream side
   16  if(iptn(i) ==  1) goto 15
       sbm(i) = -dt2*((qs(i + 1) - qs(i))/dx2(i) - qys(i) &
                     + bs(i)*cbm(i)/cslmd*((htes(i + 1) - htes(i))/dx2(i) + (fs(i) + fs(i + 1))*0.5d0))
   15 enddo
!
      end subroutine elm
!
!     *********************************************************
      subroutine hahr
      real(8) h, hh, hd, a, r, b, bo(irv), dif
      integer i, idm, ii
!     *********************************************************
!                   断面iの水位が与えられたとき
!                 断面積a, 径深r, 水路幅b を求める
!     *********************************************************
      entry abrz(i, hh, a, r, b)
      hd = hh - hb(i)
      if(hd < th) goto 300
      idm = int(hd/0.1d0) + 1
!     ------------------- 断面積、径深
      if(idm <= ihnum(i) - 1) then
        dif = hd - dble(idm - 1)*0.1d0
        a = ha(i, idm) + (ha(i, idm + 1) - ha(i, idm))/0.1d0*dif
        r = hr(i, idm) + (hr(i, idm + 1) - hr(i, idm))/0.1d0*dif
      else
        dif = hd - dble(ihnum(i))*0.1d0
        a = (ha(i, ihnum(i)) - ha(i, ihnum(i) - 1))*hd/0.1d0 + ha(i, ihnum(i))
        r = (hr(i, ihnum(i)) - hr(i, ihnum(i) - 1))*hd/0.1d0 + hr(i, ihnum(i))
      endif
!     ------------------- 川幅
      if(abs(a-as(i)) < 1.0d-5 .or. abs(hn(i) - hs(i)) < 1.0d-7) then
        b = bo(i)
        if(b == 0.0d0) b = a/hd
      else
        b = (a - as(i))/(hn(i) - hs(i))
        bo(i) = b
      endif
      return
!
  300 write(*, 200) i, hh
  200 format(1h/1h, 'too low stage  i, hh=', i5, 3f10.4)
      pause
      a = 0.0d0
      b = 0.0d0
      r = 0.0d0
      return
!
!     *********************************************************
!                   断面iの面積a が与えられたとき
!                         水位hh を求める
!     *********************************************************
      entry invaz(i, a, hh)
       do ii = 1, ihnum(i)
       if(ha(i, ii) > a) then
         h = dble(ii - 2)*0.1d0 + (a - ha(i, ii - 1))/(ha(i, ii) - ha(i, ii - 1))*0.1d0
         goto 410
       endif
      enddo
      write(*, *) i     ! h-a, h-rのデータ数不足
      pause
  410 hh = h + hb(i)
!
      end subroutine hahr
!
!     ******************************************************************
      subroutine wrfile
      real(8) sv, sa, saj, saa
      integer i, j
!     =============================================
!                ディスプレイ表示
!     =============================================
      entry dispwrite
      write(*, 1000) time
 1000 format('   time=', f8.0, '(s)', 5f18.4)
      return
!
      entry diskwrite
      write(81, 2111) time
      do i = 1, msctn
        write(81, 2112) i, hs(i), qs(i), qys(i)
      enddo
 2111 format(f12.1, '  time(sec)')
 2112 format(i4, 3f14.8)
!
      return
!
!     =============================================
!              流量ハイドログラフ書き込み
!     =============================================
      entry qtwrite
!     ------------------------- 河川網：松江流量と矢田の水位
      write(82, 2021) time, hs(52)
 2021 format('time =',f12.1,'     hs =',5f13.8)
!
!     =============================================
!              デバッグ用
!     =============================================
      entry debugwrite
        write(91, 9000) time, hs(1)
        write(92, 9000) time, hs(2)
        write(93, 9000) time, hs(3)
        write(94, 9000) time, hs(4)
        write(95, 9000) time, hs(5)
        write(96, 9000) time, hs(6)
        write(97, 9000) time, hs(7)
        write(98, 9000) time, hs(8)
        9000 format(f10.2, f10.3)
      end subroutine wrfile
!
end module subprogs
!
!
!
!     #######################################################
!     ##                                                   ##
!     ##                   main program                    ##
!     ##                                                   ##
!     #######################################################
!
!
!
program main
  use globals
  use subprogs
  implicit none
      real(8) tday, thour, tmin, tsec, dkout, dpout, dqout, dtva
      real(8) time0, timmax, alpg2, alpbet, cslgb, rnof, dx, dy
      integer i, lpout, lkout, lva, lqout, iqmax, ihmax
      integer kkk
      character*50  fshoki, fkasho, fnoder, fha, fhr, fhydro, fsuii, fqh
!     =====================================================
!                      パラメータ情報
!     =====================================================
      do kkk = 1, 1
      open(10, file = 'river.dat', action = 'read')
      read(10, 1001) tday, thour, tmin, tsec
      read(10, 1002) dt
      read(10, 1002) dkout
      read(10, 1002) dpout
      read(10, 1002) dqout
      read(10, *)
!     =====================================================
!                        ファイル名
!     =====================================================
      read(10, 1009) fshoki
      read(10, 1009) fkasho
      read(10, 1009) fnoder
      read(10, 1009) fha
      read(10, 1009) fhr
      read(10, 1009) fhydro
      read(10, *)
!    ---------------------out 
      read(10, 1009) fsuii
      read(10, 1009) fqh
 1001 format(7x, 4f6.1)
 1002 format(7x, f11.2)
 1003 format(12x, i1)
 1009 format(a50)
      close(10)
!     ===============================================
      time0 = 0.0d0
      timmax = 3600.0d0*24.0d0*tday + 3600.d0*thour + 60.d0*tmin + tsec
      dt2 = 2.0d0*dt
      th = 1.0d-3
      gg = 9.8d0
!
      alpha = 1.0d0
      beta = 1.0d0
      cslmd = 1.0d0
      alpg2 = alpha/(2.0d0*gg)
      alpbet = (alpha - beta)/(2.0d0*beta)
      cslgb = cslmd*gg/beta
!     =====================================================
!                        書き込み時間
!     =====================================================
      lpout = int(dpout/dt)
      lkout = int(dkout/dt)
      lqout = int(dqout/dt)
!     =====================================================
!                     データファイル開く
!     =====================================================
!     ------------------------------- 入力ファイル
      open(10, file = fkasho, action = 'read')
      open(11, file = fha, action = 'read')
      open(12, file = fhr, action = 'read')
      open(13, file = fnoder, action = 'read')
      open(14, file = fhydro, action = 'read')
      open(15, file = fshoki, action = 'read')
!     ------------------------------- 出力ファイル
      open(81, file = fsuii, action = 'write')
      open(82, file = fqh, action = 'write')
      !open(91, file = 'out/suii1.dat', action = 'write')
      !open(92, file = 'out/suii2.dat', action = 'write')
      !open(93, file = 'out/suii3.dat', action = 'write')
      !open(94, file = 'out/suii4.dat', action = 'write')
      !open(95, file = 'out/suii5.dat', action = 'write')
      !open(96, file = 'out/suii6.dat', action = 'write')
      !open(97, file = 'out/suii7.dat', action = 'write')
      !open(98, file = 'out/suii8.dat', action = 'write')
!     =====================================================
!                       データ読み込み
!     =====================================================
      call rdat
      call bndry(iqmax, ihmax)
!     =====================================================
!                         初期条件
!     =====================================================     
      call initiald
!     =====================================================
      time = time0
      mstep = 0
!     =====================================================
      call elm(alpg2, alpbet, cslgb)
!     =====================================================
      call diskwrite
      call dispwrite
      !call qtwrite
!     +++++++++++++++++++++++++++++++++++++++++++++++++++++
!                       loop start↓
!     +++++++++++++++++++++++++++++++++++++++++++++++++++++
      goto 100
    1 continue
!     ==========================
!         横流入流量リセット
!     ==========================
      do i = 1, msctn
        qys(i) = 0.0d0
      enddo
!     $$$$$$$$$$$$$$$$$$$$
!         河川網の計算
!     $$$$$$$$$$$$$$$$$$$$
      call links
      call inodes
      call bnodes(iqmax, ihmax)
      call elm(alpg2, alpbet, cslgb)
  100 continue
!     ====================
!         time step       
!     ====================
      time = time + dt
      mstep = mstep + 1
!     ====================
!         time step       
!     ====================
      time = time + dt
      mstep = mstep + 1
!     =================================================================
!              unst1.f出力
!     =================================================================
      if(mod(mstep, lkout) == 0) call diskwrite
      if(mod(mstep, lpout) == 0) call dispwrite
      !if(mod(mstep, lqout) == 0) call qtwrite
      !if(time >= 46200.0d0) call debugwrite
!     =================================================================
!              time judging
!     =================================================================
      if(time + dt <= timmax) goto 1
!     +++++++++++++++++++++++++++++++++++++++++++++++++++++
!                          loop end
!     +++++++++++++++++++++++++++++++++++++++++++++++++++++
      call diskwrite
      write(*, 1999) time, timmax
 1999 format('      - normal end -  time=', f8.0, '  timmax=', f8.0)
      pause
 9999 continue
!     ------------------------------- 出力ファイル
        close(81)
        close(82)
        close(91)
        close(92)
        close(93)
        close(96)
        close(97)
        close(98)
        close(99)
      enddo
!
end program main
