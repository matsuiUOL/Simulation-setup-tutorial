C     ##########################################
C
C            h-A, h-r <-- 5m‚Ì•Ç‚ð‚Â‚¯‚é
C
C     ##########################################
C
      PARAMETER(INO = 430, JNO = 10, KNO = 400)
      DIMENSION NOA(INO), HA(INO, KNO), NOR(INO), HR(INO, KNO)
C
      ISCTN = 92
      OPEN(10, FILE = 'h-a.dat', STATUS = 'OLD')
      OPEN(11, FILE = 'h-r.dat', STATUS = 'OLD')
      OPEN(71, FILE = 'hahosei.dat', STATUS = 'UNKNOWN')
      OPEN(72, FILE = 'hrhosei.dat', STATUS = 'UNKNOWN')
C
      DO I = 1, ISCTN
        READ(10, 1000) NOA(I)
        READ(10, 1001) (HA(I, K), K = 1, NOA(I))
        READ(11, 1000) NOR(I)
        READ(11, 1001) (HR(I, K), K = 1, NOR(I))
      ENDDO
 1000 FORMAT(3X, I10)
 1001 FORMAT(10F10.3)
      CLOSE(10)
      CLOSE(11)
C
      DO I = 1, ISCTN
        SS = HA(I, NOA(I))/HR(I, NOR(I))   ! •Ó
        BS = (HA(I, NOA(I)) - HA(I, NOA(I) - 1))/0.1
C        BS(I)=SS(I)-FLOAT(NOA(I))*0.1*2.  ! ì•H
      DO J = 1, 50
        HP = FLOAT(J)*0.1
        HA(I, NOA(I) + J) = BS*HP + HA(I, NOA(I))       
        HR(I, NOR(I) + J) = HA(I, NOA(I) + J)/(SS + HP*2.)
!        HR(I, NOR(I) + J) = HA(I, J)/(SS + HP*2.)
      ENDDO
C
        WRITE(71, 4000) I, NOA(I) + 50
        WRITE(71, 4001) (HA(I, K), K = 1, NOA(I) + 50)
        WRITE(72, 4000) I, NOR(I) + 50
        WRITE(72, 4001) (HR(I, K), K = 1, NOR(I) + 50)
      ENDDO
 4000 FORMAT(I3, I10)
 4001 FORMAT(10F10.3)
      CLOSE(71)
      CLOSE(72)
C
      STOP
      END
