!     ##################################################################
!     ##                                                              ##
!     ##       PRE-DATA (MESH.DAT, LINK.DAT) GENERATING PROGRAM       ##
!     ##                                                              ##
!     ##################################################################
!
      IMPLICIT DOUBLE PRECISION (A-H,O-Z)
      PARAMETER(MEG=90000,NOG=50000,LIG=300000,KOG=10)
      COMMON / AA /  KO(MEG),MENODE(MEG,KOG),MELINK(MEG,KOG)
      COMMON / BB /  DNOX(NOG),DNOY(NOG)
      COMMON / CC /  NEIB1(LIG),NEIB2(LIG),LNODE1(LIG),LNODE2(LIG)
      COMMON / DD /  SMESH(MEG),XMESH(MEG),YMESH(MEG)
      COMMON / FF /  WEI(MEG,KOG)
      COMMON / GG /  SCV(LIG),HMRATIO(LIG,2),UX(LIG),UY(LIG)
      COMMON / ZZ /  MESH,LINK
!
      OPEN(11,FILE='node.dat', STATUS='OLD')
      OPEN(12,FILE='mesho.dat',STATUS='OLD')
      OPEN(20,FILE='link.dat',STATUS='UNKNOWN')
      OPEN(30,FILE='mesh.dat',STATUS='UNKNOWN')
!
              WRITE(*,*) 'RDAT'
      CALL RDAT
              WRITE(*,*) 'MKLINK'
      CALL MKLINK
              WRITE(*,*) 'MKMESH'
      CALL MKMESH
              WRITE(*,*) 'MKLINK2'
      CALL MKLINK2
!     ======================================================================
!                    WRITE LINK DATA
!     ======================================================================
      WRITE(20,1021) LINK
      DO LI=1,LINK
        WRITE(20,1022) LI,NEIB1(LI),NEIB2(LI),LNODE1(LI),LNODE2(LI)
        WRITE(20,1023) SCV(LI),HMRATIO(LI,1),HMRATIO(LI,2)
        WRITE(20,1024) UX(LI),UY(LI)
      ENDDO
 1021 FORMAT(I6)
 1022 FORMAT(I8,2I8,2X,2I8)
 1023 FORMAT(8X,F15.7,2F15.7)
 1024 FORMAT(18X,2F15.7)
      CLOSE(20)
!     ======================================================================
!                    WRITE MESH DATA
!     ======================================================================
      WRITE(30,1031) MESH
      DO ME=1,MESH
        WRITE(30,1032) ME,KO(ME),(MENODE(ME,K),K=1,KO(ME))
        WRITE(30,1033) (MELINK(ME,K),K=1,KO(ME))
        WRITE(30,1034) SMESH(ME),XMESH(ME),YMESH(ME)
        WRITE(30,1035) (WEI(ME,K),K=1,KO(ME))
      ENDDO
 1031 FORMAT(I6)
 1032 FORMAT(I8,I5,5X,20I8)
 1033 FORMAT(13X,20I8)
 1034 FORMAT(8X,F15.7,F15.7,1x,F15.7)
 1035 FORMAT(13X,20F15.7)
      CLOSE(30)
!
      STOP
      END
!
!     ******************************************************************
!     ******************************************************************
!     ****                                                          ****
!     ****                       SUBROUTINE                         ****
!     ****                                                          ****
!     ******************************************************************
!     ******************************************************************
!
!     ************************************
!           MESH AND NODE DATA READ       
!     ************************************
      SUBROUTINE RDAT
      IMPLICIT DOUBLE PRECISION (A-H,O-Z)
      PARAMETER(MEG=90000,NOG=50000,LIG=300000,KOG=10)
      COMMON / AA /  KO(MEG),MENODE(MEG,KOG),MELINK(MEG,KOG)
      COMMON / BB /  DNOX(NOG),DNOY(NOG)
      COMMON / ZZ /  MESH,LINK
      integer i,k
!     =====================
!        NODE.DAT READ
!     =====================
      READ(11, *) NODE
      READ(11, *)
      DO NO=1,NODE
        READ(11,*) i, DNOX(NO),DNOY(NO)
      ENDDO
      CLOSE(11)
!     =====================
!        MESHO.DAT READ
!     =====================
      READ(12,1001) MESH
      DO ME=1,MESH
        READ(12,*) k,KO(ME),(MENODE(ME,K),K=1,KO(ME))
      ENDDO
      CLOSE(12)
 1001 FORMAT(6X, I6)
 1002 FORMAT(5X,2F15.5)
 1003 FORMAT(5X,I3,20I6)
!
      RETURN
      END
!     ******************************************************************
!     ************************************
!               MAKE LINK DATA            
!     ************************************
      SUBROUTINE MKLINK
      IMPLICIT DOUBLE PRECISION (A-H,O-Z)
      PARAMETER(MEG=90000,NOG=50000,LIG=300000,KOG=10)
      COMMON / AA /  KO(MEG),MENODE(MEG,KOG),MELINK(MEG,KOG)
      COMMON / CC /  NEIB1(LIG),NEIB2(LIG),LNODE1(LIG),LNODE2(LIG)
      COMMON / ZZ /  MESH,LINK
!
      LINK=1
      DO ME=1,MESH
      DO K=1,KO(ME)
        IF(K.NE.KO(ME)) KK=K+1
        IF(K.EQ.KO(ME)) KK=1
        NO1=MENODE(ME,K)
        NO2=MENODE(ME,KK)
        CALL SEARCH(ME,NO1,NO2)
      ENDDO
      ENDDO
      LINK=LINK-1
!
      RETURN
      END
!     **************************************
      SUBROUTINE SEARCH(ME,NO1,NO2)
      IMPLICIT DOUBLE PRECISION (A-H,O-Z)
      PARAMETER(MEG=90000,NOG=50000,LIG=300000,KOG=10)
      COMMON / AA /  KO(MEG),MENODE(MEG,KOG),MELINK(MEG,KOG)
      COMMON / CC /  NEIB1(LIG),NEIB2(LIG),LNODE1(LIG),LNODE2(LIG)
      COMMON / ZZ /  MESH,LINK
!     ==========================================================
!          COINCIDENCE OF NODE NUMBER ==> THE ADJACENT MESH
!     ==========================================================
      KSW=0
      DO MME=ME+1,MESH
      DO K=1,KO(MME)
         IF(MENODE(MME,K).EQ.NO1) THEN
         DO KK=1,KO(MME)
           IF(MENODE(MME,KK).EQ.NO2) THEN
             NEIB1(LINK)=ME
             NEIB2(LINK)=MME
             LNODE1(LINK)=NO1
             LNODE2(LINK)=NO2
             LINK=LINK+1
             KSW=1
           ENDIF
         ENDDO
         ENDIF
      ENDDO
      ENDDO
!     ==========================================================
!             NONEXISTENCE OF ADJACENT MESH
!                  ==> MEIYO=0 : OUTSIDE LINK
!                  ==> MEIYO=1 : ALREADY DEFINED LINK
!     ==========================================================
      IF(KSW.EQ.0) THEN
        CALL CHECK(NO1,NO2,MEIYO)
        IF(MEIYO.EQ.0) THEN
             NEIB1(LINK)=ME
             NEIB2(LINK)=0
             LNODE1(LINK)=NO1
             LNODE2(LINK)=NO2
             LINK=LINK+1
        ENDIF
      ENDIF
!
      RETURN
      END
!     **************************************
      SUBROUTINE CHECK(NO1,NO2,MEIYO)
      IMPLICIT DOUBLE PRECISION (A-H,O-Z)
      PARAMETER(MEG=90000,NOG=50000,LIG=300000,KOG=10)
      COMMON / CC /  NEIB1(LIG),NEIB2(LIG),LNODE1(LIG),LNODE2(LIG)
      COMMON / ZZ /  MESH,LINK
!
      MEIYO=0
      DO L=1,LINK
        IF(NO1.EQ.LNODE1(L) .AND. NO2.EQ.LNODE2(L)) MEIYO=1
        IF(NO1.EQ.LNODE2(L) .AND. NO2.EQ.LNODE1(L)) MEIYO=1
      ENDDO
!
      RETURN
      END
!     ******************************************************************
!     ************************************
!               MAKE MESH DATA             
!     ************************************
      SUBROUTINE MKMESH
      IMPLICIT DOUBLE PRECISION (A-H,O-Z)
      PARAMETER(MEG=90000,NOG=50000,LIG=300000,KOG=10)
      COMMON / AA /  KO(MEG),MENODE(MEG,KOG),MELINK(MEG,KOG)
      COMMON / BB /  DNOX(NOG),DNOY(NOG)
      COMMON / CC /  NEIB1(LIG),NEIB2(LIG),LNODE1(LIG),LNODE2(LIG)
      COMMON / DD /  SMESH(MEG),XMESH(MEG),YMESH(MEG)
      COMMON / FF /  WEI(MEG,KOG)
      COMMON / ZZ /  MESH,LINK
      DIMENSION S(MEG),WEIGHT(MEG,KOG)
!     ====================================
!                 MELINK DATA
!     ====================================
      DO ME=1,MESH
      DO K=1,KO(ME)
        IF(K.NE.KO(ME)) K2=K+1
        IF(K.EQ.KO(ME)) K2=1
!
        DO LI=1,LINK
        IF((MENODE(ME,K).EQ.LNODE1(LI).AND.MENODE(ME,K2).EQ.LNODE2(LI)) .OR. &
           (MENODE(ME,K).EQ.LNODE2(LI).AND.MENODE(ME,K2).EQ.LNODE1(LI))) THEN
             MELINK(ME,K)=LI
             GOTO 301
        ENDIF
        ENDDO
  301 ENDDO
      ENDDO
!     ====================================
!                  MESH AREA
!     ====================================
      DO ME=1,MESH
            SMESH(ME)=0.0D0
      DO K=1,KO(ME)
            IF(K.NE.KO(ME)) K2=K+1
            IF(K.EQ.KO(ME)) K2=1
            SMESH(ME)=SMESH(ME) &
                 +(DNOY(MENODE(ME,K2))+DNOY(MENODE(ME,K))) &
                 *(DNOX(MENODE(ME,K2))-DNOX(MENODE(ME,K)))/2.0D0
      ENDDO
            SMESH(ME)=ABS(SMESH(ME))
      ENDDO
!     ====================================
!                 MESH CENTROID
!     ====================================
      DO ME=1,MESH
         SUMX=0.0D0
         SUMY=0.0D0
      DO K=1,KO(ME)
         SUMX=SUMX+DNOX(MENODE(ME,K))
         SUMY=SUMY+DNOY(MENODE(ME,K))
      ENDDO
         XMESH(ME)=SUMX/FLOAT(KO(ME))
         YMESH(ME)=SUMY/FLOAT(KO(ME))
      ENDDO
!     ====================================
!       WEIGHT OF EACH LINK ON THE MESH
!     ====================================
      DO ME=1,MESH
        S(ME)=0.0
      DO K=1,KO(ME)
      IF(MELINK(ME,K).EQ.0) GOTO 321
        DX=(DNOX(LNODE1(MELINK(ME,K)))+DNOX(LNODE2(MELINK(ME,K))))/2.0
        DY=(DNOY(LNODE1(MELINK(ME,K)))+DNOY(LNODE2(MELINK(ME,K))))/2.0
        WEIGHT(ME,K)=1.0/SQRT((XMESH(ME)-DX)**2.0+(YMESH(ME)-DY)**2.0)
        S(ME)=S(ME)+WEIGHT(ME,K)
  321 ENDDO
      ENDDO
!
      DO ME=1,MESH
      DO K=1,KO(ME)
        WEI(ME,K)=WEIGHT(ME,K)/S(ME)
      ENDDO
      ENDDO
!
      RETURN
      END
!     ******************************************************************
!     ************************************
!             MAKE EXTRA LINK DATA             
!     ************************************
      SUBROUTINE MKLINK2
      IMPLICIT DOUBLE PRECISION (A-H,O-Z)
      PARAMETER(MEG=90000,NOG=50000,LIG=300000,KOG=10)
      COMMON / BB /  DNOX(NOG),DNOY(NOG)
      COMMON / CC /  NEIB1(LIG),NEIB2(LIG),LNODE1(LIG),LNODE2(LIG)
      COMMON / DD /  SMESH(MEG),XMESH(MEG),YMESH(MEG)
      COMMON / GG /  SCV(LIG),HMRATIO(LIG,2),UX(LIG),UY(LIG)
      COMMON / ZZ /  MESH,LINK
!     ==========================
!        CONTROL VOLUME AREA
!     ==========================
      DO LI=1,LINK
        SCV(LI)=SMESH(NEIB1(LI))+SMESH(NEIB2(LI))
      ENDDO
!     ========================
!     INTERPOLATION LENGTH FOR HM
!     ========================
      DO LI=1,LINK
        XM=(DNOX(LNODE1(LI))+DNOX(LNODE2(LI)))/2.0
        YM=(DNOY(LNODE1(LI))+DNOY(LNODE2(LI)))/2.0
        D1=DSQRT((XMESH(NEIB1(LI))-XM)**2.0+(YMESH(NEIB1(LI))-YM)**2.0)
        D2=DSQRT((XMESH(NEIB2(LI))-XM)**2.0+(YMESH(NEIB2(LI))-YM)**2.0)
        HMRATIO(LI,1)=(1./D1)/(1./D1+1./D2)
        HMRATIO(LI,2)=(1./D2)/(1./D1+1./D2)
      ENDDO
!     =====================
!       UX,UY CALCULATION
!     =====================
      DO LI=1,LINK
        IF(NEIB2(LI).NE.0) THEN
          XX=XMESH(NEIB2(LI))-XMESH(NEIB1(LI))
          YY=YMESH(NEIB2(LI))-YMESH(NEIB1(LI))
          DD=DSQRT(XX**2.0+YY**2.0)
          UX(LI)=XX/DD
          UY(LI)=YY/DD
        ENDIF
      ENDDO
      1021 FORMAT(I6)
!
      RETURN
      END
