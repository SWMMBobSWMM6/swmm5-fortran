#!/bin/bash
# lang_survey.sh - the quick survey that preceded the Go port: do Go, Perl, Ruby and Free Pascal give glibc's
# answers for SWMM's math functions and for printf? Writes gate/results/lang_survey.txt.
#   gate/lang_survey.sh          (needs gcc, go, perl, ruby, fpc)
# Math: gen.c draws 100,000 arguments per function (pow, exp, log, log10, sin, cos) and records the system
# glibc's results; each check program recomputes them with the language's own functions and counts results
# whose bits differ. printf: twenty awkward cases (cases.txt) formatted by C's snprintf (ref.c) and by each
# language's own formatter; a case counts as different when the printed text differs.
# Written by Claude (Anthropic); see AI-USE.md.
set -e
cd "$(dirname "$0")/.."
SRC=gate/lang_survey; B=build/lang_survey; OUT=gate/results/lang_survey.txt
mkdir -p $B
gcc -O2 -o $B/gen $SRC/gen.c -lm
gcc -O2 -o $B/ref $SRC/ref.c
$B/gen 100000 > $B/vec.txt
fpc -O2 -FE$B -o$B/check_fpc $SRC/check.pas > /dev/null
fpc -O2 -FE$B -o$B/checkc_fpc $SRC/checkc.pas > /dev/null
fpc -O2 -FE$B -o$B/fmt_fpc $SRC/fmtp.pas > /dev/null
$B/ref < $SRC/cases.txt > $B/printf_c.txt
go run $SRC/fmt.go < $SRC/cases.txt > $B/printf_go.txt
perl $SRC/fmt.pl < $SRC/cases.txt > $B/printf_perl.txt
ruby $SRC/fmt.rb < $SRC/cases.txt > $B/printf_ruby.txt
$B/fmt_fpc < $SRC/cases.txt > $B/printf_fpc.txt
{
  echo "Language survey: own math functions and own printf against glibc $(ldd --version | head -1 | awk '{print $NF}')"
  echo "($(go version | awk '{print $3}'), $(perl -e 'print "perl $^V"'), $(ruby -v | awk '{print "ruby", $2}'), fpc $(fpc -iV))"
  echo
  echo "Math: results whose bits differ from glibc's (100,000 arguments per function)"
  echo "-- Go math package";               go run $SRC/check.go $B/vec.txt
  echo "-- Perl (calls the C library)";    perl $SRC/check.pl $B/vec.txt
  echo "-- Ruby Math (calls the C library)"; ruby $SRC/check.rb $B/vec.txt
  echo "-- Free Pascal Math unit";         $B/check_fpc $B/vec.txt
  echo "-- Free Pascal calling glibc's libm directly"; $B/checkc_fpc $B/vec.txt
  echo
  echo "printf: cases (of $(wc -l < $SRC/cases.txt)) printed differently from C's snprintf"
  for L in go perl ruby fpc; do
    n=$(diff <(cat $B/printf_c.txt) $B/printf_$L.txt | grep -c '^>' || true)
    printf '%-5s %2d\n' $L $n
  done
  echo
  echo "C's output, then each language's lines that differ:"
  cat $B/printf_c.txt
  for L in go perl ruby fpc; do echo "-- $L"; diff $B/printf_c.txt $B/printf_$L.txt | grep '^>' | sed 's/^> //' || true; done
} > $OUT
cat $OUT
