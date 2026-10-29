#!/bin/bash
# run_libm_generic_control.sh : run EPA 5.2.4 itself with glibc's generic (non-FMA) math routines, as glibc
# would choose them on a processor without FMA and AVX2, and gate it against the stored reference.
# Result in this session: 437 of 480 identical, 43 differ (ctl_libm_generic.txt).
cd "$(dirname "$0")"
GLIBC_TUNABLES=glibc.cpu.hwcaps=-AVX2,-FMA,-FMA4 python3 gate.py ctl_libm_generic "$(pwd)/../ref/runswmm" -j 2 | tee ctl_libm_generic.txt
