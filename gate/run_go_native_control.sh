#!/bin/bash
# run_go_native_control.sh - positive control for the Go port's math library.
# Builds a copy of the Go engine (build/go_native) whose glibm package hands every call to Go's own
# math.Exp, math.Pow, ... instead of the translations of glibc, and gates it. Go's math package is its own
# port of FreeBSD/Cephes code and disagrees with glibc far more often than Java's StrictMath does
# (scratchpad survey: pow differs on 45,738 of 100,000 arguments), so this asks how much of the output moves.
#   gate/run_go_native_control.sh [IDS_FILE RUN_NAME]   (default: smoke40.txt ctl_go_native)
# Written by Claude (Anthropic); see AI-USE.md.
set -e
HERE=$(cd "$(dirname "$0")" && pwd); ROOT=$(cd "$HERE/.." && pwd)
B=$ROOT/build/go_native
rm -rf "$B" && mkdir -p "$B"
cp -r "$ROOT/go/go.mod" "$ROOT/go/crt" "$ROOT/go/swmm5" "$B/"
mkdir -p "$B/glibm"
cat > "$B/glibm/glibm.go" <<'GO'
// Control build: Go's math package in place of the glibc translations.
package glibm

import "math"

func Exp(x float64) float64          { return math.Exp(x) }
func Log(x float64) float64          { return math.Log(x) }
func Log10(x float64) float64        { return math.Log10(x) }
func Pow(x, y float64) float64       { return math.Pow(x, y) }
func Sin(x float64) float64          { return math.Sin(x) }
func Cos(x float64) float64          { return math.Cos(x) }
func Tan(x float64) float64          { return math.Tan(x) }
func Asin(x float64) float64         { return math.Asin(x) }
func Acos(x float64) float64         { return math.Acos(x) }
func Atan(x float64) float64         { return math.Atan(x) }
func Fabs(x float64) float64         { return math.Abs(x) }
func Sqrt(x float64) float64         { return math.Sqrt(x) }
func Floor(x float64) float64        { return math.Floor(x) }
func Ceil(x float64) float64         { return math.Ceil(x) }
GO
(cd "$B" && GOAMD64=v1 go build -trimpath -o bin/runswmm ./swmm5)
cd "$HERE"
python3 gate.py "${2:-ctl_go_native}" "$B/bin/runswmm" --ids "${1:-smoke40.txt}" -j 1 --timeout 1800
