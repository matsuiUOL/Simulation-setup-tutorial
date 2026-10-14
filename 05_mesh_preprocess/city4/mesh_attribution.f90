!############################################################
!############################################################
!##                                                        ##
!##    MESH ATTRIBUTION                                    ##
!##    （メッシュの重なりを判断してメッシュに属性を与える）     ##
!##                                                        ##
!##                   Final Editted by   Yoshiki Saito     ##
!############################################################
!############################################################
program mesh_attribution
    implicit none
    integer nocount, mecount
    integer node, mesh, node1, mesh1, node2, mesh2, node3, mesh3, node4, mesh4
    character(5) gomoji
    real   ,save,allocatable ::  dnox(:),dnoy(:)
    real   ,save,allocatable ::  dnox1(:),dnoy1(:)
    real   ,save,allocatable ::  dnox2(:),dnoy2(:)
    real   ,save,allocatable ::  dnox3(:),dnoy3(:)
    real   ,save,allocatable ::  dnox4(:),dnoy4(:)
    integer,save,allocatable ::  menode(:,:),mark(:)
    integer,save,allocatable ::  menode1(:,:),menode2(:,:), menode3(:,:), menode4(:,:)
    real(8),allocatable :: xg(:),yg(:)
    integer no, me, i, k, m, n
    real(8) s, t
    real(8) xba, xca, xga, yba, yca, yga
    integer count1, count2, count3, count4
    !No.11:全メッシュ(属性分けを行うメッシュ)
    open(11,file='city4_after_all.msh', status='old')
    !No.12:道路のみメッシュ(属性１のみのメッシュ)
    open(12,file='city4_road.msh',status='old')
    !No.13:建物のみメッシュ（属性２のみのメッシュ）
    open(13,file='city4_building.msh',status='old')
    !No.14:河川のみメッシュ（属性３のみのメッシュ）
    open(14,file='city4_river.msh',status='old')
    !No.13:その他のみメッシュ（属性４のみのメッシュ）
    open(15,file='city4_others.msh',status='old')


    !出力ファイル
    open(21,file='node.dat')  !各ノードの座標を書き込む
    open(22,file='mesho.dat') !各メッシュの構成ノードを書き込む
    open(23,file='centroid.dat') !各メッシュの重心座標を書き込む
    open(24,file='inf.dat')

    !######################################
    !       File No.11 の読み取り
    !######################################
    !#### ノード数とメッシュ数の読み取り ####
    nocount = 0
    mecount = 0
    read(11,*)
    read(11,*)
    do
        nocount = nocount + 1
        read(11,'(a5)') gomoji
        if(gomoji == 'End C')exit   ! [End Coordinates]を読んだら、そこまでカウントした数字をノード数とする
    enddo
        node = nocount - 1
        write(21, *)node
        write(21, *)
        write(*, 1101)node
    read(11,*)
    read(11,*)
    do 
        mecount = mecount + 1
        read(11,'(a5)') gomoji
        if(gomoji == 'End E')exit   ! [End Elements]を読んだら、そこまでカウントした数字をメッシュ数とする
    enddo
        mesh = mecount - 1
        write(22,1102)mesh
        write(*, 1102)mesh
    !#### ノード座標とメッシュ構成ノードの書き込み ####
    rewind(11)
    read(11,*)
    read(11,*)
    allocate(dnox(node),dnoy(node))
    allocate(menode(mesh,3),mark(mesh))
    allocate(xg(mesh),yg(mesh))
    do no = 1, node
        read(11,*) i, dnox(no), dnoy(no)
        write(21,1103) no, dnox(no), dnoy(no)
    enddo
    read(11,*)
    read(11,*)
    read(11,*)
    do me = 1, mesh
        read(11,*) i, (menode(me,k),k=1,3)
        write(22,1104) me, 3, (menode(me,k),k=1,3)
    enddo
    !#### メッシュの重心座標の算出＆書き込み ####
    write(23,1102)mesh
    do me = 1, mesh
        xg(me) = (dnox(menode(me,1)) + dnox(menode(me,2)) + dnox(menode(me,3))) /3.0
        yg(me) = (dnoy(menode(me,1)) + dnoy(menode(me,2)) + dnoy(menode(me,3))) /3.0
        write(23,1103) me, xg(me), yg(me)
    enddo
    !#### 初期属性を４とする ####
    do me = 1, mesh
        mark(me) = 4
    enddo
    !######################################
    !    File No.12 の読み取り（属性１）
    !######################################
    !#### ノード数とメッシュ数の読み取り ####
    nocount = 0
    mecount = 0
    read(12,*)
    read(12,*)
    do
        nocount = nocount + 1
        read(12,'(a5)') gomoji
        if(gomoji == 'End C')exit   ! [End Coordinates]を読んだら、そこまでカウントした数字をノード数とする
    enddo
        node1 = nocount - 1
    read(12,*)
    read(12,*)
    do 
        mecount = mecount + 1
        read(12,'(a5)') gomoji
        if(gomoji == 'End E')exit   ! [End Elements]を読んだら、そこまでカウントした数字をメッシュ数とする
    enddo
        mesh1 = mecount - 1
    !#### ノード座標とメッシュ構成ノードの読み取り ####
    rewind(12)
    read(12,*)
    read(12,*)
    allocate(dnox1(node1),dnoy1(node1))
    allocate(menode1(mesh1,3))
    do no = 1, node1
        read(12,*) i, dnox1(no), dnoy1(no)
    enddo
    read(12,*)
    read(12,*)
    read(12,*)
    do me = 1, mesh1
        read(12,*) i, (menode1(me,k),k=1,3)
    enddo
    !#### menode1の座標と重心座標を比較 ####
    !メッシュ内に含まれていれば属性２を与える
    do n = 1, mesh1
    do m = 1, mesh
        xba = dnox1(menode1(n,2)) - dnox1(menode1(n,1))
        xca = dnox1(menode1(n,3)) - dnox1(menode1(n,1))
        yba = dnoy1(menode1(n,2)) - dnoy1(menode1(n,1))
        yca = dnoy1(menode1(n,3)) - dnoy1(menode1(n,1))
        xga = xg(m) - dnox1(menode1(n,1))
        yga = yg(m) - dnoy1(menode1(n,1))
        s = ((xca*yga)-(xga*yca)) / ((xca*yba)-(xba*yca))
        t = ((xba*yga)-(xga*yba)) / ((xba*yca)-(xca*yba))
        if((s>=0).and.(s<=1))then
        if((t>=0).and.(t<=1))then
            if((s+t>=0).and.(s+t<=1))then
                mark(m) = 1
            endif
        endif
        endif
    enddo
    enddo
    !######################################
    !    File No.13 の読み取り（属性２）
    !######################################
    !#### ノード数とメッシュ数の読み取り ####
    nocount = 0
    mecount = 0
    read(13,*)
    read(13,*)
    do
        nocount = nocount + 1
        read(13,'(a5)') gomoji
        if(gomoji == 'End C')exit   ! [End Coordinates]を読んだら、そこまでカウントした数字をノード数とする
    enddo
        node2 = nocount - 1
    read(13,*)
    read(13,*)
    do 
        mecount = mecount + 1
        read(13,'(a5)') gomoji
        if(gomoji == 'End E')exit   ! [End Elements]を読んだら、そこまでカウントした数字をメッシュ数とする
    enddo
        mesh2 = mecount - 1
    !#### ノード座標とメッシュ構成ノードの読み取り ####
    rewind(13)
    read(13,*)
    read(13,*)
    allocate(dnox2(node2),dnoy2(node2))
    allocate(menode2(mesh2,3))
    do no = 1, node2
        read(13,*) i, dnox2(no), dnoy2(no)
    enddo
    read(13,*)
    read(13,*)
    read(13,*)
    do me = 1, mesh2
        read(13,*) i, (menode2(me,k),k=1,3)
    enddo
    !#### menode1の座標と重心座標を比較 ####
    !メッシュ内に含まれていれば属性２を与える
    do n = 1, mesh2
    do m = 1, mesh
        xba = dnox2(menode2(n,2)) - dnox2(menode2(n,1))
        xca = dnox2(menode2(n,3)) - dnox2(menode2(n,1))
        yba = dnoy2(menode2(n,2)) - dnoy2(menode2(n,1))
        yca = dnoy2(menode2(n,3)) - dnoy2(menode2(n,1))
        xga = xg(m) - dnox2(menode2(n,1))
        yga = yg(m) - dnoy2(menode2(n,1))
        s = ((xca*yga)-(xga*yca)) / ((xca*yba)-(xba*yca))
        t = ((xba*yga)-(xga*yba)) / ((xba*yca)-(xca*yba))
        if((s>=0).and.(s<=1))then
        if((t>=0).and.(t<=1))then
            if((s+t>=0).and.(s+t<=1))then
                mark(m) = 2
            endif
        endif
        endif
    enddo
    enddo
    !######################################
    !    File No.14 の読み取り（属性３）
    !######################################
    !#### ノード数とメッシュ数の読み取り ####
    nocount = 0
    mecount = 0
    read(14,*)
    read(14,*)
    do
        nocount = nocount + 1
        read(14,'(a5)') gomoji
        if(gomoji == 'End C')exit   ! [End Coordinates]を読んだら、そこまでカウントした数字をノード数とする
    enddo
        node3 = nocount - 1
    read(14,*)
    read(14,*)
    do 
        mecount = mecount + 1
        read(14,'(a5)') gomoji
        if(gomoji == 'End E')exit   ! [End Elements]を読んだら、そこまでカウントした数字をメッシュ数とする
    enddo
        mesh3 = mecount - 1
    !#### ノード座標とメッシュ構成ノードの読み取り ####
    rewind(14)
    read(14,*)
    read(14,*)
    allocate(dnox3(node3),dnoy3(node3))
    allocate(menode3(mesh3,3))
    do no = 1, node3
        read(14,*) i, dnox3(no), dnoy3(no)
    enddo
    read(14,*)
    read(14,*)
    read(14,*)
    do me = 1, mesh3
        read(14,*) i, (menode3(me,k),k=1,3)
    enddo
    !#### menode3の座標と重心座標を比較 ####
    !メッシュ内に含まれていれば属性３を与える
    do n = 1, mesh3
    do m = 1, mesh
        xba = dnox3(menode3(n,2)) - dnox3(menode3(n,1))
        xca = dnox3(menode3(n,3)) - dnox3(menode3(n,1))
        yba = dnoy3(menode3(n,2)) - dnoy3(menode3(n,1))
        yca = dnoy3(menode3(n,3)) - dnoy3(menode3(n,1))
        xga = xg(m) - dnox3(menode3(n,1))
        yga = yg(m) - dnoy3(menode3(n,1))
        s = ((xca*yga)-(xga*yca)) / ((xca*yba)-(xba*yca))
        t = ((xba*yga)-(xga*yba)) / ((xba*yca)-(xca*yba))
        if((s>=0).and.(s<=1))then
        if((t>=0).and.(t<=1))then
            if((s+t>=0).and.(s+t<=1))then
                mark(m) = 3
            endif
        endif
        endif
    enddo
    enddo
    !######################################
    !    File No.15 の読み取り（属性４）
    !######################################
    !#### ノード数とメッシュ数の読み取り ####
    nocount = 0
    mecount = 0
    read(15,*)
    read(15,*)
    do
        nocount = nocount + 1
        read(15,'(a5)') gomoji
        if(gomoji == 'End C')exit   ! [End Coordinates]を読んだら、そこまでカウントした数字をノード数とする
    enddo
        node4 = nocount - 1
    read(15,*)
    read(15,*)
    do 
        mecount = mecount + 1
        read(15,'(a5)') gomoji
        if(gomoji == 'End E')exit   ! [End Elements]を読んだら、そこまでカウントした数字をメッシュ数とする
    enddo
        mesh4 = mecount - 1
    !#### ノード座標とメッシュ構成ノードの読み取り ####
    rewind(15)
    read(15,*)
    read(15,*)
    allocate(dnox4(node4),dnoy4(node4))
    allocate(menode4(mesh4,3))
    do no = 1, node4
        read(15,*) i, dnox4(no), dnoy4(no)
    enddo
    read(15,*)
    read(15,*)
    read(15,*)
    do me = 1, mesh4
        read(15,*) i, (menode4(me,k),k=1,3)
    enddo
    !#### menode4の座標と重心座標を比較 ####
    !メッシュ内に含まれていれば属性４を与える
    do n = 1, mesh4
    do m = 1, mesh
        xba = dnox4(menode4(n,2)) - dnox4(menode4(n,1))
        xca = dnox4(menode4(n,3)) - dnox4(menode4(n,1))
        yba = dnoy4(menode4(n,2)) - dnoy4(menode4(n,1))
        yca = dnoy4(menode4(n,3)) - dnoy4(menode4(n,1))
        xga = xg(m) - dnox4(menode4(n,1))
        yga = yg(m) - dnoy4(menode4(n,1))
        s = ((xca*yga)-(xga*yca)) / ((xca*yba)-(xba*yca))
        t = ((xba*yga)-(xga*yba)) / ((xba*yca)-(xca*yba))
        if((s>=0).and.(s<=1))then
        if((t>=0).and.(t<=1))then
            if((s+t>=0).and.(s+t<=1))then
                mark(m) = 4
            endif
        endif
        endif
    enddo
    enddo
    !######################################
    !    得られた属性の書き込み
    !######################################
    !ファイルへの書き込み
        write(24, *)
        write(24, *)
    do me = 1, mesh
        write(24,1105) me, mark(me)
    enddo
    !ディスプレイに個数を表示
    count1 = 0
    count2 = 0
    count3 = 0
    count4 = 0
    do me = 1, mesh
        if(mark(me) == 1) count1 = count1 + 1
        if(mark(me) == 2) count2 = count2 + 1
        if(mark(me) == 3) count3 = count3 + 1
        if(mark(me) == 4) count4 = count4 + 1
    enddo
    write(*,*)'mark:1 = ', count1
    write(*,*)'mark:2 = ', count2
    write(*,*)'mark:3 = ', count3
    write(*,*)'mark:4 = ', count4

1101 format('NODE = ',i5)
1102 format('MESH = ',i5)
1103 format(i5,2f15.5)
1104 format(i5,i3,5x,3i6)
1105 format(2i5)

end program
