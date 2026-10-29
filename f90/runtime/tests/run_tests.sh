#!/usr/bin/env bash
# run_tests.sh - build and run the crt_format glibc comparison tests.
# Written by Claude (Anthropic); see AI-USE.md.
#
# gen_ref (C, glibc) generates every case and glibc's answer; test_crt_format (Fortran)
# replays them through crt_format and compares byte for byte.  The reference stream (~0.7 GB)
# is a temporary file in $WORK, deleted afterwards.  Exit status is non-zero on any mismatch.
#
#   VALS=/path/vals.txt ./run_tests.sh   # optional extra doubles (16 hex chars LE per line)
set -euo pipefail
HERE=$(cd "$(dirname "$0")" && pwd)
RT=$(cd "$HERE/.." && pwd)
WORK=${WORK:-$HERE/work}
mkdir -p "$WORK"
DEFVALS=/tmp/claude-0/-home-claude/9f3dde4c-f353-52c4-b476-e410dd8d4e21/scratchpad/fmt/vals.txt
VALS=${VALS:-$DEFVALS}
[ -f "$VALS" ] || VALS=""

gcc --version | sed -n 1p
gfortran --version | sed -n 1p
ldd --version | sed -n 1p

# same flavour as the SWMM reference build (ref/Makefile): gnu17, no _FORTIFY_SOURCE
gcc -O2 -std=gnu17 -U_FORTIFY_SOURCE -D_FORTIFY_SOURCE=0 -w -o "$WORK/gen_ref" "$HERE/gen_ref.c" -lm
FFLAGS="-O2 -std=f2008 -fall-intrinsics -Wall"
gfortran $FFLAGS -J "$WORK" -c "$RT/crt_base.f90" -o "$WORK/crt_base.o"
gfortran $FFLAGS -J "$WORK" -c "$RT/crt_format.f90" -o "$WORK/crt_format.o"
gfortran $FFLAGS -J "$WORK" -I "$WORK" "$HERE/test_crt_format.f90" \
    "$WORK/crt_format.o" "$WORK/crt_base.o" -o "$WORK/test_crt_format"

REF="$WORK/ref.bin"
trap 'rm -f "$REF"' EXIT
# a regular file, not a pipe: libgfortran treats a short read() from a pipe as end of file
if [ -n "$VALS" ]; then "$WORK/gen_ref" "$VALS" > "$REF"; else "$WORK/gen_ref" > "$REF"; fi
ls -l "$REF"
"$WORK/test_crt_format" "$REF" | tee "$WORK/results.txt"
