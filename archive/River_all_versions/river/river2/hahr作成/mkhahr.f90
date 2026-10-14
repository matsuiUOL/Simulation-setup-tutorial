      common /aa/ ko(500), x(500, 300), y(500, 300), ymin(500)
      common /bb/ asum(500, 200), ssum(500, 200), r(500, 200)
!
!     ==========================
!             read file
!     ==========================
      open(20, file = 'h-a.dat', status = 'unknown')
      open(30, file = 'h-r.dat', status = 'unknown')

      isctn = 92
      open(10, file = 'danmen_data.dat', status = 'old')
         read(10, *)
      !do i = 1, isctn
      do i = isctn, 1, -1
         read(10, *) dd, ko(i)
         write(*,*) i, dd, ko(i)
         do k = 1, ko(i)
            read(10, *) x(i, k), y(i, k)
         enddo
         !read(10, *)
      enddo
      close(10)
!
!     ==========================
!           y-minimum cal
!     ==========================
      do i = 1, isctn
        km = 1
        ymin(i) = 1000.0
        do k = 1, ko(i)
!           ymin(i) = min(ymin(i), y(i, k))
          if(y(i, k) < ymin(i)) then
             km = k
             ymin(i) = y(i, k)
          endif
        enddo
!       ------------- ¶Šİì’ç–h‚‚Æ‚»‚Ì’n“_
        kos = 1
        ymax = ymin(i)
        do k = 1, km
           if(y(i, k) > ymax) then
              kos = k
              ymax = y(i, k)
           endif
        enddo
!       ------------- ‰EŠİì’ç–h‚‚Æ‚»‚Ì’n“_
        koe = km
        ymax = ymin(i)
        do k = km, ko(i)
           if(y(i, k) > ymax) then
              koe = k
              ymax = y(i, k)
           endif
        enddo
!
!     ==========================
!     …[‚ğ10cm‚İ‚Åã‚°‚Ä‚¢‚­
!     ==========================
      do ih = 1, 200
        dh = float(ih)*0.1
        hh = ymin(i) + dh
        if(y(i, kos) < hh .or. y(i, koe) < hh) goto 209
        isw = 0                         ! 0:…ˆÊ‚ªhh‚æ‚èãA1:…ˆÊ‚ªhh‚æ‚è‰º
        asum(i, ih) = 0.0
        ssum(i, ih) = 0.0
!     ==========================
!           Œğ“_‚ğŒ©‚Â‚¯‚é
!     ==========================
        do k = kos, koe
          if(isw.eq.0 .and. y(i, k).lt.hh) then
            isw = 1
            ks = k
          elseif(isw.eq.1 .and. y(i, k).ge.hh) then
            isw = -1
            ke = k - 1
          endif
          if(isw.eq.-1) then
            call danmen(i, hh, ks, ke, a, s, isw)
            asum(i, ih) = asum(i, ih) + a
            ssum(i, ih) = ssum(i, ih) + s
          endif
        enddo
      enddo
!
  209 num = ih - 1
      do ih = 1, num
          r(i, ih) = asum(i, ih)/ssum(i, ih)
      enddo
!     ==========================
!            write file
!     ==========================
      write(20, 1021) i, num + 1
      write(30, 1021) i, num + 1
      write(20, 1022) dummy, (asum(i, ih), ih = 1, num)
      write(30, 1022) dummy, (r(i, ih), ih = 1, num)
      enddo
 1021 format(i3, i10)
 1022 format(10f10.3)
!
      end
!
!
!     ************************************************************
      subroutine danmen(i, hh, ks, ke, a, s, isw)
      common /aa/ ko(500), x(500, 300), y(500, 300), ymin(500)
!     ====================
!         Œğ“_‚ÌxÀ•W
!     ====================
      if(ks.eq.1) then
        xs = x(i, 1)
      else
        xs = x(i, ks - 1) + (y(i, ks - 1) - hh)/(y(i, ks - 1) - y(i, ks))*(x(i, ks) - x(i, ks - 1))
      endif
      if(ke.eq.ko(i)) then
        xe = x(i,ko(i))
      else
        xe = x(i, ke + 1) - (y(i, ke + 1) - hh)/(y(i, ke + 1) - y(i, ke))*(x(i, ke + 1) - x(i, ke))
      endif
!     ====================
!     ’f–Êi‚Ì…ˆÊhh‚É‘Î‚·‚é
!     ’f–ÊÏa‚ÆŒa[s‚ğŒvZ
!     ====================
        a = (hh - y(i, ks))*(x(i, ks) - xs)/2.0
        s = sqrt((x(i, ks) - xs)**2 + (hh - y(i, ks))**2)
      do k = ks, ke - 1
        a = a + ((hh - y(i, k)) + (hh - y(i, k + 1)))*(x(i, k + 1) - x(i, k))/2.0
        s = s + sqrt((x(i, k + 1) - x(i, k))**2 + (y(i, k + 1) - y(i, k))**2)
      enddo
        a = a + (hh - y(i, ke))*(xe - x(i, ke))/2.0
        s = s + sqrt((xe - x(i, ke))**2 + (hh - y(i, ke))**2)
      isw = 0
!
      return
      end
