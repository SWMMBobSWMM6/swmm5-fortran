! crt_base.f90 - the C char* type shared by the Fortran port's runtime and generated code.
! Written by Claude (Anthropic); see AI-USE.md.
module crt_base
  use iso_fortran_env, only: int8, int32, int64, real32, real64
  implicit none
  integer, parameter :: dp = real64, sp = real32

  !> C char*: a byte buffer (lower bound 0) plus an offset; b null = NULL pointer
  type :: CPtr
     integer(int8), pointer :: b(:) => null()
     integer(int32) :: o = 0
  end type CPtr

  !> index/size arguments may be int32 or int64 (C's int and size_t)
  interface cbuf
     module procedure cbuf_8, cbuf_4
  end interface
  interface cadd
     module procedure cadd_8, cadd_4
  end interface
  interface cget
     module procedure cget_8, cget_4
  end interface
  interface cset
     module procedure cset_8, cset_4
  end interface

contains

  !> new zeroed buffer of n bytes (at least 1), like calloc(n,1)
  function cbuf_8(n) result(p)
    integer(int64), intent(in) :: n
    type(CPtr) :: p
    allocate(p%b(0:max(n, 1_int64) - 1))
    p%b = 0_int8
    p%o = 0
  end function cbuf_8

  function cbuf_4(n) result(p)
    integer(int32), intent(in) :: n
    type(CPtr) :: p
    p = cbuf_8(int(n, int64))
  end function cbuf_4

  !> view of a fixed byte array (e.g. a char[] global, local or struct member)
  function cview(arr) result(p)
    integer(int8), target, intent(in) :: arr(0:)
    type(CPtr) :: p
    p%b => arr
    p%o = 0
  end function cview

  pure function cnull() result(p)
    type(CPtr) :: p
    p%b => null()
    p%o = 0
  end function cnull

  pure logical function cisnull(p)
    type(CPtr), intent(in) :: p
    cisnull = .not. associated(p%b)
  end function cisnull

  function cadd_8(p, n) result(q)
    type(CPtr), intent(in) :: p
    integer(int64), intent(in) :: n
    type(CPtr) :: q
    q%b => p%b
    q%o = p%o + int(n, int32)
  end function cadd_8

  function cadd_4(p, n) result(q)
    type(CPtr), intent(in) :: p
    integer(int32), intent(in) :: n
    type(CPtr) :: q
    q%b => p%b
    q%o = p%o + n
  end function cadd_4

  logical function ceq(p, q)
    type(CPtr), intent(in) :: p, q
    if (.not. associated(p%b) .or. .not. associated(q%b)) then
       ceq = (.not. associated(p%b)) .and. (.not. associated(q%b))
    else
       ceq = associated(p%b, q%b) .and. p%o == q%o
    end if
  end function ceq

  integer(int64) function cdiff(p, q)
    type(CPtr), intent(in) :: p, q
    cdiff = int(p%o - q%o, int64)
  end function cdiff

  !> signed char p[i]
  integer(int32) function cget_8(p, i)
    type(CPtr), intent(in) :: p
    integer(int64), intent(in) :: i
    cget_8 = int(p%b(p%o + i), int32)
  end function cget_8

  integer(int32) function cget_4(p, i)
    type(CPtr), intent(in) :: p
    integer(int32), intent(in) :: i
    cget_4 = int(p%b(p%o + i), int32)
  end function cget_4

  !> C's conversion of an int to (signed) char: keep the low byte
  elemental integer(int8) function c8(v)
    integer(int32), intent(in) :: v
    integer(int32) :: w
    w = iand(v, 255)
    if (w > 127) w = w - 256
    c8 = int(w, int8)
  end function c8

  subroutine cset_8(p, i, v)
    type(CPtr), intent(in) :: p
    integer(int64), intent(in) :: i
    integer(int32), intent(in) :: v
    p%b(p%o + i) = c8(v)
  end subroutine cset_8

  subroutine cset_4(p, i, v)
    type(CPtr), intent(in) :: p
    integer(int32), intent(in) :: i
    integer(int32), intent(in) :: v
    p%b(p%o + i) = c8(v)
  end subroutine cset_4

  integer(int64) function strlen(p)
    type(CPtr), intent(in) :: p
    integer(int64) :: i
    i = p%o
    do while (p%b(i) /= 0_int8)
       i = i + 1
    end do
    strlen = i - p%o
  end function strlen

  !> Fortran string from a C string (for file names and diagnostics)
  function cstr(p) result(s)
    type(CPtr), intent(in) :: p
    character(len=:), allocatable :: s
    integer(int64) :: n, i
    n = strlen(p)
    allocate(character(len=n) :: s)
    do i = 1, n
       s(i:i) = achar(iand(int(p%b(p%o + i - 1), int32), 255))
    end do
  end function cstr

  !> C string (new buffer) from a Fortran string
  function clit(s) result(p)
    character(len=*), intent(in) :: s
    type(CPtr) :: p
    integer :: i
    p = cbuf(int(len(s) + 1, int64))
    do i = 1, len(s)
       p%b(i - 1) = int(ichar(s(i:i)) - merge(256, 0, ichar(s(i:i)) > 127), int8)
    end do
  end function clit
end module crt_base
