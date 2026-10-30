#!/bin/bash
# profile_go.sh - where the Go engine spends its time. Builds a copy of the engine (build/go_prof) whose main
# wraps the run in runtime/pprof (the shipped go/swmm5/main.go is not touched), runs one model and prints the
# top functions by flat and by cumulative CPU time.   gate/profile_go.sh MODEL_ID > results/go_pprof.txt
# Written by Claude (Anthropic); see AI-USE.md.
set -e
HERE=$(cd "$(dirname "$0")" && pwd); ROOT=$(cd "$HERE/.." && pwd); B=$ROOT/build/go_prof
rm -rf "$B" && mkdir -p "$B" && cp -r "$ROOT/go/go.mod" "$ROOT/go/crt" "$ROOT/go/glibm" "$ROOT/go/swmm5" "$B/"
mv "$B/swmm5/main.go" "$B/swmm5/main_orig.go.txt"
sed -e 's/^func main() {/func realMain() {/' "$B/swmm5/main_orig.go.txt" > "$B/swmm5/main.go"
cat > "$B/swmm5/prof.go" <<'GO'
package main

import (
	"os"
	"runtime/pprof"
)

func main() {
	f, err := os.Create(os.Getenv("GO_CPUPROFILE"))
	if err != nil {
		panic(err)
	}
	pprof.StartCPUProfile(f)
	realMain()
	pprof.StopCPUProfile()
	f.Close()
}
GO
(cd "$B" && GOAMD64=v1 go build -trimpath -o bin/runswmm ./swmm5)
P=$(grep -P "^$1\t" "$HERE/models_all.tsv" | cut -f2)
CORPUS=${SWMM_CORPUS:-$HERE/../../1729-SWMM5-Models-2030}
case "$P" in /*) ;; *) P=$CORPUS/$P ;; esac
W=$(mktemp -d)
(cd "$(dirname "$P")" && GO_CPUPROFILE=$W/cpu.prof "$B/bin/runswmm" "$(basename "$P")" $W/r.rpt $W/r.out > /dev/null)
echo "model: ${P##*2030/}   $(cd "$B" && go version)"
cmp -s $W/r.out "$HERE/ref_outputs/$1/r.out" && echo "profiling build's .out is identical to EPA's" || echo "profiling build's .out DIFFERS from EPA's"
(cd "$B" && go tool pprof -top -nodecount=30 bin/runswmm $W/cpu.prof 2>/dev/null)
echo
(cd "$B" && go tool pprof -top -cum -nodecount=25 bin/runswmm $W/cpu.prof 2>/dev/null | tail -n +6)
rm -rf "$W"
