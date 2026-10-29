#!/bin/bash
# run_ts_native_control.sh - positive control for the TypeScript port's math library.
# Builds a copy of the TypeScript engine (build/ts_native) whose glibm module hands every call to
# JavaScript's own Math.exp, Math.pow, ... instead of the translations of glibc, and gates it on the
# 40-model control set (smoke40.txt). If carrying glibc along matters, this copy should differ from EPA
# on some of those models; the shipped engine is identical on all 480.
#   gate/run_ts_native_control.sh [IDS_FILE RUN_NAME]   (default: smoke40.txt ctl_ts_native; after `npm run build` in ts/)
# Written by Claude (Anthropic); see AI-USE.md.
set -e
HERE=$(cd "$(dirname "$0")" && pwd); ROOT=$(cd "$HERE/.." && pwd)
B=$ROOT/build/ts_native
rm -rf "$B" && mkdir -p "$B" && cp "$ROOT"/ts/dist/*.js "$B/"
cat > "$B/glibm.js" <<'EOF'
"use strict";
// Control build: V8's Math in place of the glibc translations.
Object.defineProperty(exports, "__esModule", { value: true });
for (const f of ["exp", "log", "log10", "pow", "sin", "cos", "tan", "asin", "acos", "atan"]) exports[f] = Math[f];
EOF
cd "$HERE"
python3 gate.py "${2:-ctl_ts_native}" "node $B/runswmm.js" --ids "${1:-smoke40.txt}" -j 1 --timeout 1800
