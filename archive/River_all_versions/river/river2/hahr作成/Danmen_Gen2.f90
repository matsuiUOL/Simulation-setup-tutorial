!
!
!   河道断面の座標値からh-r.dat,h-a.datを計算・生成するプログラム
!   ごめんなさい、不具合が多いです。
!
!   config.dat
!   danmen : 処理したい断面の数
!   yoko   : 縦横の縮尺比を考慮するために使う。横方向を(yokoに入れた値)倍する
!   rn     : 粗度係数
!   dx     : 断面の間隔
!   5行目  : 入力ファイル
!
!   入力ファイル(uji.dat)
!   1行目  : ノード(座標を取った点)の個数
!   2行目～: ノードのx,y座標
!            ただし、x座標が小さい順に並べること。
!            また、x座標が同じ点が2つ以上あったらダメ
!            このルールを守らないとこのプログラムは動きません。
!   もしプログラム組むのが得意な方がいたら改良していただけると大変ありがたいです。
!



module param
    implicit none
    
    real(8), allocatable, save :: ha(:, :), hr(:, :)
    integer, allocatable, save :: sep(:)
    
    integer, save :: node
    real(8), allocatable, save :: rnx(:), rny(:)
    real(8), allocatable, save :: nx(:), ny(:)
    real(8), allocatable, save :: lin_a(:), lin_b(:)
    real(8), allocatable, save :: cx(:)
    
    integer, save :: ix, danmen
    real(8), save :: yoko
    character(50), save :: fzahyo
    
    real(8), allocatable, save :: r_dist(:), mini_ny(:)
    real(8), allocatable, save :: teibou_l(:), teibou_r(:)
    integer, save :: kawa, iptn
    real(8), save :: rn, dx
    
    integer, save :: i, j, k
    integer, save :: f_end, danmen_count
end module param







module sub_prog
    use param
    implicit none
contains

    subroutine warituke
        allocate(ha(danmen, 1000), hr(danmen, 1000))
        allocate(sep(danmen))
        allocate(rnx(999), rny(999))
        allocate(nx(999), ny(999))
        allocate(lin_a(999), lin_b(999))
        allocate(cx(999))
        allocate(r_dist(999), mini_ny(999))
        allocate(teibou_l(999), teibou_r(999))
        return
    end subroutine warituke
    
    
!---数値の初期化
    subroutine initialset(ix)
        integer :: ix
    
        do i = 1, 1000
            ha(ix, i) = 0.0d0
            hr(ix, i) = 0.0d0
        enddo
        node = 0
        sep(ix) = 0
        do i = 1, 999
            rnx(i) = 0.0d0
            rny(i) = 0.0d0
            nx(i) = 0.0d0
            ny(i) = 0.0d0
            lin_a(i) = 0.0d0
            lin_b(i) = 0.0d0
            cx(i) = 0.0d0
        enddo
        
        return
    end subroutine initialset
    
    
!---断面の座標データ読み込み
    subroutine rdat(ix, node)
        integer :: ix, node, iost
    
        !read(11, 1111) r_dist(ix), node
        read(11, *, iostat = iost) r_dist(ix), node
        1111 format(f4.1, 6x, i5)
        !write(*, *) node
        if(iost < 0) then
            f_end = 1
            return
        endif
        do i = 1, node
            read(11, *) rnx(i), rny(i)
        enddo
        
        return
    end subroutine rdat


!---計算前のデータ前処理
    subroutine dat_proc(ix, node)
        integer :: ix, node
    
        real(8) :: teibou_h
        
        !もっとも標高の低い点が z=0 となるように調整
        mini_ny(ix) = rny(1)
        do i = 2, node
            mini_ny(ix) = min(mini_ny(ix), rny(i))
        enddo
        !0.1で割り切れる中間点があると面倒なので0.001下げる
        do i = 1, node
            nx(i) = rnx(i) * yoko !横の縮尺比補正
            ny(i) = rny(i) - mini_ny(ix) + 0.001
           ! if( ny(i) /= 0.0d0 .and. mod(ny(i), 0.1d0) == 0 .and. i /= 1 .and. i /= node) then
           !     ny(i) = ny(i) - 0.001
           ! endif
        enddo
        !左岸か右岸、どちらか低い方の堤防の高さから分割数を求める
        teibou_h = min(ny(1), ny(node))
        sep(ix) = (teibou_h / 0.1d0) + 1
        !write(*, *) teibou_h,ix,node, sep(ix)
        
        teibou_l(ix) = rny(1)
        teibou_r(ix) = rny(node)
    
        return
    end subroutine dat_proc
    
    
!---ノードどうしをつなぐ直線の式を計算する
    subroutine lincal
        integer :: link
        link = node - 1
        
        do i = 1, link
            lin_a(i) = (ny(i+1) - ny(i)) / (nx(i+1) - nx(i))
            lin_b(i) = ny(i) - lin_a(i) * nx(i)
        enddo
    end subroutine lincal
    
    
!---h-a,h-rを求める
    subroutine arcal(ix)
        integer :: ix, link, num_cx, seki, m, st, gl, loc
        real(8) :: h, kouten
        real(8) :: jun, area
        real(8) :: dist, menseki
        
        link = node - 1
        h = 0.1d0
        
        ha(ix, 1) = 0.0d0
        hr(ix, 1) = 0.0d0
        
        do i = 2, sep(ix)
        
            jun = 0.0d0
            area = 0.0d0
        
            !高さhの位置に直線を引き、交点を全て求める
            k = 1
            do j = 1, link
                kouten = ( h - lin_b(j) ) / lin_a(j)
                if( kouten > nx(j) .and. nx(j+1) > kouten ) then
                    cx(k) = kouten
                    k = k + 1
                endif
            enddo
            num_cx = k - 1
            if( mod(num_cx, 2) /= 0) then
                write(*, *) '距離', r_dist(ix), '高さ ', h + mini_ny(ix)
                write(*, *) '同じx座標の点が複数ある、またはデータの順番に誤りがあります。'
                stop
            endif
            seki = num_cx / 2
            
            !積分によって径深、断面積を計算する
            do j = 1, seki
                !cx(2*j-1)(=積分の始点)がどの直線上にあるのか探す
                m = 2 * j - 1
                do k = 1, node
                    if( cx(m) >= nx(k) .and. nx(k+1) >= cx(m) ) then
                        st = k
                        goto 110
                    endif
                enddo
                110 continue
                !cx(2*j)(=積分の終点)がどの直線上にあるか探す
                do k = 1, node
                    if( cx(m+1) >= nx(k) .and. nx(k+1) >= cx(m+1) ) then
                        gl = k
                        goto 120
                    endif
                enddo
                120 continue
                
                !始点部分の計算
                loc = st
                dist = sqrt( ( nx(st+1) - cx(m) )**2 + ( ny(st+1) - h )**2 )
                menseki = (nx(st+1) - cx(m)) * abs(ny(st+1) - h) / 2
                jun = jun + dist
                area = area + menseki
                loc = loc + 1
                
                !中間部分の計算
                do while(loc < gl)
                    dist = sqrt( (nx(loc+1)-nx(loc))**2 + (ny(loc+1)-ny(loc))**2)
                    menseki = (2*h - ny(loc) - ny(loc+1)) * (nx(loc+1)-nx(loc)) / 2
                    jun = jun + dist
                    area = area + menseki
                    loc = loc + 1
                enddo
                !終点部分の計算
                dist = sqrt((nx(gl) - cx(m+1))**2 + (ny(gl) - h)**2)
                menseki = (cx(m+1) - nx(gl)) * abs(ny(gl) - h) / 2
                jun = jun + dist
                area = area + menseki
            enddo
            
            !径深=断面積/潤辺
            hr(ix, i) = area / jun
            ha(ix, i) = area
            
            h = h + 0.1d0
        enddo
        
        return
    end subroutine arcal
end module sub_prog







program main
!    use param
    use sub_prog
    
    implicit none
    
!---config.datの読み込み
!   danmen : 処理を行う断面の個数
!   yoko   : 縦と横の縮尺比
!   rn     : 粗度係数
!   dx     : 断面の間隔
!   fzahyo : 座標データへのパス
    open(10, file = 'config.dat', action = 'read')
    read(10, 1011) danmen
    read(10, 1012) yoko
    read(10, 1013) rn
    read(10, 1014) dx
    read(10, 1020) fzahyo
    1011 format(8x, i4)
    1012 format(8x, f7.2)
    1013 format(8x, f8.3)
    1014 format(8x, f6.1)
    1020 format(a50)
    close(10)
    
    call warituke    
    f_end = 0
    danmen_count = 0
    
!---h-a,h-rの計算を行う部分
    open(11, file = fzahyo, action = 'read')
    
    do ix = 1, danmen
        call initialset(ix)
        call rdat(ix, node)
        if(f_end == 1) exit
        danmen_count = danmen_count + 1
        call dat_proc(ix, node)
        call lincal
        call arcal(ix)
    enddo
    
    close(11)
    
!---出力
    open(21, file = 'h-r.dat', action = 'write')
    danmen = danmen_count
    write(*, 9901) 'num_danmen = ', danmen
    9901 format(a13, i5)
    
!    do ix = 1, danmen
    j = 1
    do ix = danmen, 1, -1
        write(21, 2101) j, sep(ix)
        write(21, 2102) (hr(ix, i), i = 1, sep(ix))
        j = j + 1
    enddo
    2101 format(i3, i10)
    2102 format(10f10.3)
    close(21)
    
    open(22, file = 'h-a.dat', action = 'write')
    
!    do ix = 1, danmen
    j = 1
    do ix = danmen, 1, -1
        write(22, 2101) j, sep(ix)
        write(22, 2102) (ha(ix, i), i = 1, sep(ix))
        j = j + 1
    enddo
    close(22)
    
    
    
    open(23, file = 'kasyo.dat', action = 'write')
    
    write(23, 2301) danmen
    write(23, *) '  IND 距離 KAWA IPTN      HB(m)                               RN      DX(m)'
    2301 format(i5)
    
    j = 1
    kawa = 1
    do ix = danmen, 1, -1
        if(j==1) then
            iptn = -1
        else if(j==danmen) then
            iptn = 1
        else
            iptn = 0
        endif
        write(23, 2302) j, r_dist(ix), kawa, iptn, mini_ny(ix), teibou_l(ix), teibou_r(ix), rn, dx
        j = j + 1
    enddo
    2302 format(i5, f6.2, i4, i5, 4f11.3, f11.1)
    close(23)
    
    write(*, *) 'h-a.dat, h-r.dat, kasyo.datは正常に出力されました。'
    
end program main