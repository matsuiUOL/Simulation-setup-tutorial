program bsmake
  implicit none
  integer me, i
  integer mesh, num_bsdata, tmp
  real(8) , allocatable :: xg(:), yg(:),  xcoord(:), ycoord(:), bsdata(:)
  real(8) , allocatable :: xg_min(:), xg_max(:), yg_min(:), yg_max(:)  
  real(8) , allocatable :: dist1(:), dist2(:), dist3(:)
  integer , allocatable :: near1(:), near2(:), near3(:)
  integer , allocatable :: near_me1(:), near_me2(:), near_me3(:)
  real(8) , allocatable :: drate1(:), drate2(:), drate3(:), drate_total(:), bs(:) 
  real(8) kyori


  open(11, file = 'centroid0129_v2.dat', action = 'read')
  open(12, file = 'out5m2_city0.txt', action = 'read')
  open(99, file = 'bs_op_corrected_city0.dat', action = 'write')
  open(98, file = 'checknear1ichioka.dat', action = 'write')
  open(97, file = 'checknear2ichioka.dat', action = 'write')
  open(96, file = 'checknear3ichioka.dat', action = 'write')
  open(95, file = 'checkdrateichioka.dat', action = 'write')
  open(94, file = 'check_none_coord.dat', action = 'write')


  read(11, '(6x, i7)') mesh
  write(*, *) mesh
  allocate(xg(mesh), yg(mesh), xg_min(mesh), xg_max(mesh), yg_min(mesh), yg_max(mesh))
  do me = 1, mesh
    read(11, *) tmp, xg(me), yg(me)
    xg_min(me) = xg(me) - 20.0d0
    xg_max(me) = xg(me) + 20.0d0
    yg_min(me) = yg(me) - 20.0d0
    yg_max(me) = yg(me) + 20.0d0
  enddo

  num_bsdata = 0

  do
    read(12, *, end = 1000)
    num_bsdata = num_bsdata + 1
  enddo
1000 continue
  rewind(12)

  write(*, *) num_bsdata

  allocate(xcoord(num_bsdata), ycoord(num_bsdata), bsdata(num_bsdata))

  do i = 1, num_bsdata
    read(12, *) xcoord(i), ycoord(i), bsdata(i)
  enddo

  allocate(dist1(mesh), dist2(mesh), dist3(mesh))
  allocate(near1(mesh), near2(mesh), near3(mesh))
  allocate(near_me1(mesh), near_me2(mesh), near_me3(mesh))
  allocate(drate1(mesh), drate2(mesh), drate3(mesh), drate_total(mesh), bs(mesh))

  do me = 1, mesh
    dist1(me) = 1.0d9
    dist2(me) = 1.0d9
    dist3(me) = 1.0d9
  enddo

  do me = 1, mesh
    near1(me) = 0
    near2(me) = 0
    near3(me) = 0
  enddo

  do me = 1, mesh
    do i = 1, num_bsdata
      if(bsdata(i) == 0.0d0) goto 1001 
      if(xcoord(i) <= xg_min(me)) goto 1001
      if(xcoord(i) >= xg_max(me)) goto 1001
      if(ycoord(i) <= yg_min(me)) goto 1001
      if(ycoord(i) >= yg_max(me)) goto 1001
        kyori = sqrt(((xg(me) - xcoord(i)) ** 2.0d0) + ((yg(me) - ycoord(i)) ** 2.0d0))
        dist1(me) = min(kyori, dist1(me))
        if(kyori == dist1(me)) then
          near1(me) = i
        endif
1001 enddo      
    write(98, *) me, near1(me), dist1(me), bsdata(near1(me))
  enddo

  write(*, *) 'near1 finished'

  do me = 1, mesh
    do i = 1, num_bsdata
      if(i == near1(me)) goto 1002
      if(bsdata(i) == 0.0d0) goto 1002 
      if(xcoord(i) <= xg_min(me)) goto 1002
      if(xcoord(i) >= xg_max(me)) goto 1002
      if(ycoord(i) <= yg_min(me)) goto 1002
      if(ycoord(i) >= yg_max(me)) goto 1002
      kyori = sqrt(((xg(me) - xcoord(i)) ** 2.0d0) + ((yg(me) - ycoord(i)) ** 2.0d0))
      dist2(me) = min(kyori, dist2(me))
      if(dist2(me) == kyori) then
        near2(me) = i
      endif
1002 enddo
    write(97, *) me, near2(me), dist2(me), bsdata(near2(me))
  enddo

  write(*, *) 'near2 finished'

  do me = 1, mesh
    do i = 1, num_bsdata
      if(i == near1(me) .or. i == near2(me)) goto 1003
      if(bsdata(i) == 0.0d0) goto 1003 
      if(xcoord(i) <= xg_min(me)) goto 1003
      if(xcoord(i) >= xg_max(me)) goto 1003
      if(ycoord(i) <= yg_min(me)) goto 1003
      if(ycoord(i) >= yg_max(me)) goto 1003
      kyori = sqrt(((xg(me) - xcoord(i)) ** 2.0d0) + ((yg(me) - ycoord(i)) ** 2.0d0))
      dist3(me) = min(kyori, dist3(me))
      if(dist3(me) == kyori) then
        near3(me) = i
      endif
1003 enddo
    write(96, *) me, near3(me), dist3(me), bsdata(near3(me))
  enddo

  write(*, *) 'near3 finished'

  do me = 1, mesh
    if(near3(me) /= 0)then
      drate1(me) = dist2(me) * dist3(me)
      drate2(me) = dist3(me) * dist1(me)
      drate3(me) = dist1(me) * dist2(me)
      drate_total(me) = drate1(me) + drate2(me) + drate3(me)
      write(95, *) me, drate1(me), drate2(me), drate3(me), drate_total(me)
      bs(me) = bsdata(near1(me)) * (drate1(me) / drate_total(me)) &
               + bsdata(near2(me)) * (drate2(me) / drate_total(me)) &
               + bsdata(near3(me)) * (drate3(me) / drate_total(me))
    elseif(near2(me) /= 0)then
      drate1(me) = dist2(me)
      drate2(me) = dist1(me)
      drate3(me) = 0.0d0
      drate_total(me) = drate1(me) + drate2(me)
      write(95, *) me, drate1(me), drate2(me), drate3(me), drate_total(me)
      bs(me) = bsdata(near1(me)) * (drate1(me) / drate_total(me)) &
               + bsdata(near2(me)) * (drate2(me) / drate_total(me))
    elseif(near1(me) /= 0)then
      drate1(me) = dist2(me)
      drate2(me) = 0.0d0
      drate3(me) = 0.0d0
      drate_total(me) = drate1(me)
      write(95, *) me, drate1(me), drate2(me), drate3(me), drate_total(me)
      bs(me) = bsdata(near1(me))
    endif            
!    write(99, *) me, bs(me)
  enddo

! if xg, yg cannot find near xcoord ycoord
  do me = 1, mesh
    xg_min(me) = xg(me) - 1000.0d0
    xg_max(me) = xg(me) + 1000.0d0
    yg_min(me) = yg(me) - 1000.0d0
    yg_max(me) = yg(me) + 1000.0d0
  enddo

  do me = 1, mesh
    if(near1(me) == 0)then
      do i = 1, mesh
        if(near1(i) == 0) goto 2001
        if(xg(i) <= xg_min(me)) goto 2001
        if(xg(i) >= xg_max(me)) goto 2001
        if(yg(i) <= yg_min(me)) goto 2001
        if(yg(i) >= yg_max(me)) goto 2001
        kyori = sqrt(((xg(me) - xg(i)) ** 2.0d0) + ((yg(me) - yg(i)) ** 2.0d0))
        dist1(me) = min(kyori, dist1(me))
        if(dist1(me) == kyori)then
          near_me1(me) = i
        endif
2001  enddo
      do i = 1, mesh
        if(near1(i) == 0) goto 2002
        if(i == near_me1(me)) goto 2002
        if(xg(i) <= xg_min(me)) goto 2002
        if(xg(i) >= xg_max(me)) goto 2002
        if(yg(i) <= yg_min(me)) goto 2002
        if(yg(i) >= yg_max(me)) goto 2002
        kyori = sqrt(((xg(me) - xg(i)) ** 2.0d0) + ((yg(me) - yg(i)) ** 2.0d0))
        dist2(me) = min(kyori, dist2(me))
        if(dist2(me) == kyori)then
          near_me2(me) = i
        endif
2002  enddo
      do i = 1, mesh
        if(near1(i) == 0) goto 2003
        if(i == near_me1(me)) goto 2003
        if(i == near_me2(me)) goto 2003
        if(xg(i) <= xg_min(me)) goto 2003
        if(xg(i) >= xg_max(me)) goto 2003
        if(yg(i) <= yg_min(me)) goto 2003
        if(yg(i) >= yg_max(me)) goto 2003
        kyori = sqrt(((xg(me) - xg(i)) ** 2.0d0) + ((yg(me) - yg(i)) ** 2.0d0))
        dist3(me) = min(kyori, dist3(me))
        if(dist3(me) == kyori)then
          near_me3(me) = i
        endif
2003  enddo
      drate1(me) = dist2(me) * dist3(me)
      drate2(me) = dist3(me) * dist1(me)
      drate3(me) = dist1(me) * dist2(me)
      drate_total(me) = drate1(me) + drate2(me) + drate3(me)
      bs(me) = bs(near_me1(me)) * (drate1(me) / drate_total(me)) &
             + bs(near_me2(me)) * (drate2(me) / drate_total(me)) &
             + bs(near_me3(me)) * (drate3(me) / drate_total(me))
    endif
  enddo

  do me = 1, mesh
    if(near1(me) == 0)then
      if(near_me1(me) == 0)then
        write(94, '(i7,"   caution!")') me
      else
        write(94, *) me, near_me1(me), bs(near_me1(me)), near_me2(me), bs(near_me2(me)), near_me3(me), bs(near_me3(me))
      endif
    endif
  enddo     


! ! TP OP adjustment (set to OP)
   do me = 1, mesh
!     bs(me) = bs(me) + 1.3d0
     write(99, *) me, bs(me)
   enddo

   write(*, *) 'Completed!'

end program


