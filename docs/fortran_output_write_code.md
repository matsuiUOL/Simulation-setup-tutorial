# Fortran本体：外部ファイル出力部（抜粋）

元ファイル: `others/` 内のメモを整形したもの。Fortran本体がどの書式で各入力ファイルを読むかの参考。

## 17 disk_riv

```fortran
    write(151, 1511) time
    do i = 1, msctn
      write(151, 1512) i, hs_riv(i), qs_riv(i), qys_riv(i)
    enddo
entry overtop_hantei(timmax)
    write(152, *) '------------ Left Side ------------'
    do i = 1, msctn
      write(152, 1521) i, overtop_l(i)
    enddo
    write(152, *)
    write(152, *) '------------ Right Side ------------'
    do i = 1, msctn
      write(152, 1521) i, overtop_r(i)
    enddo
    1521 format(2i8)
    close(152)
! 越流量の合計値を出力
    ! ファイル番号
    ! 153         overtop_q_ac.dat
    write(153, *) '------------ River to Flood Plain'
    do i = 1, msctn
      write(153, 1531) i, ac_rivtome(i), ac_metoriv(i), ac_rivme(i)
    enddo
    write(153, *) '------------ River to Uncalculated Area'
    do i = 1, msctn
      write(153, 1532) i, ac_rivtoouter(i, 1), ac_rivtoouter(i, 2)
    enddo
    1531 format(i6, 3f12.4)
    1532 format(i6, 2f12.4)
    1539 format(a99)
    close(153)
! 越流する流量(5分間平均)を出力
    ! ファイル番号
    ! 154         overtop_q.dat
    max_it = int(timmax/300.0d0) + 1
    do i = 1, msctn
      do j = 1, 2
        do it = 1, max_it
          q_rivtome(i, j, it) = q_rivtome(i, j, it) / 300.0d0
        enddo
      enddo
    enddo
    do it = 1, max_it
      write(154, 1541) dble(it - 1)*300.0d0
      do i = 1, msctn
        write(154, 1542) i, q_rivtome(i, 1, it), q_rivtome(i, 2, it)
      enddo
    enddo
    1541 format('time = ', f10.2, '(s)')
    1542 format(i6, 2f12.4)
    close(154)
 end subroutine disk_riv
```
