! overrides_decl.inc - module variables of the hand-ported odesolve.c (see overrides.inc).
! Written by Claude (Anthropic); see AI-USE.md.
integer(int32), save :: ode_nmax = 0
real(dp), pointer, save :: ode_y(:) => null(), ode_yscal(:) => null(), ode_dydx(:) => null(), &
   ode_yerr(:) => null(), ode_ytemp(:) => null()
real(dp), pointer, save :: ode_ak2(:) => null(), ode_ak3(:) => null(), ode_ak4(:) => null(), &
   ode_ak5(:) => null(), ode_ak6(:) => null()
