#!/bin/bash
# go_powtime.sh - nanoseconds per call of pow, sin and cos: the system glibc (tools/libm/test/powtime.c), the Go
# port's translations as shipped (each GIMPLE block a label, edges as goto), the same translations in the
# dispatch-loop shape the TypeScript and Java ports use (gim2x.py --go-loop, built in a scratch copy), and Go's
# own math package. Same 2,000,000 arguments for all.   gate/go_powtime.sh [GLIBM_WORKDIR] > results/go_powtime.txt
# GLIBM_WORKDIR holds gimple/ and tables.json from tools/libm/build_glibm.sh and extract_tables.py.
# Written by Claude (Anthropic); see AI-USE.md.
set -e
HERE=$(cd "$(dirname "$0")" && pwd); ROOT=$(cd "$HERE/.." && pwd); W=${1:-$ROOT/build/glibm}; T=$(mktemp -d)
G=$W/gimple
DUMPS="$G/e_exp.c.254t.optimized $G/e_log.c.254t.optimized $G/e_pow.c.254t.optimized $G/s_sin.c.254t.optimized
       $G/s_tan.c.254t.optimized $G/e_asin.c.254t.optimized $G/s_atan.c.254t.optimized $G/e_log10.c.254t.optimized"
echo "# ns per call, 2,000,000 arguments (x in 0.001-100; y = 2/3, 5/3 or uniform -4..4), third of three passes; $(go version | awk '{print $3}'), $(gcc --version | sed -n 1p | awk '{print $1, $NF}') -O2"
gcc -O2 -o "$T/powtime" "$ROOT/tools/libm/test/powtime.c" -lm && "$T/powtime"
(cd "$ROOT/go" && go run ./internal/powtime)
mkdir -p "$T/m/glibm" "$T/m/internal" && cp "$ROOT/go/go.mod" "$T/m/" && cp "$ROOT/go/glibm/glibm_rt.go" "$T/m/glibm/"
cp -r "$ROOT/go/internal/powtime" "$T/m/internal/"
python3 "$ROOT/tools/libm/gim2x.py" go "$T/m/glibm/glibm.go" $DUMPS --tables "$W/tables.json" --name my_exp_fma=Exp \
    --name my_log=Log --name my_pow=Pow --name my_sin=Sin --name my_cos=Cos --name my_tan=Tan --name my_asin=ieee754_asin \
    --name my_acos=ieee754_acos --name my_atan=Atan --name my_log10=ieee754_log10 --go-loop > /dev/null
(cd "$T/m" && go run ./internal/powtime "Go glibm, dispatch loop" nomath)
rm -rf "$T"
