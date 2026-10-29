! crt_io.f90 - the slice of the C library that EPA SWMM 5.2.4 uses, for the Fortran port:
! FILE streams (byte-exact, buffered, with C's fseek/ftell/feof semantics), the string
! functions, number conversions with x86 semantics, the math functions with libm's exact
! results, and time.  Formatting (printf/scanf/strtod) lives in crt_format.f90.
! Written by Claude (Anthropic); see AI-USE.md.
module crt_io
  use iso_fortran_env, only: int8, int32, int64, real32, real64, output_unit
  use crt_base
  use iso_c_binding, only: c_double
  use crt_format
  implicit none

  integer(int64), parameter :: MASK32 = 4294967295_int64
  integer(int64), parameter :: IOBUF = 65536

  !> C FILE: a Fortran stream unit plus our own read/write buffers and position
  type :: CFile
     integer :: unit = -1             ! gfortran's NEWUNIT numbers are negative
     logical :: is_open = .false.
     logical :: is_stdout = .false.
     logical :: can_read = .false., can_write = .false.
     integer(int64) :: pos = 0       ! logical position, 0-based
     integer(int64) :: fsize = 0     ! file size including unflushed writes
     logical :: eof = .false.
     integer(int8), allocatable :: wbuf(:)
     integer(int64) :: wstart = 0, wlen = 0
     integer(int8), allocatable :: rbuf(:)
     integer(int64) :: rstart = 0, rlen = 0
  end type CFile

  type(CFile), pointer :: c_stdout => null()

  ! scratch buffer for formatted output
  integer(int8), allocatable, save, private :: fmtbuf(:)
  ! strtok state
  type(CPtr), save, private :: tok_next
  ! ctime result buffer
  integer(int8), target, save, private :: ctime_buf(0:31) = 0_int8

  interface
     ! libm functions whose results the C engine depends on bit for bit
     pure real(c_double) function libm_pow(x, y) bind(C, name='pow')
       import :: c_double
       real(c_double), value :: x, y
     end function
     pure real(c_double) function libm_floor(x) bind(C, name='floor')
       import :: c_double
       real(c_double), value :: x
     end function
     pure real(c_double) function libm_ceil(x) bind(C, name='ceil')
       import :: c_double
       real(c_double), value :: x
     end function
     pure real(c_double) function libm_exp(x) bind(C, name='exp')
       import :: c_double
       real(c_double), value :: x
     end function
     pure real(c_double) function libm_log(x) bind(C, name='log')
       import :: c_double
       real(c_double), value :: x
     end function
     pure real(c_double) function libm_log10(x) bind(C, name='log10')
       import :: c_double
       real(c_double), value :: x
     end function
     pure real(c_double) function libm_sin(x) bind(C, name='sin')
       import :: c_double
       real(c_double), value :: x
     end function
     pure real(c_double) function libm_cos(x) bind(C, name='cos')
       import :: c_double
       real(c_double), value :: x
     end function
     pure real(c_double) function libm_tan(x) bind(C, name='tan')
       import :: c_double
       real(c_double), value :: x
     end function
     pure real(c_double) function libm_asin(x) bind(C, name='asin')
       import :: c_double
       real(c_double), value :: x
     end function
     pure real(c_double) function libm_acos(x) bind(C, name='acos')
       import :: c_double
       real(c_double), value :: x
     end function
     pure real(c_double) function libm_atan(x) bind(C, name='atan')
       import :: c_double
       real(c_double), value :: x
     end function
  end interface

contains

  ! ===================================================================== numbers

  !> (int)x with x86 cvttsd2si semantics: NaN and out-of-range give INT_MIN
  elemental integer(int32) function d2i(x)
    real(dp), intent(in) :: x
    if (x /= x .or. x >= 2147483648.0_dp .or. x <= -2147483649.0_dp) then
       d2i = -2147483647 - 1
    else
       d2i = int(x, int32)
    end if
  end function d2i

  elemental integer(int32) function f2i(x)
    real(sp), intent(in) :: x
    f2i = d2i(real(x, dp))
  end function f2i

  !> (long)x, cvttsd2si 64-bit
  elemental integer(int64) function d2l(x)
    real(dp), intent(in) :: x
    if (x /= x .or. x >= 9223372036854775808.0_dp .or. x < -9223372036854775808.0_dp) then
       d2l = -9223372036854775807_int64 - 1
    else
       d2l = int(x, int64)
    end if
  end function d2l

  !> unsigned int held in an int64 -> int (two's complement)
  elemental integer(int32) function u2i(x)
    integer(int64), intent(in) :: x
    integer(int64) :: w
    w = iand(x, MASK32)
    if (w > 2147483647_int64) w = w - 4294967296_int64
    u2i = int(w, int32)
  end function u2i

  !> int -> unsigned int (held in int64)
  elemental integer(int64) function i2u(x)
    integer(int64), intent(in) :: x
    i2u = iand(x, MASK32)
  end function i2u

  elemental integer(int32) function b2i(b)
    logical, intent(in) :: b
    if (b) then
       b2i = 1
    else
       b2i = 0
    end if
  end function b2i

  real(dp) function cpow(x, y)
    real(dp), intent(in) :: x, y
    cpow = libm_pow(x, y)
  end function cpow
  real(dp) function cfloor(x)
    real(dp), intent(in) :: x
    cfloor = libm_floor(x)
  end function cfloor
  real(dp) function cceil(x)
    real(dp), intent(in) :: x
    cceil = libm_ceil(x)
  end function cceil
  real(dp) function cexp(x)
    real(dp), intent(in) :: x
    cexp = libm_exp(x)
  end function cexp
  real(dp) function clog(x)
    real(dp), intent(in) :: x
    clog = libm_log(x)
  end function clog
  real(dp) function clog10(x)
    real(dp), intent(in) :: x
    clog10 = libm_log10(x)
  end function clog10
  real(dp) function csin(x)
    real(dp), intent(in) :: x
    csin = libm_sin(x)
  end function csin
  real(dp) function ccos(x)
    real(dp), intent(in) :: x
    ccos = libm_cos(x)
  end function ccos
  real(dp) function ctan(x)
    real(dp), intent(in) :: x
    ctan = libm_tan(x)
  end function ctan
  real(dp) function casin(x)
    real(dp), intent(in) :: x
    casin = libm_asin(x)
  end function casin
  real(dp) function cacos(x)
    real(dp), intent(in) :: x
    cacos = libm_acos(x)
  end function cacos
  real(dp) function catan(x)
    real(dp), intent(in) :: x
    catan = libm_atan(x)
  end function catan

  !> C's 0.0/0.0 gives the x86 default NaN (sign bit set); Fortran arithmetic does the same
  !> at run time, but constant folding would not, so the engine never divides constants.

  ! ===================================================================== strings

  type(CPtr) function c_strcpy(dst, src) result(r)
    type(CPtr), intent(in) :: dst, src
    integer(int64) :: i
    i = 0
    do
       dst%b(dst%o + i) = src%b(src%o + i)
       if (src%b(src%o + i) == 0_int8) exit
       i = i + 1
    end do
    r = dst
  end function c_strcpy

  type(CPtr) function c_strcat(dst, src) result(r)
    type(CPtr), intent(in) :: dst, src
    r = c_strcpy(cadd(dst, strlen(dst)), src)
    r = dst
  end function c_strcat

  integer(int32) function c_strcmp(a, b)
    type(CPtr), intent(in) :: a, b
    integer(int64) :: i
    integer(int32) :: x, y
    i = 0
    do
       x = iand(int(a%b(a%o + i), int32), 255)
       y = iand(int(b%b(b%o + i), int32), 255)
       if (x /= y .or. x == 0) exit
       i = i + 1
    end do
    c_strcmp = x - y
  end function c_strcmp

  type(CPtr) function c_strchr(s, c) result(r)
    type(CPtr), intent(in) :: s
    integer(int32), intent(in) :: c
    integer(int64) :: i
    integer(int8) :: ch
    ch = c8(c)
    i = 0
    do
       if (s%b(s%o + i) == ch) then
          r = cadd(s, i)
          return
       end if
       if (s%b(s%o + i) == 0_int8) exit
       i = i + 1
    end do
    r = cnull()
  end function c_strchr

  type(CPtr) function c_strrchr(s, c) result(r)
    type(CPtr), intent(in) :: s
    integer(int32), intent(in) :: c
    integer(int64) :: i
    integer(int8) :: ch
    ch = c8(c)
    r = cnull()
    i = 0
    do
       if (s%b(s%o + i) == ch) r = cadd(s, i)
       if (s%b(s%o + i) == 0_int8) exit
       i = i + 1
    end do
  end function c_strrchr

  type(CPtr) function c_strstr(h, n) result(r)
    type(CPtr), intent(in) :: h, n
    integer(int64) :: i, j, ln, lh
    ln = strlen(n)
    lh = strlen(h)
    do i = 0, lh - ln
       do j = 0, ln - 1
          if (h%b(h%o + i + j) /= n%b(n%o + j)) exit
       end do
       if (j == ln) then
          r = cadd(h, i)
          return
       end if
    end do
    r = cnull()
  end function c_strstr

  integer(int64) function c_strcspn(s, rej)
    type(CPtr), intent(in) :: s, rej
    integer(int64) :: i, j
    i = 0
    do while (s%b(s%o + i) /= 0_int8)
       j = 0
       do while (rej%b(rej%o + j) /= 0_int8)
          if (rej%b(rej%o + j) == s%b(s%o + i)) then
             c_strcspn = i
             return
          end if
          j = j + 1
       end do
       i = i + 1
    end do
    c_strcspn = i
  end function c_strcspn

  logical function in_set(ch, set)
    integer(int8), intent(in) :: ch
    type(CPtr), intent(in) :: set
    integer(int64) :: j
    in_set = .false.
    j = 0
    do while (set%b(set%o + j) /= 0_int8)
       if (set%b(set%o + j) == ch) then
          in_set = .true.
          return
       end if
       j = j + 1
    end do
  end function in_set

  !> glibc strtok
  type(CPtr) function c_strtok(s, delim) result(r)
    type(CPtr), intent(in) :: s, delim
    type(CPtr) :: p
    if (.not. cisnull(s)) then
       p = s
    else
       p = tok_next
    end if
    if (cisnull(p)) then
       r = cnull()
       return
    end if
    ! skip leading delimiters
    do while (p%b(p%o) /= 0_int8)
       if (.not. in_set(p%b(p%o), delim)) exit
       p%o = p%o + 1
    end do
    if (p%b(p%o) == 0_int8) then
       tok_next = p
       r = cnull()
       return
    end if
    r = p
    do while (p%b(p%o) /= 0_int8)
       if (in_set(p%b(p%o), delim)) then
          p%b(p%o) = 0_int8
          p%o = p%o + 1
          tok_next = p
          return
       end if
       p%o = p%o + 1
    end do
    tok_next = p
  end function c_strtok

  integer(int32) function c_toupper(c)
    integer(int32), intent(in) :: c
    if (c >= 97 .and. c <= 122) then
       c_toupper = c - 32
    else
       c_toupper = c
    end if
  end function c_toupper

  logical function c_isspace(ch)
    integer(int8), intent(in) :: ch
    c_isspace = ch == 32_int8 .or. (ch >= 9_int8 .and. ch <= 13_int8)
  end function c_isspace

  !> glibc atoi = (int) strtol(s, NULL, 10)
  integer(int32) function c_atoi(s)
    type(CPtr), intent(in) :: s
    integer(int64) :: i, v
    logical :: neg, ovf
    integer(int32) :: d
    i = s%o
    do while (c_isspace(s%b(i)))
       i = i + 1
    end do
    neg = .false.
    if (s%b(i) == 45_int8) then
       neg = .true.
       i = i + 1
    else if (s%b(i) == 43_int8) then
       i = i + 1
    end if
    v = 0
    ovf = .false.
    do while (s%b(i) >= 48_int8 .and. s%b(i) <= 57_int8)
       d = int(s%b(i), int32) - 48
       if (.not. ovf) then
          if (v > (huge(v) - d) / 10) then
             ovf = .true.
          else
             v = v * 10 + d
          end if
       end if
       i = i + 1
    end do
    if (ovf) then
       if (neg) then
          v = -huge(v) - 1
       else
          v = huge(v)
       end if
    else if (neg) then
       v = -v
    end if
    c_atoi = u2i(v)
  end function c_atoi

  real(dp) function c_atof(s)
    type(CPtr), intent(in) :: s
    integer(int64) :: n
    c_atof = c_strtod(s, n)
  end function c_atof

  !> strtod(s, &endp)
  real(dp) function c_strtod_ep(s, endp)
    type(CPtr), intent(in) :: s
    type(CPtr), intent(inout) :: endp
    integer(int64) :: n
    c_strtod_ep = c_strtod(s, n)
    endp = cadd(s, n)
  end function c_strtod_ep

  !> char x[N] = "literal": zero the array, then copy the literal (truncated to fit)
  subroutine cinit(arr, s)
    integer(int8), intent(inout) :: arr(0:)
    type(CPtr), intent(in) :: s
    integer(int64) :: i, n
    arr = 0_int8
    n = min(strlen(s), int(size(arr), int64))
    do i = 0, n - 1
       arr(i) = s%b(s%o + i)
    end do
  end subroutine cinit

  !> memset(p, v, n) on a char buffer
  subroutine c_memset(p, v, n)
    type(CPtr), intent(in) :: p
    integer(int32), intent(in) :: v
    integer(int64), intent(in) :: n
    if (n > 0) p%b(p%o:p%o + n - 1) = c8(v)
  end subroutine c_memset

  ! ===================================================================== files

  function c_fopen(name, mode) result(f)
    type(CPtr), intent(in) :: name, mode
    type(CFile), pointer :: f
    character(len=:), allocatable :: fn, md
    integer :: u, ios
    logical :: plus, ex
    integer(int64) :: sz
    fn = cstr(name)
    md = cstr(mode)
    f => null()
    if (len(fn) == 0 .or. len(md) == 0) return
    plus = index(md, '+') > 0
    select case (md(1:1))
    case ('r')
       inquire(file=fn, exist=ex)
       if (.not. ex) return
       if (plus) then
          open(newunit=u, file=fn, access='stream', form='unformatted', status='old', action='readwrite', iostat=ios)
       else
          open(newunit=u, file=fn, access='stream', form='unformatted', status='old', action='read', iostat=ios)
       end if
    case ('w')
       if (plus) then
          open(newunit=u, file=fn, access='stream', form='unformatted', status='replace', action='readwrite', iostat=ios)
       else
          open(newunit=u, file=fn, access='stream', form='unformatted', status='replace', action='write', iostat=ios)
       end if
    case ('a')
       if (plus) then
          open(newunit=u, file=fn, access='stream', form='unformatted', status='unknown', action='readwrite', iostat=ios)
       else
          open(newunit=u, file=fn, access='stream', form='unformatted', status='unknown', action='write', iostat=ios)
       end if
    case default
       return
    end select
    if (ios /= 0) return
    allocate(f)
    f%unit = u
    f%is_open = .true.
    f%can_read = md(1:1) == 'r' .or. plus
    f%can_write = md(1:1) /= 'r' .or. plus
    sz = 0
    inquire(unit=u, size=sz)
    if (sz < 0) sz = 0
    f%fsize = sz
    f%pos = 0
    if (md(1:1) == 'a') f%pos = sz
    allocate(f%wbuf(IOBUF), f%rbuf(IOBUF))
  end function c_fopen

  subroutine io_flushw(f)
    type(CFile), intent(inout) :: f
    if (f%wlen > 0) then
       if (f%is_stdout) then
          block
            character(len=f%wlen) :: s
            integer(int64) :: i
            do i = 1, f%wlen
               s(i:i) = achar(iand(int(f%wbuf(i), int32), 255))
            end do
            write(output_unit, '(a)', advance='no') s
            flush(output_unit)
          end block
       else if (f%is_open) then
          write(f%unit, pos=f%wstart + 1) f%wbuf(1:f%wlen)
       end if
       f%wlen = 0
    end if
  end subroutine io_flushw

  !> append bytes at the current position
  subroutine io_write(f, src, n)
    type(CFile), intent(inout) :: f
    integer(int8), intent(in) :: src(*)
    integer(int64), intent(in) :: n
    integer(int64) :: k, m
    if (n <= 0) return
    f%rlen = 0
    if (f%wlen > 0 .and. f%pos /= f%wstart + f%wlen) call io_flushw(f)
    if (f%wlen == 0) f%wstart = f%pos
    k = 0
    do while (k < n)
       m = min(n - k, IOBUF - f%wlen)
       f%wbuf(f%wlen + 1:f%wlen + m) = src(k + 1:k + m)
       f%wlen = f%wlen + m
       k = k + m
       if (f%wlen == IOBUF) then
          call io_flushw(f)
          f%wstart = f%pos + k
       end if
    end do
    f%pos = f%pos + n
    if (f%pos > f%fsize) f%fsize = f%pos
  end subroutine io_write

  !> read up to n bytes at the current position; returns the count read (sets eof when short)
  integer(int64) function io_read(f, dst, n) result(got)
    type(CFile), intent(inout) :: f
    integer(int8), intent(inout) :: dst(*)
    integer(int64), intent(in) :: n
    integer(int64) :: m
    got = 0
    if (f%wlen > 0) call io_flushw(f)
    do while (got < n)
       if (f%pos >= f%fsize) then
          f%eof = .true.
          return
       end if
       if (f%rlen == 0 .or. f%pos < f%rstart .or. f%pos >= f%rstart + f%rlen) call io_fill(f)
       m = min(n - got, f%rstart + f%rlen - f%pos)
       dst(got + 1:got + m) = f%rbuf(f%pos - f%rstart + 1:f%pos - f%rstart + m)
       got = got + m
       f%pos = f%pos + m
    end do
  end function io_read

  subroutine io_fill(f)
    type(CFile), intent(inout) :: f
    f%rstart = f%pos
    f%rlen = min(IOBUF, f%fsize - f%pos)
    if (f%rlen > 0) read(f%unit, pos=f%pos + 1) f%rbuf(1:f%rlen)
  end subroutine io_fill

  integer(int32) function c_fclose(f)
    type(CFile), pointer, intent(in) :: f
    type(CFile), pointer :: g
    c_fclose = -1
    if (.not. associated(f)) return
    g => f
    c_fclose = 0
    if (g%is_stdout) then
       call io_flushw(g)
       return
    end if
    if (.not. g%is_open) return
    call io_flushw(g)
    close(g%unit)
    g%is_open = .false.
  end function c_fclose

  integer(int32) function c_fflush(f)
    type(CFile), pointer, intent(in) :: f
    c_fflush = 0
    if (associated(f)) call io_flushw(f)
  end function c_fflush

  integer(int32) function c_feof(f)
    type(CFile), pointer, intent(in) :: f
    c_feof = b2i(f%eof)
  end function c_feof

  subroutine c_rewind(f)
    type(CFile), pointer, intent(in) :: f
    if (f%wlen > 0) call io_flushw(f)
    f%pos = 0
    f%eof = .false.
  end subroutine c_rewind

  integer(int32) function c_fseek(f, off, whence)
    type(CFile), pointer, intent(in) :: f
    integer(int64), intent(in) :: off
    integer(int32), intent(in) :: whence
    integer(int64) :: np
    if (f%wlen > 0) call io_flushw(f)
    select case (whence)
    case (0)
       np = off
    case (1)
       np = f%pos + off
    case default
       np = f%fsize + off
    end select
    if (np < 0) then
       c_fseek = -1
       return
    end if
    f%pos = np
    f%eof = .false.
    c_fseek = 0
  end function c_fseek

  integer(int64) function c_ftell(f)
    type(CFile), pointer, intent(in) :: f
    c_ftell = f%pos
  end function c_ftell

  !> fgets(buf, n, f)
  type(CPtr) function c_fgets(buf, n, f) result(r)
    type(CPtr), intent(in) :: buf
    integer(int32), intent(in) :: n
    type(CFile), pointer, intent(in) :: f
    integer(int64) :: k
    integer(int8) :: ch
    if (f%wlen > 0) call io_flushw(f)
    k = 0
    do while (k < n - 1)
       if (f%pos >= f%fsize) then
          f%eof = .true.
          exit
       end if
       if (f%rlen == 0 .or. f%pos < f%rstart .or. f%pos >= f%rstart + f%rlen) call io_fill(f)
       ch = f%rbuf(f%pos - f%rstart + 1)
       f%pos = f%pos + 1
       buf%b(buf%o + k) = ch
       k = k + 1
       if (ch == 10_int8) exit
    end do
    if (k == 0) then
       r = cnull()
       return
    end if
    buf%b(buf%o + k) = 0_int8
    r = buf
  end function c_fgets

  integer(int32) function c_remove(name)
    type(CPtr), intent(in) :: name
    integer :: u, ios
    logical :: ex
    c_remove = -1
    inquire(file=cstr(name), exist=ex)
    if (.not. ex) return
    open(newunit=u, file=cstr(name), status='old', iostat=ios)
    if (ios /= 0) return
    close(u, status='delete', iostat=ios)
    if (ios == 0) c_remove = 0
  end function c_remove

  !> mkstemp: replace the trailing XXXXXX with a unique suffix and create the file; returns 0 or -1
  integer(int32) function c_mkstemp(tmpl)
    type(CPtr), intent(in) :: tmpl
    character(len=*), parameter :: chars = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
    integer(int64) :: n, i
    integer :: try, u, ios, k
    real :: r
    logical :: ex
    c_mkstemp = -1
    n = strlen(tmpl)
    if (n < 6) return
    do try = 1, 100
       do i = n - 6, n - 1
          call random_number(r)
          k = 1 + int(r * 62.0)
          if (k > 62) k = 62
          tmpl%b(tmpl%o + i) = int(ichar(chars(k:k)), int8)
       end do
       inquire(file=cstr(tmpl), exist=ex)
       if (ex) cycle
       open(newunit=u, file=cstr(tmpl), status='new', access='stream', form='unformatted', iostat=ios)
       if (ios /= 0) cycle
       close(u)
       c_mkstemp = 0
       return
    end do
  end function c_mkstemp

  ! --- typed binary I/O (little-endian, as on x86)
  integer(int64) function c_fwrite_i4(v, f)
    integer(int32), intent(in) :: v
    type(CFile), pointer, intent(in) :: f
    call io_write(f, transfer(v, [0_int8]), 4_int64)
    c_fwrite_i4 = 1
  end function c_fwrite_i4

  integer(int64) function c_fwrite_i8(v, f)
    integer(int64), intent(in) :: v
    type(CFile), pointer, intent(in) :: f
    call io_write(f, transfer(v, [0_int8]), 8_int64)
    c_fwrite_i8 = 1
  end function c_fwrite_i8

  !> fwrite(&wide, n, 1, f) with n smaller than the variable: its low n bytes
  integer(int64) function c_fwrite_lo(v, n, f)
    integer(int64), intent(in) :: v
    integer(int32), intent(in) :: n
    type(CFile), pointer, intent(in) :: f
    integer(int8) :: b(8)
    b = transfer(v, b)
    call io_write(f, b, int(n, int64))
    c_fwrite_lo = 1
  end function c_fwrite_lo

  integer(int64) function c_fwrite_r4(v, f)
    real(sp), intent(in) :: v
    type(CFile), pointer, intent(in) :: f
    call io_write(f, transfer(v, [0_int8]), 4_int64)
    c_fwrite_r4 = 1
  end function c_fwrite_r4

  integer(int64) function c_fwrite_r8(v, f)
    real(dp), intent(in) :: v
    type(CFile), pointer, intent(in) :: f
    call io_write(f, transfer(v, [0_int8]), 8_int64)
    c_fwrite_r8 = 1
  end function c_fwrite_r8

  integer(int64) function c_fwrite_i4a(a, off, n, f)
    integer(int32), intent(in) :: a(0:)
    integer(int32), intent(in) :: off, n
    type(CFile), pointer, intent(in) :: f
    if (n > 0) call io_write(f, transfer(a(off:off + n - 1), [0_int8]), 4_int64 * n)
    c_fwrite_i4a = max(n, 0)
  end function c_fwrite_i4a

  integer(int64) function c_fwrite_r4a(a, off, n, f)
    real(sp), intent(in) :: a(0:)
    integer(int32), intent(in) :: off, n
    type(CFile), pointer, intent(in) :: f
    if (n > 0) call io_write(f, transfer(a(off:off + n - 1), [0_int8]), 4_int64 * n)
    c_fwrite_r4a = max(n, 0)
  end function c_fwrite_r4a

  integer(int64) function c_fwrite_r8a(a, off, n, f)
    real(dp), intent(in) :: a(0:)
    integer(int32), intent(in) :: off, n
    type(CFile), pointer, intent(in) :: f
    if (n > 0) call io_write(f, transfer(a(off:off + n - 1), [0_int8]), 8_int64 * n)
    c_fwrite_r8a = max(n, 0)
  end function c_fwrite_r8a

  !> fwrite(p, 1, n, f) of a char buffer
  integer(int64) function c_fwrite_c(p, n, f)
    type(CPtr), intent(in) :: p
    integer(int64), intent(in) :: n
    type(CFile), pointer, intent(in) :: f
    if (n > 0) call io_write(f, p%b(p%o:p%o + n - 1), n)
    c_fwrite_c = max(n, 0_int64)
  end function c_fwrite_c

  integer(int64) function c_fread_i4(v, f)
    integer(int32), intent(inout) :: v
    type(CFile), pointer, intent(in) :: f
    integer(int8) :: b(4)
    if (io_read(f, b, 4_int64) == 4) then
       v = transfer(b, v)
       c_fread_i4 = 1
    else
       c_fread_i4 = 0
    end if
  end function c_fread_i4

  integer(int64) function c_fread_i8(v, f)
    integer(int64), intent(inout) :: v
    type(CFile), pointer, intent(in) :: f
    integer(int8) :: b(8)
    if (io_read(f, b, 8_int64) == 8) then
       v = transfer(b, v)
       c_fread_i8 = 1
    else
       c_fread_i8 = 0
    end if
  end function c_fread_i8

  !> fread into the low n bytes of a wider variable (upper bytes unchanged, as C does)
  integer(int64) function c_fread_lo(v, n, f)
    integer(int64), intent(inout) :: v
    integer(int32), intent(in) :: n
    type(CFile), pointer, intent(in) :: f
    integer(int8) :: b(8), t(8)
    b = transfer(v, b)
    if (io_read(f, t, int(n, int64)) == n) then
       b(1:n) = t(1:n)
       v = transfer(b, v)
       c_fread_lo = 1
    else
       c_fread_lo = 0
    end if
  end function c_fread_lo

  integer(int64) function c_fread_r4(v, f)
    real(sp), intent(inout) :: v
    type(CFile), pointer, intent(in) :: f
    integer(int8) :: b(4)
    if (io_read(f, b, 4_int64) == 4) then
       v = transfer(b, v)
       c_fread_r4 = 1
    else
       c_fread_r4 = 0
    end if
  end function c_fread_r4

  integer(int64) function c_fread_r8(v, f)
    real(dp), intent(inout) :: v
    type(CFile), pointer, intent(in) :: f
    integer(int8) :: b(8)
    if (io_read(f, b, 8_int64) == 8) then
       v = transfer(b, v)
       c_fread_r8 = 1
    else
       c_fread_r8 = 0
    end if
  end function c_fread_r8

  integer(int64) function c_fread_i4a(a, off, n, f)
    integer(int32), intent(inout) :: a(0:)
    integer(int32), intent(in) :: off, n
    type(CFile), pointer, intent(in) :: f
    integer(int8), allocatable :: b(:)
    integer(int64) :: got
    integer(int32) :: k
    allocate(b(4 * max(n, 0)))
    got = io_read(f, b, 4_int64 * n)
    k = int(got / 4)
    if (k > 0) a(off:off + k - 1) = transfer(b(1:4 * k), a(0:0), k)
    c_fread_i4a = k
  end function c_fread_i4a

  integer(int64) function c_fread_r4a(a, off, n, f)
    real(sp), intent(inout) :: a(0:)
    integer(int32), intent(in) :: off, n
    type(CFile), pointer, intent(in) :: f
    integer(int8), allocatable :: b(:)
    integer(int64) :: got
    integer(int32) :: k
    allocate(b(4 * max(n, 0)))
    got = io_read(f, b, 4_int64 * n)
    k = int(got / 4)
    if (k > 0) a(off:off + k - 1) = transfer(b(1:4 * k), a(0:0), k)
    c_fread_r4a = k
  end function c_fread_r4a

  integer(int64) function c_fread_r8a(a, off, n, f)
    real(dp), intent(inout) :: a(0:)
    integer(int32), intent(in) :: off, n
    type(CFile), pointer, intent(in) :: f
    integer(int8), allocatable :: b(:)
    integer(int64) :: got
    integer(int32) :: k
    allocate(b(8 * max(n, 0)))
    got = io_read(f, b, 8_int64 * n)
    k = int(got / 8)
    if (k > 0) a(off:off + k - 1) = transfer(b(1:8 * k), a(0:0), k)
    c_fread_r8a = k
  end function c_fread_r8a

  integer(int64) function c_fread_c(p, n, f)
    type(CPtr), intent(in) :: p
    integer(int64), intent(in) :: n
    type(CFile), pointer, intent(in) :: f
    c_fread_c = 0
    if (n > 0) c_fread_c = io_read(f, p%b(p%o:p%o + n - 1), n)
  end function c_fread_c

  ! ===================================================================== printf family

  subroutine c_fprintf(f, fmt, a1, a2, a3, a4, a5, a6, a7, a8, a9, a10, a11, a12, a13, a14, a15, a16, a17, a18, a19, a20)
    type(CFile), pointer, intent(in) :: f
    type(CPtr), intent(in) :: fmt
    class(*), intent(in), optional :: a1, a2, a3, a4, a5, a6, a7, a8, a9, a10, a11, a12, a13, a14, a15, a16, a17, a18, a19, a20
    integer :: nout
    if (.not. allocated(fmtbuf)) allocate(fmtbuf(4096))
    call c_format(fmt, fmtbuf, nout, a1, a2, a3, a4, a5, a6, a7, a8, a9, a10, a11, a12, a13, a14, a15, a16, a17, a18, a19, a20)
    if (.not. associated(f)) return
    call io_write(f, fmtbuf, int(nout, int64))
  end subroutine c_fprintf

  !> snprintf(buf, n, fmt, ...): returns the untruncated length
  integer(int32) function c_snprintf(buf, n, fmt, a1, a2, a3, a4, a5, a6, a7, a8, a9, a10, a11, a12, a13, a14, a15, a16, &
                                     a17, a18, a19, a20)
    type(CPtr), intent(in) :: buf
    integer(int64), intent(in) :: n
    type(CPtr), intent(in) :: fmt
    class(*), intent(in), optional :: a1, a2, a3, a4, a5, a6, a7, a8, a9, a10, a11, a12, a13, a14, a15, a16, a17, a18, a19, a20
    integer :: nout
    integer(int64) :: m
    if (.not. allocated(fmtbuf)) allocate(fmtbuf(4096))
    call c_format(fmt, fmtbuf, nout, a1, a2, a3, a4, a5, a6, a7, a8, a9, a10, a11, a12, a13, a14, a15, a16, a17, a18, a19, a20)
    c_snprintf = nout
    if (n <= 0) return
    m = min(int(nout, int64), n - 1)
    if (m > 0) buf%b(buf%o:buf%o + m - 1) = fmtbuf(1:m)
    buf%b(buf%o + m) = 0_int8
  end function c_snprintf

  ! ===================================================================== time

  integer(int64) function days_from_civil(y0, m, d)
    integer, intent(in) :: y0, m, d
    integer :: y, era, yoe, doy, doe, mp
    y = y0
    if (m <= 2) y = y - 1
    era = merge(y, y - 399, y >= 0) / 400
    yoe = y - era * 400
    mp = merge(m - 3, m + 9, m > 2)
    doy = (153 * mp + 2) / 5 + d - 1
    doe = yoe * 365 + yoe / 4 - yoe / 100 + doy
    days_from_civil = int(era, int64) * 146097 + doe - 719468
  end function days_from_civil

  !> time(NULL): seconds since the epoch
  integer(int64) function c_time()
    integer :: v(8)
    call date_and_time(values=v)
    c_time = days_from_civil(v(1), v(2), v(3)) * 86400_int64 + v(5) * 3600 + v(6) * 60 + v(7) - v(4) * 60_int64
  end function c_time

  !> ctime(&t): "Www Mmm dd hh:mm:ss yyyy\n" in local time
  type(CPtr) function c_ctime(t) result(r)
    integer(int64), intent(in) :: t
    character(len=*), parameter :: wd = 'ThuFriSatSunMonTueWed'
    character(len=*), parameter :: mn = 'JanFebMarAprMayJunJulAugSepOctNovDec'
    integer :: v(8), y, m, d, doe, yoe, doy, mp, era, k
    integer(int64) :: lt, days, secs, z
    character(len=26) :: s
    call date_and_time(values=v)
    lt = t + v(4) * 60_int64
    days = lt / 86400
    secs = lt - days * 86400
    if (secs < 0) then
       secs = secs + 86400
       days = days - 1
    end if
    ! civil_from_days
    z = days + 719468
    era = int(merge(z, z - 146096, z >= 0) / 146097)
    doe = int(z - era * 146097_int64)
    yoe = (doe - doe / 1460 + doe / 36524 - doe / 146096) / 365
    y = yoe + era * 400
    doy = doe - (365 * yoe + yoe / 4 - yoe / 100)
    mp = (5 * doy + 2) / 153
    d = doy - (153 * mp + 2) / 5 + 1
    m = merge(mp + 3, mp - 9, mp < 10)
    if (m <= 2) y = y + 1
    k = int(modulo(days, 7_int64))
    write(s, '(a3,1x,a3,1x,i2,1x,i2.2,":",i2.2,":",i2.2,1x,i4)') wd(3 * k + 1:3 * k + 3), mn(3 * m - 2:3 * m), d, &
         int(secs / 3600), int(mod(secs, 3600_int64) / 60), int(mod(secs, 60_int64)), y
    do k = 1, 24
       ctime_buf(k - 1) = int(ichar(s(k:k)), int8)
    end do
    ctime_buf(24) = 10_int8
    ctime_buf(25) = 0_int8
    r = cview(ctime_buf)
  end function c_ctime

  ! ===================================================================== setup

  subroutine crt_init()
    if (.not. associated(c_stdout)) then
       allocate(c_stdout)
       c_stdout%is_stdout = .true.
       c_stdout%can_write = .true.
       allocate(c_stdout%wbuf(IOBUF), c_stdout%rbuf(1))
    end if
  end subroutine crt_init

end module crt_io
