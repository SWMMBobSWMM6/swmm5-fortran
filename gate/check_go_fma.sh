#!/bin/bash
# check_go_fma.sh - list every fused multiply-add instruction in the Go engine binary, by function.
# The only ones allowed are in package glibm (glibc's FMA variants, via math.FMA). Go's own disassembler
# misreads VEX FMA encodings, so this uses GNU objdump.   gate/check_go_fma.sh [BINARY]
B=${1:-$(dirname "$0")/../go/bin/runswmm}
objdump -d --no-show-raw-insn "$B" | awk '/^[0-9a-f]+ <.*>:$/{fn=$2} /vfmadd|vfmsub|vfnmadd|vfnmsub/{c[fn]++; t++}
  END{for (f in c) printf "%5d %s\n", c[f], f; printf "%5d total\n", t}' | sort -k2
echo "outside glibm: $(objdump -d --no-show-raw-insn "$B" | awk '/^[0-9a-f]+ <.*>:$/{fn=$2} /vfmadd|vfmsub|vfnmadd|vfnmsub/ && fn !~ /glibm/{n++} END{print n+0}') instructions"
# the two-function demo (go/internal/fusedemo) at the default and the newest x86-64 levels
W=$(mktemp -d)
for v in v1 v3; do
  (cd "$(dirname "$0")/../go" && GOAMD64=$v go build -o "$W/demo_$v" ./internal/fusedemo)
  for f in plain wrapped; do
    echo "fusedemo GOAMD64=$v main.$f: $(objdump -d --no-show-raw-insn "$W/demo_$v" | awk -v F="<main.$f>:" '$2==F{on=1;next} /^[0-9a-f]+ <.*>:$/{on=0} on && /vfmadd|vfmsub|vfnmadd|vfnmsub/' | wc -l) fused"
  done
done
rm -rf "$W"
