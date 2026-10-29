#!/bin/bash
# profile_fortran.sh <model.inp> : gprof flat profile of the Fortran engine on one model.
# Builds a copy of f90/ with the shipped flags plus -pg, runs the model in its own folder,
# and prints the top of the flat profile.  Used for gate/results/fortran_gprof.txt.
set -e
cd "$(dirname "$0")/.."
inp=$(readlink -f "$1")
W=${TMPDIR:-/tmp}/swmm_f90prof; rm -rf "$W"; mkdir -p "$W"
cp -r f90/runtime f90/gen f90/build.sh "$W"/
FFLAGS="-O2 -fwrapv -ffp-contract=off -fno-fast-math -ffree-line-length-none -fimplicit-none -fno-range-check -pg" \
  bash "$W/build.sh" >/dev/null
( cd "$(dirname "$inp")" && GMON_OUT_PREFIX="$W/gmon" "$W/bin/runswmm" "$(basename "$inp")" "$W/r.rpt" "$W/r.out" >/dev/null )
g=$(ls "$W"/gmon.* | head -1)
echo "# gprof flat profile, Fortran engine (f90/gen + runtime, shipped flags + -pg)"
echo "# model: ${1}"
echo "# gfortran: $(gfortran --version | sed -n 1p)"
gprof -b -p "$W/bin/runswmm" "$g" | sed -n 1,40p
