#!/bin/bash
# run_java_native_control.sh - positive control for the Java port's math library.
# Builds a copy of the Java engine (build/java_native) whose Glibm class hands every call to Java's own
# Math.exp, Math.pow, ... instead of the translations of glibc, and gates it on the 40-model control set
# (smoke40.txt). Java's Math.pow disagrees with glibc's far less often than V8's (gate/results/libm_native.txt),
# so this asks whether the rare disagreements still reach the output.
#   gate/run_java_native_control.sh [IDS_FILE RUN_NAME]   (default: smoke40.txt ctl_java_native)
# Written by Claude (Anthropic); see AI-USE.md.
set -e
HERE=$(cd "$(dirname "$0")" && pwd); ROOT=$(cd "$HERE/.." && pwd)
B=$ROOT/build/java_native
rm -rf "$B" && mkdir -p "$B/src/swmm5" "$B/classes"
cp "$ROOT"/java/src/swmm5/*.java "$B/src/swmm5/"
cat > "$B/src/swmm5/Glibm.java" <<'EOF'
package swmm5;
// Control build: Java's Math in place of the glibc translations.
final class Glibm {
  private Glibm() {}
  static double exp(double x) { return Math.exp(x); }
  static double log(double x) { return Math.log(x); }
  static double log10(double x) { return Math.log10(x); }
  static double pow(double x, double y) { return Math.pow(x, y); }
  static double sin(double x) { return Math.sin(x); }
  static double cos(double x) { return Math.cos(x); }
  static double tan(double x) { return Math.tan(x); }
  static double asin(double x) { return Math.asin(x); }
  static double acos(double x) { return Math.acos(x); }
  static double atan(double x) { return Math.atan(x); }
}
EOF
rm -f "$B/src/swmm5/GlibmRt.java"
javac -nowarn -encoding ISO-8859-1 -d "$B/classes" "$B"/src/swmm5/*.java
cd "$HERE"
python3 gate.py "${2:-ctl_java_native}" "java -XX:+UseParallelGC -XX:MaxRAMPercentage=75 -cp $B/classes swmm5.Main" --ids "${1:-smoke40.txt}" -j 1 --timeout 1800
