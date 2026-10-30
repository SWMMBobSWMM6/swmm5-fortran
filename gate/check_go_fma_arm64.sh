#!/bin/bash
# check_go_fma_arm64.sh - the Go compiler does fuse x*y + z on arm64, unlike on x86-64. Cross-compile a
# two-function demo (go/internal/fusedemo) and the whole engine for arm64, and list the fused instructions
# (FMADDD, FMSUBD, FNMADDD, FNMSUBD) by function, with Go's own disassembler (it decodes arm64 correctly).
#   gate/check_go_fma_arm64.sh > gate/results/go_fma_arm64.txt
# Written by Claude (Anthropic); see AI-USE.md.
set -e
HERE=$(cd "$(dirname "$0")" && pwd); ROOT=$(cd "$HERE/.." && pwd); W=$(mktemp -d)
cd "$ROOT/go"
echo "$(go version); GOARCH=arm64"
GOARCH=arm64 go build -o "$W/demo" ./internal/fusedemo
echo "-- go/internal/fusedemo:"
go tool objdump -s 'main\.(plain|wrapped)' "$W/demo" | awk '/^TEXT /{print "  " $2} /\tF(N)?M(ADD|SUB|UL)D |\tFADDD /{print "      " $4, $5, $6, $7, $8}'
GOARCH=arm64 go build -trimpath -o "$W/runswmm" ./swmm5
echo "-- the engine (go/swmm5), fused instructions by function:"
go tool objdump "$W/runswmm" | awk '/^TEXT /{fn=$2} /\tF(N)?M(ADD|SUB)D /{c[fn]++; t++} END{for (f in c) printf "%5d %s\n", c[f], f; printf "%5d total\n", t}' | sort -k2
go tool objdump "$W/runswmm" | awk '/^TEXT /{fn=$2} /\tF(N)?M(ADD|SUB)D / && fn ~ /^main\./{n++} END{print "in package main (the SWMM engine): " n+0}'
rm -rf "$W"
