! runswmm for the Fortran port: same command line and console messages as EPA's run/main.c.
! Written by Claude (Anthropic); see AI-USE.md.
program runswmm
  use iso_fortran_env, only: int8, int32, int64, real64, output_unit
  use crt_base
  use crt_format
  use crt_io
  use swmm5_engine, only: swmm5_init, swmm_getVersion, swmm_run, swmm_getError, swmm_getWarnings
  implicit none
  integer :: nargs, version, vMajor, vMinor, vRelease, ierr
  character(len=4096) :: a1, a2, a3
  integer(int64) :: start
  real(real64) :: runTime
  type(CPtr) :: err
  character(len=32) :: tbuf

  call swmm5_init()
  version = swmm_getVersion()
  vMajor = version / 10000
  vMinor = (version - 10000 * vMajor) / 1000
  vRelease = version - 10000 * vMajor - 1000 * vMinor
  start = c_time()
  nargs = command_argument_count()
  if (nargs == 0) then
     call say(achar(10) // 'Not Enough Arguments (See Help --help)' // achar(10) // achar(10))
  else if (nargs == 1) then
     call get_command_argument(1, a1)
     if (trim(a1) == '--help' .or. trim(a1) == '-h') then
        call say(achar(10) // achar(10) // 'STORMWATER MANAGEMENT MODEL (SWMM) HELP' // achar(10) // achar(10) // &
             'COMMANDS:' // achar(10) // achar(9) // '--help (-h)       SWMM Help' // achar(10) // achar(9) // &
             '--version (-v)    Build Version' // achar(10) // achar(10) // 'RUNNING A SIMULATION:' // achar(10) // &
             achar(9) // ' runswmm <input file> <report file> <optional output file>' // achar(10) // achar(10))
     else if (trim(a1) == '--version' .or. trim(a1) == '-v') then
        write(tbuf, '(i0,".",i0,".",i0)') vMajor, vMinor, vRelease
        call say(achar(10) // trim(tbuf) // achar(10) // achar(10))
     else
        call say(achar(10) // 'Unknown Argument (See Help --help)' // achar(10) // achar(10))
     end if
  else
     call get_command_argument(1, a1)
     call get_command_argument(2, a2)
     a3 = ''
     if (nargs > 2) call get_command_argument(3, a3)
     write(tbuf, '(i0,".",i0)') vMajor, vMinor
     call say(achar(10) // '... EPA SWMM ' // trim(tbuf))
     write(tbuf, '(i0,".",i0,".",i0)') vMajor, vMinor, vRelease
     call say(' (Build ' // trim(tbuf) // ') [Fortran port]' // achar(10))
     ierr = swmm_run(clit(trim(a1)), clit(trim(a2)), clit(trim(a3)))
     runTime = real(c_time() - start, real64)
     write(tbuf, '(f0.2)') runTime
     if (tbuf(1:1) == '.') tbuf = '0' // tbuf
     call say(achar(10) // achar(10) // '... EPA SWMM completed in ' // trim(tbuf) // ' seconds.')
     err = cbuf(128)
     if (swmm_getError(err, 127) > 0) then
        call say(' There are errors.' // achar(10))
     else if (swmm_getWarnings() > 0) then
        call say(' There are warnings.' // achar(10))
     else
        call say(achar(10))
     end if
  end if
  ierr = c_fflush(c_stdout)
contains
  subroutine say(s)
    character(len=*), intent(in) :: s
    call c_fprintf(c_stdout, clit('%s'), clit(s))
    ierr = c_fflush(c_stdout)
  end subroutine say
end program runswmm
