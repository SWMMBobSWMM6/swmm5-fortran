#!/bin/bash
# measure_env.sh - record the toolchain and processor the stored runs used, and peak memory on the largest model.
#   gate/measure_env.sh   writes gate/results/toolchain.txt and gate/results/peak_memory.txt
# Peak resident memory is the kernel's ru_maxrss for the engine process (and its children), read by Python's
# resource module, for EPA's reference build, the TypeScript engine and the Java engine through its launcher, on
# Hydrology/sewer_rdii_problem.inp, the model behind lesson 14; and the jar run with no heap flags, which is how
# the first Java gate run (java_a/java_b) crashed on it.
# Written by Claude (Anthropic); see AI-USE.md.
set -e
HERE=$(cd "$(dirname "$0")" && pwd); ROOT=$(cd "$HERE/.." && pwd)
CORPUS=${SWMM_CORPUS:-/home/claude/swmmbobswmm6/1729-swmm5-models-2030}
{
  echo "uname -m: $(uname -m)"
  echo "kernel:   $(uname -r)"
  echo "cpu:      $(grep -m1 'model name' /proc/cpuinfo | cut -d: -f2- | sed 's/^ //')"
  for f in fma avx2 fma4; do grep -qw $f /proc/cpuinfo && echo "cpu flag: $f present" || echo "cpu flag: $f absent"; done
  echo "gcc:      $(gcc --version | sed -n 1p)"
  echo "glibc:    $(ldd --version | sed -n 1p)"
  echo "gfortran: $(gfortran --version 2>/dev/null | sed -n 1p)"
  echo "dotnet:   $(dotnet --version 2>/dev/null || echo absent)"
  echo "python:   $(python3 --version)"
  echo "node:     $(node --version)"
  echo "java:     $(java -version 2>&1 | grep -v '^Picked up' | sed -n 1p)"
  echo "javac:    $(javac -version 2>&1 | grep -v '^Picked up' | sed -n 1p)"
  echo "tsc:      $(cd "$ROOT/ts" && npx tsc --version)"
} > "$HERE/results/toolchain.txt"
cat "$HERE/results/toolchain.txt"

M=Hydrology/sewer_rdii_problem.inp
W=$(mktemp -d)
peak() {  # label, command...
  local label=$1; shift
  python3 - "$label" "$CORPUS/$(dirname $M)" "$W" "$@" <<'EOF'
import os, resource, subprocess, sys, time
label, cwd, w, cmd = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4:]
base = os.path.basename('Hydrology/sewer_rdii_problem.inp')
t = time.time()
p = subprocess.run(cmd + [base, os.path.join(w, 'r.rpt'), os.path.join(w, 'r.out')], cwd=cwd,
                   stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
kb = resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss
err = [l for l in p.stderr.decode('latin-1').splitlines() if 'Error' in l or 'error' in l][:1]
print('%-28s peak resident %5.2f GB   exit %d   %.0f s%s' % (label, kb * 1024 / 1e9, p.returncode, time.time() - t,
                                                           ('   ' + err[0].strip()[:90]) if err else ''))
EOF
}
{
  echo "Peak resident memory on $M (machine: $(free -g | awk '/^Mem:/{print $2}') GB):"
  peak "EPA 5.2.4 (ref/runswmm)" "$ROOT/ref/runswmm"
  peak "TypeScript (node)" node "$ROOT/ts/dist/runswmm.js"
  peak "Java (java/runswmm)" "$ROOT/java/runswmm"
  peak "Java (plain java -jar)" java -jar "$ROOT/java/swmm5.jar"
} > "$HERE/results/peak_memory.txt"
cat "$HERE/results/peak_memory.txt"
rm -rf "$W"
