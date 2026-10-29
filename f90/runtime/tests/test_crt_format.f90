! test_crt_format.f90 - replays gen_ref's glibc reference stream through crt_format.
! Written by Claude (Anthropic); see AI-USE.md.
!
! Reads the chunked record stream written by gen_ref.c (file named on the command line), runs every case
! through c_format / c_sscanf / c_strtod and compares with glibc byte for byte (sscanf:
! return value and every target; strtod: value bits and consumed length).
! Prints per-format and per-category totals and the first mismatches of each kind.
! Exit status 0 when there are no mismatches, 1 otherwise.
program test_crt_format
  use iso_fortran_env, only: int8, int16, int32, int64, real32, real64, output_unit
  use crt_base
  use crt_format
  implicit none

  type box
     class(*), allocatable :: v
  end type box
  type fstring
     character(len=:), allocatable :: s
  end type fstring

  integer, parameter :: MAXF = 2048, MAXSHOW = 4
  type(fstring) :: fname(0:MAXF-1)
  type(CPtr) :: fmtp(0:MAXF-1)
  character :: fcat(0:MAXF-1)
  integer(int64) :: ntest(0:MAXF-1), nbad(0:MAXF-1)
  integer :: nshow(0:MAXF-1)
  integer(int64) :: rhist(-1:12, 0:MAXF-1)
  integer :: gn(0:7), gid(128, 0:7)
  integer(int64) :: dn(0:15), dbad(0:15), gtot(0:7), gbad(0:7)
  integer :: dshow(0:15)
  character(len=24), parameter :: DCLASS(0:7) = [character(len=24) :: '?', 'random decimal', &
       'double halfway +/-', 'special spellings', 'hex floats', 'subnormal/boundary', &
       'long digit strings', 'short junk']

  integer(int8), allocatable :: ck(:), out(:)
  integer(int8), target, save :: sbuf(0:4095, 20), tbuf(0:255, 12), inbuf(0:8191)
  type(box) :: bx(20)
  integer :: cpos, u, ios, k, id, grp, cnt, n, l, na, t, nt, i, ret, rgot
  integer(int32) :: n32, v32
  integer(int64) :: bits, v64, nc, cons
  real(real64) :: x
  logical :: finished, bad
  character(len=:), allocatable :: ctx
  integer(int64) :: totp, badp, tots, bads, totd, badd
  character(len=4096) :: refname

  ntest = 0
  nbad = 0
  nshow = 0
  rhist = 0
  gn = 0
  dn = 0
  dbad = 0
  dshow = 0
  gtot = 0
  gbad = 0
  fcat = ' '
  finished = .false.

  call get_command_argument(1, refname, status=ios)
  if (ios /= 0 .or. len_trim(refname) == 0) refname = '/dev/stdin'
  open(newunit=u, file=trim(refname), access='stream', form='unformatted', action='read', &
       status='old', iostat=ios)
  if (ios /= 0) stop 'cannot open the reference stream'
  allocate(ck(4 * 1024 * 1024))

  do
     read(u, iostat=ios) n32
     if (ios /= 0) then
        print '(a)', 'ERROR: reference stream ended without an end record'
        exit
     end if
     if (n32 == 0) exit
     if (size(ck) < n32) then
        deallocate(ck)
        allocate(ck(n32))
     end if
     read(u, iostat=ios) ck(1:n32)
     if (ios /= 0) stop 'short chunk'
     cpos = 1
     do while (cpos <= n32)
        t = g8()
        select case (t)
        case (70)                               ! 'F'
           id = g16()
           l = g16()
           allocate(character(len=l) :: fname(id)%s)
           do i = 1, l
              fname(id)%s(i:i) = achar(iand(int(ck(cpos + i - 1)), 255))
           end do
           fmtp(id) = cbuf(int(l + 1, int64))
           if (l > 0) fmtp(id)%b(0:l-1) = ck(cpos:cpos+l-1)
           cpos = cpos + l
        case (72)                               ! 'H'
           grp = g8()
           cnt = g16()
           gn(grp) = cnt
           do k = 1, cnt
              gid(k, grp) = g16()
           end do
        case (86)                               ! 'V'
           grp = g8()
           bits = g64()
           x = transfer(bits, x)
           do k = 1, gn(grp)
              id = gid(k, grp)
              l = g16()
              call c_format(fmtp(id), out, n, x)
              call check_out(id, 'p', l, n, grp, 'value bits=' // hex64(bits))
              cpos = cpos + l
           end do
        case (73)                               ! 'I'
           grp = g8()
           na = g8()
           v64 = g64()
           do k = 1, gn(grp)
              id = gid(k, grp)
              l = g16()
              if (na == 1) then
                 v32 = int(v64, int32)
                 call c_format(fmtp(id), out, n, v32)
                 call check_out(id, 'p', l, n, grp, 'int32 value=' // itoa(v64))
              else
                 call c_format(fmtp(id), out, n, v64)
                 call check_out(id, 'p', l, n, grp, 'int64 value=' // itoa(v64))
              end if
              cpos = cpos + l
           end do
        case (80)                               ! 'P'
           id = g16()
           na = g8()
           ctx = 'args:'
           do k = 1, na
              t = g8()
              select case (t)
              case (1)
                 v32 = g32()
                 allocate(bx(k)%v, source=v32)
                 ctx = ctx // ' i32 ' // itoa(int(v32, int64))
              case (2)
                 v64 = g64()
                 allocate(bx(k)%v, source=v64)
                 ctx = ctx // ' i64 ' // itoa(v64)
              case (3)
                 bits = g64()
                 allocate(bx(k)%v, source=transfer(bits, x))
                 ctx = ctx // ' dbl ' // hex64(bits)
              case (4)
                 l = g16()
                 if (l == 65535) then
                    allocate(bx(k)%v, source=cnull())
                    ctx = ctx // ' NULL'
                 else
                    if (l > 0) sbuf(0:l-1, k) = ck(cpos:cpos+l-1)
                    sbuf(l, k) = 0
                    allocate(bx(k)%v, source=colptr(sbuf, k))
                    ctx = ctx // ' "' // esc(ck(cpos:cpos+l-1), l) // '"'
                    cpos = cpos + l
                 end if
              end select
           end do
           call c_format(fmtp(id), out, n, bx(1)%v, bx(2)%v, bx(3)%v, bx(4)%v, bx(5)%v, &
                bx(6)%v, bx(7)%v, bx(8)%v, bx(9)%v, bx(10)%v, bx(11)%v, bx(12)%v, bx(13)%v, &
                bx(14)%v, bx(15)%v, bx(16)%v, bx(17)%v, bx(18)%v, bx(19)%v, bx(20)%v)
           l = g32()
           call check_out(id, 'p', l, n, 7, ctx)
           cpos = cpos + l
           do k = 1, na
              deallocate(bx(k)%v)
           end do
        case (83)                               ! 'S'
           call do_sscanf()
        case (68)                               ! 'D'
           call do_strtod()
        case (69)                               ! 'E'
           finished = .true.
        case default
           print '(a,i0)', 'ERROR: bad record type ', t
           stop 2
        end select
     end do
  end do

  ! ------------------------------------------------------------------ report
  totp = 0
  badp = 0
  tots = 0
  bads = 0
  print '(a)', ''
  print '(a)', '==== printf (c_format vs glibc snprintf) ===='
  print '(a12,a12,2x,a)', 'cases', 'mismatches', 'format'
  do id = 0, MAXF - 1
     if (fcat(id) /= 'p') cycle
     print '(i12,i12,2x,a)', ntest(id), nbad(id), '"' // escs(fname(id)%s) // '"'
     totp = totp + ntest(id)
     badp = badp + nbad(id)
  end do
  print '(a)', ''
  print '(a)', '==== sscanf (c_sscanf vs glibc sscanf: return value and every target) ===='
  print '(a12,a12,2x,a,t60,a)', 'cases', 'mismatches', 'format', &
       'glibc return values seen: count[ret]'
  do id = 0, MAXF - 1
     if (fcat(id) /= 's') cycle
     ctx = ''
     do k = -1, 12
        if (rhist(k, id) > 0) ctx = ctx // ' ' // itoa(rhist(k, id)) // '[' // itoa(int(k, int64)) // ']'
     end do
     print '(i12,i12,2x,a,t60,a)', ntest(id), nbad(id), '"' // escs(fname(id)%s) // '"', ctx
     tots = tots + ntest(id)
     bads = bads + nbad(id)
  end do
  print '(a)', ''
  print '(a)', '==== strtod (c_strtod vs glibc strtod: value bits and consumed length) ===='
  totd = 0
  badd = 0
  do k = 1, 7
     print '(i12,i12,2x,a)', dn(k), dbad(k), trim(DCLASS(k))
     totd = totd + dn(k)
     badd = badd + dbad(k)
  end do
  print '(a)', ''
  print '(a)', '==== totals ===='
  print '(a,i0,a,i0)', 'printf  group 0 (19 required double formats): cases ', gtot(0), &
       '  mismatches ', gbad(0)
  print '(a,i0,a,i0)', 'printf  group 1 (extra double formats):        cases ', gtot(1), &
       '  mismatches ', gbad(1)
  print '(a,i0,a,i0)', 'printf  group 2 (integer formats):             cases ', gtot(2), &
       '  mismatches ', gbad(2)
  print '(a,i0,a,i0)', 'printf  strings/chars/stars/mixed/oddities:    cases ', gtot(7), &
       '  mismatches ', gbad(7)
  print '(a,i0,a,i0)', 'printf  all:  cases ', totp, '  mismatches ', badp
  print '(a,i0,a,i0)', 'sscanf  all:  cases ', tots, '  mismatches ', bads
  print '(a,i0,a,i0)', 'strtod  all:  cases ', totd, '  mismatches ', badd
  if (.not. finished) print '(a)', 'ERROR: stream incomplete'
  if (badp + bads + badd == 0 .and. finished) then
     print '(a)', 'RESULT: PASS (0 mismatches)'
  else
     print '(a)', 'RESULT: FAIL'
     error stop 1
  end if

contains

  integer function g8()
    g8 = iand(int(ck(cpos)), 255)
    cpos = cpos + 1
  end function g8

  integer function g16()
    g16 = iand(int(ck(cpos)), 255) + 256 * iand(int(ck(cpos + 1)), 255)
    cpos = cpos + 2
  end function g16

  integer(int32) function g32()
    g32 = transfer(ck(cpos:cpos+3), 0_int32)
    cpos = cpos + 4
  end function g32

  integer(int64) function g64()
    g64 = transfer(ck(cpos:cpos+7), 0_int64)
    cpos = cpos + 8
  end function g64

  function colptr(arr, col) result(p)
    integer(int8), target, intent(in) :: arr(0:, :)
    integer, intent(in) :: col
    type(CPtr) :: p
    p%b(0:size(arr, 1) - 1) => arr(:, col)
    p%o = 0
  end function colptr

  function hex64(v) result(s)
    integer(int64), intent(in) :: v
    character(len=18) :: s
    write(s, '(a,z16.16)') '0x', v
  end function hex64

  function itoa(v) result(s)
    integer(int64), intent(in) :: v
    character(len=:), allocatable :: s
    character(len=24) :: t
    write(t, '(i0)') v
    s = trim(t)
  end function itoa

  function esc(b, n) result(s)
    integer(int8), intent(in) :: b(:)
    integer, intent(in) :: n
    character(len=:), allocatable :: s
    character(len=4) :: t
    integer :: i, c
    s = ''
    do i = 1, n
       c = iand(int(b(i)), 255)
       if (c == 92) then
          s = s // '\\'
       else if (c >= 32 .and. c < 127) then
          s = s // achar(c)
       else
          write(t, '(a,z2.2)') '\x', c
          s = s // t
       end if
    end do
  end function esc

  function escs(str) result(s)
    character(len=*), intent(in) :: str
    character(len=:), allocatable :: s
    integer(int8) :: b(len(str))
    integer :: i
    do i = 1, len(str)
       b(i) = int(ichar(str(i:i)) - merge(256, 0, ichar(str(i:i)) > 127), int8)
    end do
    s = esc(b, len(str))
  end function escs

  !> compare out(1:n) with the expected bytes ck(cpos:cpos+l-1)
  subroutine check_out(fid, cat, l, n, grp, why)
    integer, intent(in) :: fid, l, n, grp
    character, intent(in) :: cat
    character(len=*), intent(in) :: why
    logical :: same
    fcat(fid) = cat
    ntest(fid) = ntest(fid) + 1
    gtot(grp) = gtot(grp) + 1
    same = l == n
    if (same .and. l > 0) same = all(out(1:n) == ck(cpos:cpos+l-1))
    if (same) return
    nbad(fid) = nbad(fid) + 1
    gbad(grp) = gbad(grp) + 1
    if (nshow(fid) >= MAXSHOW) return
    nshow(fid) = nshow(fid) + 1
    print '(a)', 'MISMATCH printf "' // escs(fname(fid)%s) // '" ' // why
    print '(a)', '   glibc: "' // esc(ck(cpos:), l) // '"'
    print '(a)', '   ours : "' // esc(out, n) // '"'
  end subroutine check_out

  subroutine do_sscanf()
    integer :: fid, inl, k2, tt(16), j, m
    integer(int64) :: e64(16)
    integer :: el(16), epos(16)
    type(CPtr) :: inp
    character(len=:), allocatable :: why
    integer(int64) :: g
    logical :: sbad
    fid = g16()
    inl = g16()
    if (inl > 0) inbuf(0:inl-1) = ck(cpos:cpos+inl-1)
    inbuf(inl) = 0
    inp%b(0:size(inbuf) - 1) => inbuf
    inp%o = 0
    why = 'input "' // esc(ck(cpos:), inl) // '"'
    cpos = cpos + inl
    ret = g32()
    nt = g8()
    do k2 = 1, nt
       tt(k2) = g8()
       select case (tt(k2))
       case (1)
          e64(k2) = g32()
          allocate(bx(k2)%v, source=1515870810_int32)
       case (2)
          e64(k2) = g64()
          allocate(bx(k2)%v, source=6510615555426900570_int64)
       case (3)
          e64(k2) = g64()
          allocate(bx(k2)%v, source=transfer(6510615555426900570_int64, 0.0_real64))
       case (5)
          e64(k2) = g32()
          allocate(bx(k2)%v, source=transfer(1515870810_int32, 0.0_real32))
       case (6)
          e64(k2) = g8()
          if (e64(k2) > 127) e64(k2) = e64(k2) - 256
          allocate(bx(k2)%v, source=90_int32)
       case (7)
          e64(k2) = g16()
          if (e64(k2) > 32767) e64(k2) = e64(k2) - 65536
          allocate(bx(k2)%v, source=23130_int16)
       case (8)
          e64(k2) = g8()
          if (e64(k2) > 127) e64(k2) = e64(k2) - 256
          allocate(bx(k2)%v, source=90_int8)
       case (4)
          el(k2) = g16()
          epos(k2) = cpos
          cpos = cpos + el(k2)
          tbuf(0:254, k2) = 90
          tbuf(255, k2) = 0
          allocate(bx(k2)%v, source=colptr(tbuf, k2))
       end select
    end do
    rgot = c_sscanf(inp, fmtp(fid), bx(1)%v, bx(2)%v, bx(3)%v, bx(4)%v, bx(5)%v, bx(6)%v, &
         bx(7)%v, bx(8)%v, bx(9)%v, bx(10)%v, bx(11)%v, bx(12)%v)
    bad = rgot /= ret
    if (bad) why = why // ' return glibc ' // itoa(int(ret, int64)) // ' ours ' // itoa(int(rgot, int64))
    do k2 = 1, nt
       select case (tt(k2))
       case (4)
          m = 0
          do while (m < 255)
             if (tbuf(m, k2) == 0) exit
             m = m + 1
          end do
          sbad = m /= el(k2)
          if (.not. sbad .and. m > 0) sbad = any(tbuf(0:m-1, k2) /= ck(epos(k2):epos(k2)+m-1))
          if (sbad) bad = .true.
          if (sbad) why = why // ' | t' // itoa(int(k2, int64)) // ' glibc "' // &
               esc(ck(epos(k2):), el(k2)) // '" ours "' // esc(tbuf(:, k2), m) // '"'
       case default
          select type (q => bx(k2)%v)
          type is (integer(int32))
             g = q
          type is (integer(int64))
             g = q
          type is (integer(int16))
             g = q
          type is (integer(int8))
             g = q
          type is (real(real64))
             g = transfer(q, 0_int64)
          type is (real(real32))
             g = transfer(q, 0_int32)
          class default
             g = -999
          end select
          if (g /= e64(k2)) then
             bad = .true.
             why = why // ' | t' // itoa(int(k2, int64)) // ' glibc ' // itoa(e64(k2)) // &
                  ' ours ' // itoa(g)
          end if
       end select
    end do
    do j = 1, nt
       deallocate(bx(j)%v)
    end do
    fcat(fid) = 's'
    ntest(fid) = ntest(fid) + 1
    if (ret >= -1 .and. ret <= 12) rhist(ret, fid) = rhist(ret, fid) + 1
    if (.not. bad) return
    nbad(fid) = nbad(fid) + 1
    if (nshow(fid) >= MAXSHOW) return
    nshow(fid) = nshow(fid) + 1
    print '(a)', 'MISMATCH sscanf "' // escs(fname(fid)%s) // '" ' // why
  end subroutine do_sscanf

  subroutine do_strtod()
    integer :: cls, sl
    type(CPtr) :: sp
    real(real64) :: d
    integer(int64) :: gb
    cls = g8()
    sl = g16()
    if (sl > 0) inbuf(0:sl-1) = ck(cpos:cpos+sl-1)
    inbuf(sl) = 0
    sp%b(0:size(inbuf) - 1) => inbuf
    sp%o = 0
    cpos = cpos + sl
    bits = g64()
    cons = g32()
    d = c_strtod(sp, nc)
    gb = transfer(d, 0_int64)
    dn(cls) = dn(cls) + 1
    if (gb == bits .and. nc == cons) return
    dbad(cls) = dbad(cls) + 1
    if (dshow(cls) >= 6) return
    dshow(cls) = dshow(cls) + 1
    print '(a)', 'MISMATCH strtod "' // esc(inbuf, min(sl, 200)) // '" glibc ' // hex64(bits) // &
         ' n=' // itoa(cons) // ' ours ' // hex64(gb) // ' n=' // itoa(nc)
  end subroutine do_strtod

end program test_crt_format
