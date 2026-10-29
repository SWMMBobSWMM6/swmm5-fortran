#!/bin/bash
# Positive control for the gate: the Fortran engine built with fused multiply-add allowed.
# The only difference from f90/build.sh is the floating-point contraction setting:
#   -ffp-contract=off  ->  -ffp-contract=fast -mfma
# (-mfma lets the compiler use the FMA instructions that -ffp-contract=fast asks for; without it
#  x86-64's baseline instruction set has none and nothing would change.)
# Output: gate/fma_control/bin/runswmm.  Check: objdump shows vfmadd/vfmsub instructions in it and
# none in f90/bin/runswmm.
set -e
cd "$(dirname "$0")/.."
D=gate/fma_control
rm -rf "$D"; mkdir -p "$D"
cp -r f90/runtime f90/gen f90/build.sh "$D"/
FFLAGS="-O2 -fwrapv -ffp-contract=fast -mfma -fno-fast-math -ffree-line-length-none -fimplicit-none -fno-range-check" \
  bash "$D/build.sh"
a=$(objdump -d "$D/bin/runswmm" | grep -cE 'vfn?m(add|sub)'); b=$(objdump -d f90/bin/runswmm | grep -cE 'vfn?m(add|sub)' || true)
echo "FMA instructions in control build: $a"
echo "FMA instructions in shipped build: $b"
mkdir -p gate/results
printf '{"fma_instr_control": %d, "fma_instr_shipped": %d}\n' "$a" "$b" > gate/results/fma_control_build.json
