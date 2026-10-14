program main

    implicit none
    real(8), allocatable :: kasho(:), hwl(:), suii(:, :)
    real(8), allocatable :: time(:)
    integer :: msctn
    integer :: i, j, k, iost, count
    character fyodo*128
    character fkatsura*128
    character fkizu*128
    
    ! ここで読み込むファイルを指定する
    open(11, file = 'suii.dat', action = 'read')
    open(12, file = 'kasho.dat', action = 'read')
    
!---kasyo.datの読み取り
    read(12, 1200) msctn
    read(12, *)
    1200 format(i5)
    
    allocate(kasho(msctn), hwl(msctn), suii(600, msctn))
    allocate(time(600))
    
    do i = 1, msctn
        read(12, 1201) kasho(i), hwl(i)
    enddo
    1201 format(20x, f11.3, 22x, f14.3)
    
    close(12)
    write(*, *) "kasyo.dat   読み取り完了"
    
    
!---水位データの読み取り
    count = 0
    do j = 1, 600
        read(11, 1100, iostat = iost) time(j)
        if(iost < 0) exit
        
        do i = 1, msctn
            read(11, 1101) suii(j, i)
        enddo
        count = count + 1
    enddo
    1100 format(f12.1)
    1101 format(4x, f14.8)
    
    close(11)
    write(*, *) "水位データ   読み取り完了"
    
    
!---出力(久万川:断面番号1～53)
    do j = 1, count
        write(fyodo, '("kuma/suii", i3.3, ".dat")') j+99
        open(21, file = fyodo, action = 'write', status = 'replace')
        do i = 1, 53
            write(21, 2100) i, kasho(i), hwl(i), suii(j, i)
        enddo
        close(21)
        write(*, *) fyodo, "   出力完了"
    enddo
    2100 format(i5, 3(f11.3))
    
!---出力(紅水川:断面番号54～92)
    do j = 1, count
        write(fkatsura, '("kohsui/suii", i3.3, ".dat")') j+99
        open(22, file = fkatsura, action = 'write', status = 'replace')
        do i = 54, 92
            write(22, 2200) i, kasho(i), hwl(i), suii(j, i)
        enddo
        close(22)
        write(*, *) fkatsura, "   出力完了"
    enddo
    2200 format(i5, 3(f11.3))
    
end program main