! overrides.inc - hand-ported pieces of EPA SWMM 5.2.4, included into module swmm5_engine.
! odesolve.c and mempool.c (whole files) and six helpers from swmm5.c / project.c, whose C pointer
! arithmetic the translator does not map.  Statement order and floating-point expressions follow
! the C source exactly.  The signatures must match f90/gen/override_signatures.txt.
! Written by Claude (Anthropic); see AI-USE.md.

! ------------------------------------------------------------------ swmm5.c helpers
recursive function sstrncpy(dest, src, n) result(res_)
   type(CPtr), value :: dest, src
   integer(int64), value :: n
   integer(int64) :: res_
   integer(int64) :: offset
   offset = 0
   if (n > 0) then
      do while (src%b(src%o + offset) /= 0_int8)
         if (offset == n) exit
         dest%b(dest%o + offset) = src%b(src%o + offset)
         offset = offset + 1
      end do
   end if
   dest%b(dest%o + offset) = 0_int8
   res_ = strlen(dest)
end function sstrncpy

recursive function sstrcat(dest, src, size) result(res_)
   type(CPtr), value :: dest, src
   integer(int64), value :: size
   integer(int64) :: res_
   integer(int64) :: dest_len, offset, src_index
   dest_len = strlen(dest)
   offset = dest_len
   src_index = 0
   do while (src%b(src%o + src_index) /= 0_int8)
      dest%b(dest%o + offset) = src%b(src%o + src_index)
      offset = offset + 1
      src_index = src_index + 1
      if (offset == size - 1) exit
   end do
   dest%b(dest%o + offset) = 0_int8
   res_ = strlen(dest)
end function sstrcat

!> realpath() from the C library: Fortran has no portable way to resolve symbolic links
recursive subroutine getAbsolutePath(fname, absPath, size)
   use iso_c_binding, only: c_char, c_null_char, c_associated
   type(CPtr), value :: fname, absPath
   integer(int64), value :: size
   interface
      type(c_ptr) function libc_realpath(path, resolved) bind(C, name='realpath')
         import :: c_ptr, c_char
         character(kind=c_char), intent(in) :: path(*)
         character(kind=c_char), intent(inout) :: resolved(*)
      end function
   end interface
   character(kind=c_char) :: cpath(4097), res(4097)
   character(len=:), allocatable :: f
   type(c_ptr) :: r
   type(CPtr) :: endOfDir
   integer :: i, n
   if (cisnull(fname)) return
   if (strlen(fname) == 0) return
   if (isRelativePath(fname) /= 0) then
      f = cstr(fname)
      do i = 1, len(f)
         cpath(i) = f(i:i)
      end do
      cpath(len(f) + 1) = c_null_char
      res = c_null_char
      r = libc_realpath(cpath, res)
      ! like glibc, the buffer holds what was resolved even when realpath fails
      n = 0
      do while (res(n + 1) /= c_null_char .and. n < 4096)
         n = n + 1
      end do
      do i = 1, n
         if (i - 1 >= size - 1) exit
         call cset(absPath, int(i - 1, int64), ichar(res(i)))
      end do
      call cset(absPath, int(min(int(n, int64), max(size - 1, 0_int64)), int64), 0)
   else
      res_dummy: block
        integer(int64) :: k
        k = sstrncpy(absPath, fname, strlen(fname))
      end block res_dummy
   end if
   endOfDir = c_strrchr(absPath, ichar('/'))
   if (.not. cisnull(endOfDir)) call cset(endOfDir, 1_int64, 0)
end subroutine getAbsolutePath

recursive function getTempFileName(fname) result(res_)
   type(CPtr), value :: fname
   type(CPtr) :: res_
   integer(int64) :: k
   integer(int32) :: fd
   k = sstrncpy(fname, clit('swmmXXXXXX'), int(MAXFNAME, int64))
   fd = c_mkstemp(fname)
   res_ = fname
end function getTempFileName

! ------------------------------------------------------------------ project.c matrix helpers
! (C memsets only nrows*ncols BYTES of the nrows*ncols doubles; every element is written before it
!  is read, so the Fortran port zeroes them all)
recursive function project_createMatrix(nrows, ncols) result(res_)
   integer(int32), value :: nrows, ncols
   type(dp_row), pointer :: res_(:)
   integer(int32) :: i
   nullify(res_)
   if (nrows < 1 .or. ncols < 1) return
   allocate(res_(0:nrows - 1))
   do i = 0, nrows - 1
      allocate(res_(i)%p(0:ncols - 1))
      res_(i)%p = 0.0_dp
   end do
end function project_createMatrix

recursive subroutine project_freeMatrix(a)
   type(dp_row), pointer, intent(in) :: a(:)
end subroutine project_freeMatrix

! ------------------------------------------------------------------ mempool.c (object ID strings)
recursive function AllocHdr() result(res_)
   type(alloc_hdr_t), pointer :: res_
   allocate(res_)
end function AllocHdr

recursive function AllocInit() result(res_)
   type(alloc_handle_t), pointer :: res_
   allocate(res_)
end function AllocInit

recursive function Alloc(size) result(res_)
   integer(int64), value :: size
   type(CPtr) :: res_
   res_ = cbuf(size)
end function Alloc

recursive function AllocSetPool(newpool) result(res_)
   type(alloc_handle_t), pointer, intent(in) :: newpool
   type(alloc_handle_t), pointer :: res_
   res_ => newpool
end function AllocSetPool

recursive subroutine AllocReset()
end subroutine AllocReset

recursive subroutine AllocFreePool()
end subroutine AllocFreePool

! ------------------------------------------------------------------ odesolve.c (Cash-Karp Runge-Kutta)
recursive function odesolve_open(n) result(res_)
   integer(int32), value :: n
   integer(int32) :: res_
   ode_nmax = 0
   allocate(ode_y(0:n - 1), ode_yscal(0:n - 1), ode_dydx(0:n - 1), ode_yerr(0:n - 1), ode_ytemp(0:n - 1))
   allocate(ode_ak2(0:n - 1), ode_ak3(0:n - 1), ode_ak4(0:n - 1), ode_ak5(0:n - 1), ode_ak6(0:n - 1))
   ode_y = 0.0_dp; ode_yscal = 0.0_dp; ode_dydx = 0.0_dp; ode_yerr = 0.0_dp; ode_ytemp = 0.0_dp
   ode_ak2 = 0.0_dp; ode_ak3 = 0.0_dp; ode_ak4 = 0.0_dp; ode_ak5 = 0.0_dp; ode_ak6 = 0.0_dp
   ode_nmax = n
   res_ = 1
end function odesolve_open

recursive subroutine odesolve_close()
   ode_nmax = 0
end subroutine odesolve_close

recursive function odesolve_integrate(ystart, n, x1, x2, eps, h1, derivs) result(res_)
   real(dp), pointer, intent(in) :: ystart(:)
   integer(int32), value :: n
   real(dp), value :: x1, x2, eps, h1
   procedure(ode_derivs) :: derivs
   integer(int32) :: res_
   integer(int32) :: i, errcode, nstp
   real(dp), target :: x, h, hdid, hnext
   hdid = 0.0_dp
   hnext = 0.0_dp
   x = x1
   h = h1
   if (ode_nmax < n) then
      res_ = 1
      return
   end if
   do i = 0, n - 1
      ode_y(i) = ystart(i)
   end do
   do nstp = 1, 10000
      call derivs(x, ode_y, ode_dydx)
      do i = 0, n - 1
         ode_yscal(i) = abs(ode_y(i)) + abs(ode_dydx(i) * h) + 1.0e-30_dp
      end do
      if ((x + h - x2) * (x + h - x1) > 0.0_dp) h = x2 - x
      errcode = ode_rkqs(x, n, h, eps, hdid, hnext, derivs)
      if (errcode /= 0) exit
      if ((x - x2) * (x2 - x1) >= 0.0_dp) then
         do i = 0, n - 1
            ystart(i) = ode_y(i)
         end do
         res_ = 0
         return
      end if
      if (abs(hnext) <= 0.0_dp) then
         res_ = 2
         return
      end if
      h = hnext
   end do
   res_ = 3
end function odesolve_integrate

recursive function ode_rkqs(x, n, htry, eps, hdid, hnext, derivs) result(res_)
   real(dp), intent(inout) :: x
   integer(int32), value :: n
   real(dp), value :: htry, eps
   real(dp), intent(inout) :: hdid, hnext
   procedure(ode_derivs) :: derivs
   integer(int32) :: res_
   integer(int32) :: i
   real(dp) :: err, errmax, h, htemp, xnew, xold
   xold = x
   h = htry
   do
      call ode_rkck(xold, n, h, derivs)
      errmax = 0.0_dp
      do i = 0, n - 1
         err = abs(ode_yerr(i) / ode_yscal(i))
         if (err > errmax) errmax = err
      end do
      errmax = errmax / eps
      if (errmax > 1.0_dp) then
         htemp = 0.9_dp * h * (errmax ** (-0.25_dp))
         if (h >= 0) then
            if (htemp > 0.1_dp * h) then
               h = htemp
            else
               h = 0.1_dp * h
            end if
         else
            if (htemp < 0.1_dp * h) then
               h = htemp
            else
               h = 0.1_dp * h
            end if
         end if
         xnew = xold + h
         if (xnew == xold) then
            res_ = 2
            return
         end if
         cycle
      else
         if (errmax > 1.89e-4_dp) then
            hnext = 0.9_dp * h * (errmax ** (-0.2_dp))
         else
            hnext = 5.0_dp * h
         end if
         hdid = h
         x = x + hdid
         do i = 0, n - 1
            ode_y(i) = ode_ytemp(i)
         end do
         res_ = 0
         return
      end if
   end do
end function ode_rkqs

recursive subroutine ode_rkck(x, n, h, derivs)
   real(dp), value :: x, h
   integer(int32), value :: n
   procedure(ode_derivs) :: derivs
   real(dp), parameter :: a2 = 0.2_dp, a3 = 0.3_dp, a4 = 0.6_dp, a5 = 1.0_dp, a6 = 0.875_dp, &
      b21 = 0.2_dp, b31 = 3.0_dp / 40.0_dp, b32 = 9.0_dp / 40.0_dp, b41 = 0.3_dp, b42 = -0.9_dp, b43 = 1.2_dp, &
      b51 = -11.0_dp / 54.0_dp, b52 = 2.5_dp, b53 = -70.0_dp / 27.0_dp, b54 = 35.0_dp / 27.0_dp, &
      b61 = 1631.0_dp / 55296.0_dp, b62 = 175.0_dp / 512.0_dp, b63 = 575.0_dp / 13824.0_dp, &
      b64 = 44275.0_dp / 110592.0_dp, b65 = 253.0_dp / 4096.0_dp, c1 = 37.0_dp / 378.0_dp, &
      c3 = 250.0_dp / 621.0_dp, c4 = 125.0_dp / 594.0_dp, c6 = 512.0_dp / 1771.0_dp, &
      dc5 = -277.0_dp / 14336.0_dp
   real(dp), parameter :: dc1 = c1 - 2825.0_dp / 27648.0_dp, dc3 = c3 - 18575.0_dp / 48384.0_dp, &
      dc4 = c4 - 13525.0_dp / 55296.0_dp, dc6 = c6 - 0.25_dp
   integer(int32) :: i
   do i = 0, n - 1
      ode_ytemp(i) = ode_y(i) + b21 * h * ode_dydx(i)
   end do
   call derivs(x + a2 * h, ode_ytemp, ode_ak2)
   do i = 0, n - 1
      ode_ytemp(i) = ode_y(i) + h * (b31 * ode_dydx(i) + b32 * ode_ak2(i))
   end do
   call derivs(x + a3 * h, ode_ytemp, ode_ak3)
   do i = 0, n - 1
      ode_ytemp(i) = ode_y(i) + h * (b41 * ode_dydx(i) + b42 * ode_ak2(i) + b43 * ode_ak3(i))
   end do
   call derivs(x + a4 * h, ode_ytemp, ode_ak4)
   do i = 0, n - 1
      ode_ytemp(i) = ode_y(i) + h * (b51 * ode_dydx(i) + b52 * ode_ak2(i) + b53 * ode_ak3(i) + b54 * ode_ak4(i))
   end do
   call derivs(x + a5 * h, ode_ytemp, ode_ak5)
   do i = 0, n - 1
      ode_ytemp(i) = ode_y(i) + h * (b61 * ode_dydx(i) + b62 * ode_ak2(i) + b63 * ode_ak3(i) + &
                                     b64 * ode_ak4(i) + b65 * ode_ak5(i))
   end do
   call derivs(x + a6 * h, ode_ytemp, ode_ak6)
   do i = 0, n - 1
      ode_ytemp(i) = ode_y(i) + h * (c1 * ode_dydx(i) + c3 * ode_ak3(i) + c4 * ode_ak4(i) + c6 * ode_ak6(i))
   end do
   do i = 0, n - 1
      ode_yerr(i) = h * (dc1 * ode_dydx(i) + dc3 * ode_ak3(i) + dc4 * ode_ak4(i) + dc5 * ode_ak5(i) + dc6 * ode_ak6(i))
   end do
end subroutine ode_rkck
