#!/bin/bash
# Build bin/runswmm (the Fortran port) with gfortran.
#   -fwrapv            C's int arithmetic wraps on overflow (gcc's behaviour for EPA's build)
#   -ffp-contract=off  no fused multiply-add: every product is rounded, as in EPA's x86-64 build
#   -fno-fast-math     IEEE semantics (the default; stated for the record)
set -e
cd "$(dirname "$0")"
mkdir -p bin obj
FFLAGS=${FFLAGS:-"-O2 -fwrapv -ffp-contract=off -fno-fast-math -ffree-line-length-none -fimplicit-none -fno-range-check"}
FMT=runtime/crt_format.f90
[ -f "$FMT" ] || { echo "missing $FMT"; exit 1; }
gfortran $FFLAGS -Jobj -c runtime/crt_base.f90 -o obj/crt_base.o
gfortran $FFLAGS -Jobj -c "$FMT" -o obj/crt_format.o
gfortran $FFLAGS -Jobj -c runtime/crt_io.f90 -o obj/crt_io.o
gfortran $FFLAGS -Jobj -Iruntime -c gen/swmm5_engine.f90 -o obj/swmm5_engine.o "$@"
gfortran $FFLAGS -Jobj -c runtime/runswmm.f90 -o obj/runswmm.o
gfortran $FFLAGS -o bin/runswmm obj/runswmm.o obj/swmm5_engine.o obj/crt_io.o obj/crt_format.o obj/crt_base.o -lm
echo built bin/runswmm
