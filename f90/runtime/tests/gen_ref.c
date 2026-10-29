/* gen_ref.c - glibc reference stream for the crt_format tests.
 * Written by Claude (Anthropic); see AI-USE.md.
 *
 * Writes chunks to stdout: [u32 n][n bytes of records] ... [u32 0].
 * Every case is generated from a fixed-seed PRNG, run through glibc
 * (snprintf / sscanf / strtod) and recorded together with glibc's answer.
 * test_crt_format.f90 replays the same cases through crt_format and compares bytes.
 *
 * usage: gen_ref [vals.txt]   (optional file of extra doubles, 16 hex chars little-endian per line)
 *
 * Records (little-endian):
 *   'F' u16 id u16 len bytes                       format string table entry
 *   'H' u8 group u16 count count*u16 id            format group (for V and I records)
 *   'V' u8 group u64 bits {u16 len bytes}*count    one double through every format of the group
 *   'I' u8 group u8 kind(1 int32, 2 int64) u64 v {u16 len bytes}*count
 *   'P' u16 id u8 nargs {u8 type payload}* u32 len bytes    general printf case
 *        types: 1 int32, 2 int64, 3 double(bits), 4 string(u16 len | 0xFFFF = NULL)
 *   'S' u16 id u16 inlen bytes i32 ret u8 nt {u8 type payload}*   sscanf case
 *        types: 1 int32, 2 int64, 3 double, 5 float, 6 char, 7 short, 8 schar, 4 string(u16 len bytes)
 *   'D' u8 class u16 len bytes u64 bits i32 consumed            strtod case
 *   'E'                                                         end
 *
 * Build it like the SWMM reference engine (gcc -std=gnu17, no _GNU_SOURCE): sscanf then binds
 * to glibc's C17 __isoc99_sscanf, not the C23 __isoc23_sscanf (whose %i accepts 0b prefixes).
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <math.h>
#include <float.h>

#pragma GCC diagnostic ignored "-Wformat-nonliteral"
#pragma GCC diagnostic ignored "-Wformat-security"
#pragma GCC diagnostic ignored "-Wformat"

/* ---------------------------------------------------------------- PRNG */
static uint64_t rs = 0x243F6A8885A308D3ULL;
static uint64_t rnd(void) {
  uint64_t z = (rs += 0x9E3779B97F4A7C15ULL);
  z = (z ^ (z >> 30)) * 0xBF58476D1CE4E5B9ULL;
  z = (z ^ (z >> 27)) * 0x94D049BB133111EBULL;
  return z ^ (z >> 31);
}
static double urand(void) { return (double)(rnd() >> 11) * 0x1p-53; }
static int irand(int n) { return (int)(rnd() % (uint64_t)n); }
static int chance(int pct) { return irand(100) < pct; }

/* ---------------------------------------------------------------- output */
static unsigned char cb[1 << 22];
static size_t cl;
static void flush(void) {
  uint32_t n = (uint32_t)cl;
  fwrite(&n, 4, 1, stdout);
  fwrite(cb, 1, cl, stdout);
  cl = 0;
}
static void rec(void) { if (cl > (1u << 21)) flush(); }
static void p8(unsigned v) { cb[cl++] = (unsigned char)v; }
static void p16(unsigned v) { p8(v & 255); p8((v >> 8) & 255); }
static void p32(uint32_t v) { p16(v & 0xffff); p16(v >> 16); }
static void p64(uint64_t v) { p32((uint32_t)v); p32((uint32_t)(v >> 32)); }
static void pb(const void *b, size_t n) { memcpy(cb + cl, b, n); cl += n; }
static uint64_t dbits(double x) { uint64_t b; memcpy(&b, &x, 8); return b; }
static double bitsd(uint64_t b) { double x; memcpy(&x, &b, 8); return x; }
static uint32_t fbits(float x) { uint32_t b; memcpy(&b, &x, 4); return b; }
static float bitsf(uint32_t b) { float x; memcpy(&x, &b, 4); return x; }

/* ---------------------------------------------------------------- format table */
static const char *FMT[2048];
static int nfmt;
static int deffmt(const char *f) {
  int id = nfmt++;
  FMT[id] = f;
  rec();
  p8('F'); p16(id); p16((unsigned)strlen(f)); pb(f, strlen(f));
  return id;
}
static int G[8][128], GN[8];
static void defgroup(int g, const char **list, int n) {
  GN[g] = n;
  for (int i = 0; i < n; i++) G[g][i] = deffmt(list[i]);
  rec();
  p8('H'); p8(g); p16(n);
  for (int i = 0; i < n; i++) p16(G[g][i]);
}
static int has_long(const char *f) {           /* any l / j / z / t / q / L modifier */
  for (const char *p = f; *p; p++)
    if (*p == '%') {
      p++;
      while (*p && strchr("-+ #0'I.*0123456789", *p)) p++;
      if (*p == 'l' || *p == 'j' || *p == 'z' || *p == 't' || *p == 'q' || *p == 'L') return 1;
    }
  return 0;
}

static char ob[1 << 16];

static void emit_V(int g, double x) {
  rec();
  p8('V'); p8(g); p64(dbits(x));
  for (int i = 0; i < GN[g]; i++) {
    int n = snprintf(ob, sizeof ob, FMT[G[g][i]], x);
    p16(n); pb(ob, n);
  }
}
static void emit_I(int g, int kind, int64_t v) {
  rec();
  p8('I'); p8(g); p8(kind); p64((uint64_t)v);
  for (int i = 0; i < GN[g]; i++) {
    const char *f = FMT[G[g][i]];
    int n;
    if (has_long(f)) n = snprintf(ob, sizeof ob, f, (long)v);
    else n = snprintf(ob, sizeof ob, f, (int)v);
    p16(n); pb(ob, n);
  }
}

/* general printf record: arguments described, then glibc output */
typedef struct { int t; int64_t i; double d; const char *s; } Arg;
static void emit_P(int id, Arg *a, int na, const char *out, int n) {
  rec();
  p8('P'); p16(id); p8(na);
  for (int k = 0; k < na; k++) {
    p8(a[k].t);
    switch (a[k].t) {
    case 1: p32((uint32_t)(int32_t)a[k].i); break;
    case 2: p64((uint64_t)a[k].i); break;
    case 3: p64(dbits(a[k].d)); break;
    case 4:
      if (!a[k].s) p16(0xFFFF);
      else { p16((unsigned)strlen(a[k].s)); pb(a[k].s, strlen(a[k].s)); }
      break;
    }
  }
  if (n < 0) n = (int)strlen(out);     /* glibc error (incomplete spec): what it left */
  p32(n); pb(out, n);
}

/* ---------------------------------------------------------------- doubles */
static const char *DF0[] = {"%.3f", "%.2f", "%10.3f", "%-12.4f", "%8.2f", "%.0f", "%e", "%.3e",
  "%12.4E", "%g", "%.3g", "%10.6g", "%#g", "%+.2f", "% .1f", "%010.3f", "%.6f", "%.15g", "%.17g"};
static const char *DF1[] = {"%14.3f", "%10.2f", "%7.2f", "%9.3f", "%10.4f", "%8.3f", "%6.2f",
  "%12.3f", "%5.1f", "%14.3e", "%12.3g", "%-10f", "%f", "%F", "%E", "%G", "%#.0f", "%#.0e",
  "%.0e", "%.1e", "%.10e", "%.25f", "%.20g", "%#.3g", "%-+12.3e", "%+g", "% e", "%.0g",
  "%08.3e", "%-08.3g", "%3.1f", "%.40f", "%.30e", "%#.10g", "%+010.4g", "%lf", "%.1f", "%.4f",
  "%#.2g", "%#.1g", "%#.0g", "%#G", "%#.5G", "%#12.4g",
  "%a", "%A", "%.3a", "%.0a", "%#a", "%#.0A", "%+a", "% .1a", "%015a", "%-15.2A", "%.13a", "%.20a",
  "%+#020.5a"};
#define NDF0 (int)(sizeof DF0 / sizeof *DF0)
#define NDF1 (int)(sizeof DF1 / sizeof *DF1)
static long nv;
static void dval(double x) {
  emit_V(0, x);
  if ((nv++ & 1) == 0) emit_V(1, x);
}
static double randmag(double lo10, double hi10) {
  double x = pow(10.0, lo10 + (hi10 - lo10) * urand());
  return chance(50) ? -x : x;
}

static void gen_doubles(const char *valsfile) {
  defgroup(0, DF0, NDF0);
  defgroup(1, DF1, NDF1);
  /* 1. earlier sandbox sample */
  if (valsfile) {
    FILE *f = fopen(valsfile, "r");
    if (f) {
      char h[64];
      long cnt = 0;
      while (fscanf(f, "%63s", h) == 1) {
        unsigned char b[8];
        for (int i = 0; i < 8; i++) { unsigned x; sscanf(h + 2 * i, "%2x", &x); b[i] = (unsigned char)x; }
        double d; memcpy(&d, b, 8);
        dval(d);
        cnt++;
      }
      fclose(f);
      fprintf(stderr, "gen_ref: %ld doubles from %s\n", cnt, valsfile);
    }
  }
  /* 2. random magnitudes 1e-8 .. 1e15, both signs */
  for (int i = 0; i < 300000; i++) dval(randmag(-8, 15));
  /* 3. exact binary ties */
  for (int k = 0; k <= 40000; k++) dval((chance(20) ? -k : k) / 16.0);
  for (int k = 0; k <= 20000; k++) dval((chance(20) ? -k : k) / 8.0);
  for (int k = 0; k <= 5000; k++) { dval(k / 4.0); dval(-k / 2.0); dval(k / 32.0); dval(k / 64.0); }
  for (int k = 0; k < 10000; k++) dval((double)irand(100000000) + 0.5);
  /* 4. input-like decimal spellings */
  for (int i = 0; i < 60000; i++) { double v = (double)irand(1000000000) / 1e4; dval(chance(30) ? -v : v); }
  for (int i = 0; i < 60000; i++) { double v = (double)irand(1000000000) / 1e3; dval(chance(30) ? -v : v); }
  for (int i = 0; i < 20000; i++) { double v = (double)irand(100000) / 1e4; dval(chance(30) ? -v : v); }
  for (int i = 0; i < 20000; i++) { double v = (double)irand(1000000) / 100.0; dval(chance(30) ? -v : v); }
  /* 5. specials and boundaries */
  volatile double zero = 0.0;
  double sp[] = {0.0, -0.0, INFINITY, -INFINITY, NAN, -NAN, zero / zero, -(zero / zero),
    DBL_MIN, -DBL_MIN, DBL_MAX, -DBL_MAX, DBL_TRUE_MIN, -DBL_TRUE_MIN, DBL_EPSILON,
    0.5, 1.5, 2.5, 3.5, -0.5, -2.5, 0.125, 0.375, 0.0005, 0.00049999999999999999, 0.00015,
    999999.5, 9.9999995, 99999.95, 0.0001, 0.00001, 0.000099999, 123456789012345678.0,
    1e15, 1e16, 1e17, 1e21, 1e22, 1e23, 9007199254740992.0, 9007199254740993.0,
    9223372036854775808.0, 18446744073709551616.0, 1e100, 1e-100, 1e300, 1e-300, 1e308,
    5e-324, 1e-320, 2.2250738585072009e-308, 0.1, 0.2, 0.3, 1.0 / 3, 2.0 / 3, 3.14159265358979,
    2.718281828459045, 999.9995, 99.995, 9.995, 0.995, 0.9995, 1e-5, 9.99999e-5, 0.000123456,
    123456.0, 1234567.0, 999999.0, 9999999.0, 0.00001234, 1.0, -1.0, 10.0, 100.0};
  for (size_t i = 0; i < sizeof sp / sizeof *sp; i++) dval(sp[i]);
  dval(bitsd(0x7ff8000000000001ULL)); dval(bitsd(0xfff4000000000000ULL)); dval(bitsd(0x7ff0000000000001ULL));
  /* 6. random bit patterns over the whole range */
  for (int i = 0; i < 40000; i++) dval(bitsd(rnd()));
  /* 7. subnormals */
  for (int i = 0; i < 5000; i++) dval(bitsd((rnd() >> (12 + irand(52))) | (chance(50) ? 0x8000000000000000ULL : 0)));
  /* 8. powers of ten and their neighbours; values near rounding carries */
  for (int k = -323; k <= 308; k++) {
    char s[32]; sprintf(s, "1e%d", k);
    double p = strtod(s, NULL);
    dval(p); dval(nextafter(p, INFINITY)); dval(nextafter(p, 0.0)); dval(-p);
    sprintf(s, "5e%d", k); p = strtod(s, NULL); dval(p); dval(nextafter(p, INFINITY)); dval(nextafter(p, 0.0));
    sprintf(s, "9.9999995e%d", k); p = strtod(s, NULL); dval(p);
    sprintf(s, "9.5e%d", k); p = strtod(s, NULL); dval(p);
  }
  /* 9. integers */
  for (int i = 0; i < 10000; i++) dval((double)(rnd() >> irand(64)));
  fprintf(stderr, "gen_ref: %ld doubles\n", nv);
}

/* ---------------------------------------------------------------- integers */
static const char *IF0[] = {"%d", "%5d", "%-8d", "%08d", "%+d", "%.3d", "%ld", "%lu", "%x",
  "%u", "%X", "%#x", "%#X", "%o", "%#o", "%hd", "%hhd", "%hu", "%hhu", "% d", "%.0d", "%5.3d",
  "%-+6d", "%lx", "%#lX", "%lo", "%.10ld", "%-08d", "%+08d", "%2d", "%02d", "%04d", "%3d",
  "%6ld", "%7ld", "%-5ld", "%-2ld", "%i", "%-4d", "%10d", "%6d", "%#.0o", "%#.0x", "%+.0d",
  "% .0d", "%zd", "%jd", "%lld", "%llu", "%llx", "%-#10x", "%#010x", "%#.5o", "%+5.0d", "%li",
  "%b", "%#b", "%B", "%#B", "%.4b", "%-#12b", "%#010b", "%lb", "%#lB"};
#define NIF0 (int)(sizeof IF0 / sizeof *IF0)
static void gen_ints(void) {
  defgroup(2, IF0, NIF0);
  int64_t e32[] = {0, 1, -1, 7, -7, 9, 10, -10, 99, 100, -100, 127, 128, -128, -129, 255, 256,
    32767, 32768, -32768, -32769, 65535, 65536, 999, 1000, 99999, 100000, 2147483647LL, -2147483647LL - 1};
  for (size_t i = 0; i < sizeof e32 / sizeof *e32; i++) emit_I(2, 1, e32[i]);
  for (int i = 0; i < 60000; i++) {
    int32_t v = (int32_t)(uint32_t)(rnd() >> (32 + irand(32)));
    if (chance(40)) v = -v;
    emit_I(2, 1, v);
  }
  int64_t e64[] = {0, 1, -1, 2147483647LL, 2147483648LL, -2147483648LL, -2147483649LL,
    4294967295LL, 4294967296LL, INT64_MAX, INT64_MIN, INT64_MIN + 1, 1000000000000LL,
    -999999999999LL, 0x123456789abcdefLL};
  for (size_t i = 0; i < sizeof e64 / sizeof *e64; i++) emit_I(2, 2, e64[i]);
  for (int i = 0; i < 60000; i++) {
    int64_t v = (int64_t)(rnd() >> irand(64));
    if (chance(40)) v = (int64_t)(0 - (uint64_t)v);
    emit_I(2, 2, v);
  }
}

/* ---------------------------------------------------------------- strings, stars, mixed */
static void rstr(char *s, int maxlen, int highbytes) {
  int n = irand(maxlen + 1);
  for (int i = 0; i < n; i++) {
    int c = highbytes && chance(10) ? 128 + irand(128) : 32 + irand(95);
    s[i] = (char)c;
  }
  s[n] = 0;
}
static void gen_strings(void) {
  static const char *SF[] = {"%s", "%-16s", "%16s", "%.3s", "%.10s", "%-20.5s", "%05s", "%.0s",
    "%-1s", "%.6s", "%.5s", "%20.8s", "%-s", "[%s]", "%3s|%-3s"};
  static const char *CF[] = {"%c", "%5c", "%-3c", "%05c", "[%c%c]", "%lc", "%C", "%5lc", "x%lcy%c"};
  int sid[32], cid[16];
  int ns = (int)(sizeof SF / sizeof *SF), nc = (int)(sizeof CF / sizeof *CF);
  for (int i = 0; i < ns; i++) sid[i] = deffmt(SF[i]);
  for (int i = 0; i < nc; i++) cid[i] = deffmt(CF[i]);
  char s1[64], s2[64];
  Arg a[4];
  for (int it = 0; it < 4000; it++) {
    for (int k = 0; k < ns; k++) {
      rstr(s1, 30, 1); rstr(s2, 8, 1);
      const char *x1 = chance(4) ? NULL : s1, *x2 = chance(4) ? NULL : s2;
      int n = snprintf(ob, sizeof ob, SF[k], x1, x2);
      a[0].t = 4; a[0].s = x1; a[1].t = 4; a[1].s = x2;
      emit_P(sid[k], a, strchr(SF[k] + 1, '%') ? 2 : 1, ob, n);
    }
  }
  for (int code = -300; code < 400; code++)
    for (int k = 0; k < nc; k++) {
      int c2 = irand(256) - 128;
      int n = snprintf(ob, sizeof ob, CF[k], code, c2);
      a[0].t = 1; a[0].i = code; a[1].t = 1; a[1].i = c2;
      emit_P(cid[k], a, (k == 4 || k == 8) ? 2 : 1, ob, n);
    }
}

static void gen_stars(void) {
  int f1 = deffmt("[%*d]"), f2 = deffmt("[%-*d]"), f3 = deffmt("[%.*f]"), f4 = deffmt("[%*.*f]");
  int f5 = deffmt("[%-*s]"), f6 = deffmt("[%*.*s]"), f7 = deffmt("[%.*e]"), f8 = deffmt("[%*.*g]");
  int f9 = deffmt("[%*c]"), f10 = deffmt("[%0*d]"), f11 = deffmt("[%.*d]");
  Arg a[4];
  char s[64];
  for (int it = 0; it < 20000; it++) {
    int w = irand(61) - 30, p = irand(26) - 5, iv = (int)(rnd() >> (32 + irand(32))) * (chance(50) ? -1 : 1);
    double d = randmag(-10, 12);
    int n;
    rstr(s, 20, 0);
    a[0].t = 1; a[0].i = w; a[1].t = 1; a[1].i = iv;
    n = snprintf(ob, sizeof ob, FMT[f1], w, iv); emit_P(f1, a, 2, ob, n);
    n = snprintf(ob, sizeof ob, FMT[f2], w, iv); emit_P(f2, a, 2, ob, n);
    n = snprintf(ob, sizeof ob, FMT[f10], w, iv); emit_P(f10, a, 2, ob, n);
    a[0].i = p; n = snprintf(ob, sizeof ob, FMT[f11], p, iv); emit_P(f11, a, 2, ob, n);
    a[0].t = 1; a[0].i = p; a[1].t = 3; a[1].d = d;
    n = snprintf(ob, sizeof ob, FMT[f3], p, d); emit_P(f3, a, 2, ob, n);
    n = snprintf(ob, sizeof ob, FMT[f7], p, d); emit_P(f7, a, 2, ob, n);
    a[0].i = w; a[1].t = 1; a[1].i = p; a[2].t = 3; a[2].d = d;
    n = snprintf(ob, sizeof ob, FMT[f4], w, p, d); emit_P(f4, a, 3, ob, n);
    n = snprintf(ob, sizeof ob, FMT[f8], w, p, d); emit_P(f8, a, 3, ob, n);
    a[0].i = w; a[1].t = 4; a[1].s = s;
    n = snprintf(ob, sizeof ob, FMT[f5], w, s); emit_P(f5, a, 2, ob, n);
    a[1].t = 1; a[1].i = p; a[2].t = 4; a[2].s = chance(5) ? NULL : s;
    n = snprintf(ob, sizeof ob, FMT[f6], w, p, a[2].s); emit_P(f6, a, 3, ob, n);
    a[1].t = 1; a[1].i = 33 + irand(90);
    n = snprintf(ob, sizeof ob, FMT[f9], w, (int)a[1].i); emit_P(f9, a, 2, ob, n);
  }
}

static void gen_mixed(void) {
  int m1 = deffmt("\n  %-20s %14.3f %14.3f %14.3f");
  int m2 = deffmt("  %-16s %10.2f %10.2f %9.3f %8.3f");
  int m3 = deffmt("%02d/%02d/%04d  %02d:%02d:%02d");
  int m4 = deffmt("\n  %-20s %8s %8s %4d %4d");
  int m5 = deffmt("%9.3f %9.3f%9.3f %7.2f %5.1f");
  int m6 = deffmt("Node %s surcharged %d%% of time");
  int m7 = deffmt("%-10s %6ld %4d");
  int m8 = deffmt("  %-30s %12.3f %%");
  int m9 = deffmt("%14.3e %12.3g %10.4f");
  int m10 = deffmt("\n  %s  %-*s %*.*f");
  int m11 = deffmt("%s|%c|%d|%ld|%u|%x|%e|%g|%f|%s");
  Arg a[12];
  char s1[64], s2[64], s3[64];
  int n;
  for (int it = 0; it < 20000; it++) {
    double d[6];
    for (int k = 0; k < 6; k++) d[k] = randmag(-6, 9);
    int iv[6];
    for (int k = 0; k < 6; k++) iv[k] = irand(3000) - 100;
    rstr(s1, 24, 0); rstr(s2, 10, 0); rstr(s3, 10, 0);
    a[0].t = 4; a[0].s = s1;
    for (int k = 0; k < 3; k++) { a[1 + k].t = 3; a[1 + k].d = d[k]; }
    n = snprintf(ob, sizeof ob, FMT[m1], s1, d[0], d[1], d[2]); emit_P(m1, a, 4, ob, n);
    a[4].t = 3; a[4].d = d[3];
    n = snprintf(ob, sizeof ob, FMT[m2], s1, d[0], d[1], d[2], d[3]); emit_P(m2, a, 5, ob, n);
    for (int k = 0; k < 6; k++) { a[k].t = 1; a[k].i = iv[k]; }
    n = snprintf(ob, sizeof ob, FMT[m3], iv[0], iv[1], iv[2], iv[3], iv[4], iv[5]); emit_P(m3, a, 6, ob, n);
    a[0].t = 4; a[0].s = s1; a[1].t = 4; a[1].s = s2; a[2].t = 4; a[2].s = s3; a[3].t = 1; a[3].i = iv[0];
    a[4].t = 1; a[4].i = iv[1];
    n = snprintf(ob, sizeof ob, FMT[m4], s1, s2, s3, iv[0], iv[1]); emit_P(m4, a, 5, ob, n);
    for (int k = 0; k < 5; k++) { a[k].t = 3; a[k].d = d[k]; }
    n = snprintf(ob, sizeof ob, FMT[m5], d[0], d[1], d[2], d[3], d[4]); emit_P(m5, a, 5, ob, n);
    a[0].t = 4; a[0].s = s2; a[1].t = 1; a[1].i = iv[2];
    n = snprintf(ob, sizeof ob, FMT[m6], s2, iv[2]); emit_P(m6, a, 2, ob, n);
    long lv = (long)(rnd() >> 40) - 1000;
    a[0].t = 4; a[0].s = s3; a[1].t = 2; a[1].i = lv; a[2].t = 1; a[2].i = iv[3];
    n = snprintf(ob, sizeof ob, FMT[m7], s3, lv, iv[3]); emit_P(m7, a, 3, ob, n);
    a[0].t = 4; a[0].s = s1; a[1].t = 3; a[1].d = d[5];
    n = snprintf(ob, sizeof ob, FMT[m8], s1, d[5]); emit_P(m8, a, 2, ob, n);
    for (int k = 0; k < 3; k++) { a[k].t = 3; a[k].d = d[k + 2]; }
    n = snprintf(ob, sizeof ob, FMT[m9], d[2], d[3], d[4]); emit_P(m9, a, 3, ob, n);
    int w1 = irand(30) - 5, w2 = irand(16), p2 = irand(8);
    a[0].t = 4; a[0].s = s2; a[1].t = 1; a[1].i = w1; a[2].t = 4; a[2].s = s3;
    a[3].t = 1; a[3].i = w2; a[4].t = 1; a[4].i = p2; a[5].t = 3; a[5].d = d[0];
    n = snprintf(ob, sizeof ob, FMT[m10], s2, w1, s3, w2, p2, d[0]); emit_P(m10, a, 6, ob, n);
    a[0].t = 4; a[0].s = s1; a[1].t = 1; a[1].i = 33 + irand(90); a[2].t = 1; a[2].i = iv[4];
    a[3].t = 2; a[3].i = lv; a[4].t = 1; a[4].i = iv[5]; a[5].t = 1; a[5].i = iv[1];
    a[6].t = 3; a[6].d = d[1]; a[7].t = 3; a[7].d = d[2]; a[8].t = 3; a[8].d = d[3]; a[9].t = 4; a[9].s = s2;
    n = snprintf(ob, sizeof ob, FMT[m11], s1, (int)a[1].i, iv[4], lv, (unsigned)iv[5], (unsigned)iv[1],
                 d[1], d[2], d[3], s2);
    emit_P(m11, a, 10, ob, n);
  }
  /* oddities: unknown conversions, incomplete specs, ignored flags and modifiers */
  static const char *OF[] = {"a%yb", "a%5.2yb", "[%-#05.3ly]", "x%%y", "%5%|%-5%", "tail%",
    "tail%-", "tail%5", "tail%.", "tail%l", "a%hhhd", "a%lld|%llld", "[% +d]", "[%+ d]",
    "[%-0+#5d]", "[%I5d]", "[%'d]", "[%'.2f]", "[%lf]", "[%hf]", "[%zu]", "[%td]", "[%qd]",
    "[%jd]", "[%Zd]", "[%lc]", "[%C]", "[%5.3k]", "[%#'+ -0I8.4r]", "%%%", "[%.f]", "[%.e]",
    "[%5.d]", "[%-.3s]", "[%010s]", "[%-010.2f]", "[%+-8.3e]"};
  for (size_t k = 0; k < sizeof OF / sizeof *OF; k++) {
    int id = deffmt(OF[k]);
    for (int it = 0; it < 50; it++) {
      int i1 = irand(2000) - 1000, i2 = irand(2000) - 1000;
      double dd = randmag(-3, 6);
      const char *f = OF[k];
      int n2;
      /* pick argument kinds from the spec letters */
      if (strstr(f, "f]") || strstr(f, "e]")) {
        a[0].t = 3; a[0].d = dd;
        n2 = snprintf(ob, sizeof ob, f, dd);
        emit_P(id, a, 1, ob, n2);
      } else if (strstr(f, "s]")) {
        rstr(s1, 12, 0);
        a[0].t = 4; a[0].s = s1;
        n2 = snprintf(ob, sizeof ob, f, s1);
        emit_P(id, a, 1, ob, n2);
      } else if (strstr(f, "ll") || strstr(f, "%jd") || strstr(f, "%zu") || strstr(f, "%td") ||
                 strstr(f, "%qd") || strstr(f, "%Zd")) {
        a[0].t = 2; a[0].i = (int64_t)(rnd() >> 3) * (chance(50) ? -1 : 1); a[1].t = 2; a[1].i = i2;
        n2 = snprintf(ob, sizeof ob, f, (long)a[0].i, (long)a[1].i);
        emit_P(id, a, 2, ob, n2);
      } else if (strstr(f, "%lc") || strstr(f, "%C")) {
        a[0].t = 1; a[0].i = 33 + irand(90);
        n2 = snprintf(ob, sizeof ob, f, (int)a[0].i);
        emit_P(id, a, 1, ob, n2);
      } else {
        a[0].t = 1; a[0].i = i1; a[1].t = 1; a[1].i = i2;
        n2 = snprintf(ob, sizeof ob, f, i1, i2);
        emit_P(id, a, 2, ob, n2);
      }
    }
  }
}

/* ---------------------------------------------------------------- sscanf */
typedef struct { int t; int width; } TT;
static int scan_targets(const char *f, TT *t) {
  int n = 0;
  for (const char *p = f; *p; p++) {
    if (*p != '%') continue;
    p++;
    if (*p == '%') continue;
    int sup = 0;
    while (*p == '*' || *p == '\'' || *p == 'I') { if (*p == '*') sup = 1; p++; }
    int w = 0;
    while (*p >= '0' && *p <= '9') w = w * 10 + (*p++ - '0');
    int len = 0;               /* 1 hh, 2 h, 3 l, 4 ll/L/q, 5 j/z/t */
    if (*p == 'h') { p++; if (*p == 'h') { p++; len = 1; } else len = 2; }
    else if (*p == 'l') { p++; if (*p == 'l') { p++; len = 4; } else len = 3; }
    else if (*p == 'L' || *p == 'q') { p++; len = 4; }
    else if (*p == 'j' || *p == 'z' || *p == 't') { p++; len = 5; }
    char c = *p;
    if (!c) break;
    if (sup) continue;
    int ty = 0;
    if (strchr("diuxXonb", c)) ty = len == 1 ? 8 : len == 2 ? 7 : len >= 3 ? 2 : 1;
    else if (strchr("eEfFgGaA", c)) ty = len >= 3 ? 3 : 5;
    else if (c == 's' || c == 'S') ty = 4;
    else if (c == 'c' || c == 'C') ty = w > 1 ? 4 : 6;
    if (ty) { t[n].t = ty; t[n].width = w; n++; }
  }
  return n;
}
union TV { int i; long l; double d; float f; char c; short h; signed char hh; char s[256]; };
static void emit_S(int id, const char *in) {
  TT t[16];
  int nt = scan_targets(FMT[id], t);
  union TV v[12];
  for (int k = 0; k < 12; k++) { memset(&v[k], 0x5A, sizeof v[k]); v[k].s[255] = 0; }
  int r = sscanf(in, FMT[id], &v[0], &v[1], &v[2], &v[3], &v[4], &v[5], &v[6], &v[7], &v[8],
                 &v[9], &v[10], &v[11]);
  rec();
  p8('S'); p16(id); p16((unsigned)strlen(in)); pb(in, strlen(in)); p32((uint32_t)r); p8(nt);
  for (int k = 0; k < nt; k++) {
    p8(t[k].t);
    switch (t[k].t) {
    case 1: p32((uint32_t)v[k].i); break;
    case 2: p64((uint64_t)v[k].l); break;
    case 3: p64(dbits(v[k].d)); break;
    case 5: p32(fbits(v[k].f)); break;
    case 6: p8((unsigned char)v[k].c); break;
    case 7: p16((unsigned short)v[k].h); break;
    case 8: p8((unsigned char)v[k].hh); break;
    case 4: { size_t n = strnlen(v[k].s, 255); p16((unsigned)n); pb(v[k].s, n); } break;
    }
  }
}

static const char *ALNUM = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789";
static void app(char *s, const char *x) { strcat(s, x); }
static void appc(char *s, int c) { size_t n = strlen(s); s[n] = (char)c; s[n + 1] = 0; }
static void rint_tok(char *s, int width) {
  if (chance(15)) appc(s, chance(50) ? '-' : '+');
  int nd = width > 0 && chance(60) ? width - irand(2) : irand(13);
  if (chance(5)) { app(s, "0x1f"); return; }
  for (int i = 0; i < nd; i++) appc(s, '0' + irand(10));
  if (nd == 0 && chance(50)) appc(s, ALNUM[irand(52)]);
}
static void rnum_spelling(char *s, int maxdig, int e_lo, int e_hi);
static void rflt_tok(char *s) {
  int r = irand(100);
  if (r < 3) { app(s, chance(50) ? "inf" : "nan"); return; }
  if (r < 4) { app(s, "infinity"); return; }
  if (r < 5) { app(s, "0x1.8p3"); return; }
  if (r < 7) { app(s, chance(50) ? "-" : "."); return; }
  rnum_spelling(s, 12, -12, 12);
}
static void rword(char *s, int width) {
  int n = width > 0 && chance(50) ? width + irand(3) - 1 : irand(9);
  for (int i = 0; i < n; i++) appc(s, chance(85) ? ALNUM[irand(62)] : "!*#.,:;-/"[irand(9)]);
}
static void gen_input(const char *f, char *in) {
  in[0] = 0;
  if (chance(8)) {        /* free random text */
    int n = irand(30);
    const char *al = "0123456789 +-.:,eExXabSWM5\t*";
    for (int i = 0; i < n; i++) appc(in, al[irand((int)strlen(al))]);
    return;
  }
  if (chance(10)) for (int i = irand(3); i > 0; i--) appc(in, ' ');
  for (const char *p = f; *p; p++) {
    if (*p == ' ' || *p == '\t' || *p == '\n') {
      int k = irand(4);
      for (int i = 0; i < k; i++) appc(in, chance(80) ? ' ' : (chance(50) ? '\t' : '\n'));
      continue;
    }
    if (*p != '%') {
      int r = irand(100);
      if (r < 90) appc(in, *p);
      else if (r < 95) appc(in, ALNUM[irand(62)]);
      continue;
    }
    p++;
    if (*p == '%') { appc(in, '%'); continue; }
    while (*p == '*') p++;
    int w = 0;
    while (*p >= '0' && *p <= '9') w = w * 10 + (*p++ - '0');
    while (*p == 'l' || *p == 'h' || *p == 'L') p++;
    if (chance(15)) appc(in, ' ');
    switch (*p) {
    case 'd': case 'i': case 'u': case 'x': case 'o': rint_tok(in, w); break;
    case 'b':
      if (chance(10)) appc(in, chance(50) ? '-' : '+');
      if (chance(40)) app(in, chance(50) ? "0b" : "0B");
      for (int i = irand(12); i > 0; i--) appc(in, chance(95) ? '0' + irand(2) : '2');
      break;
    case 'f': case 'e': case 'g': rflt_tok(in); break;
    case 's': rword(in, w); break;
    case 'c': appc(in, chance(80) ? ALNUM[irand(62)] : " .-*"[irand(4)]); break;
    default: break;
    }
    if (*p == 0) break;
    if (chance(10)) appc(in, ' ');
  }
  size_t n = strlen(in);
  if (n > 0 && chance(20)) in[irand((int)n)] = 0;
  if (chance(8)) app(in, " junk");
}

static const char *SSF[] = {" %2d%2d %6ld %c %c", " %2d:%2d", "%2d %4s %2s %4d", "%2d%2d%6ld%c%c",
  "%2d,%4s,%2s,%4d", "%3s%6ld%2d%4s", "%3s%c%d%c%d", "%4d %2d %2d", "%4d%2d", "%4d%2d%2d",
  "%4d%2d%4d%3d", "%4d,%2d,%2d", "%5s%6ld", "%6ld %2d %4s", "%6ld%c", "%6ld,%2d,%4s",
  "%7ld%3d%2d%2d%3d", "%7ld%4d%2d%2d%3d", "%8lf", "%d", "%d%c%3s%c%d", "%d%c%d%c%d",
  "%d:%d:%d", "%f %c", "%ld %c", "%s %d %d %d %d %d %d %lf", "%s %d %d %d %d %d %f",
  "%s %d %d %d %s %s %s %s", "%s %d %d %d %s", "%s %d %d", "%s %s %s", "%s %s", "%s",
  ",%2d%2d,%6ld,%c,%c", "SWMM5",
  /* extras */
  "%lf", "%f", "%3lf", "%5f", "%d%n", "%i %x %o", "%u", "%hd", "%5c", "%*d %d", "%*s %s",
  "%%%d", " %c%c", "%lf%s", "%f%s", "%e %g %E", "%lu %lx", "%hhd%hhu", "%2s%3c",
  "%b%s", "%3b %i", "%i%s", "%lb"};
#define NSSF (int)(sizeof SSF / sizeof *SSF)
static int ssf_id[NSSF];

static void gen_sscanf_structured(void) {
  char in[512];
  for (int k = 0; k < NSSF; k++) ssf_id[k] = deffmt(SSF[k]);
  for (int k = 0; k < NSSF; k++) {
    emit_S(ssf_id[k], "");
    emit_S(ssf_id[k], "   ");
    for (int it = 0; it < 4000; it++) {
      gen_input(SSF[k], in);
      emit_S(ssf_id[k], in);
    }
  }
}

/* ---------------------------------------------------------------- strtod */
static void emit_D(int cls, const char *s) {
  char *end;
  double d = strtod(s, &end);
  rec();
  p8('D'); p8(cls); p16((unsigned)strlen(s)); pb(s, strlen(s)); p64(dbits(d)); p32((uint32_t)(end - s));
}
static void rnum_spelling(char *s, int maxdig, int e_lo, int e_hi) {
  int nd = 1 + irand(maxdig);
  int dotpos = chance(25) ? -1 : irand(nd + 1);
  if (chance(10)) app(s, "0.");
  if (chance(5)) for (int i = irand(5); i > 0; i--) appc(s, '0');
  for (int i = 0; i < nd; i++) {
    if (i == dotpos) appc(s, '.');
    appc(s, '0' + (i == 0 && chance(80) ? 1 + irand(9) : irand(10)));
  }
  if (dotpos == nd) appc(s, '.');
  if (chance(70)) {
    appc(s, chance(50) ? 'e' : 'E');
    int r = irand(3);
    if (r == 1) appc(s, '+');
    char t[16];
    int ev = e_lo + irand(e_hi - e_lo + 1);
    if (r == 0 && ev >= 0) sprintf(t, "%d", ev); else if (ev < 0) sprintf(t, "%d", ev); else sprintf(t, "%d", ev);
    if (r != 0 && ev < 0) { /* "+-" is not an exponent: keep it to test the fallback */ }
    app(s, t);
  }
}
static const char *JUNK[] = {"", "", "", "x", " ", "e", "e+", "E-", ".5", "abc", ",", "\n", "f", "p3", "..", "e+5x"};
static void gen_strtod(void) {
  char s[4096];
  /* 1. random decimal spellings */
  for (int i = 0; i < 130000; i++) {
    s[0] = 0;
    for (int k = irand(4); k > 0 && chance(30); k--) appc(s, " \t\n"[irand(3)]);
    if (chance(40)) appc(s, chance(50) ? '-' : '+');
    rnum_spelling(s, 25, -330, 310);
    app(s, JUNK[irand(16)]);
    emit_D(1, s);
  }
  /* 2. exact halfway points between adjacent doubles, and just above / below */
  for (int i = 0; i < 12000; i++) {
    double a;
    if (i % 4 == 0) a = bitsd(rnd() >> (12 + irand(52)));         /* subnormal */
    else do a = bitsd(rnd() & 0x7fffffffffffffffULL); while (!isfinite(a) || a == DBL_MAX);
    double b = nextafter(a, INFINITY);
    long double mid = ((long double)a + (long double)b) / 2;
    char t[2400];
    snprintf(t, sizeof t, "%.1100Le", mid);
    char *e = strchr(t, 'e');
    char ex[16]; strcpy(ex, e); *e = 0;
    size_t L = strlen(t);
    while (t[L - 1] == '0') t[--L] = 0;
    if (t[L - 1] == '.') t[--L] = 0;
    snprintf(s, sizeof s, "%s%s", t, ex);                   emit_D(2, s);
    snprintf(s, sizeof s, "%s%s1%s", t, strchr(t, '.') ? "" : ".", ex); emit_D(2, s);
    size_t cut = 3 + irand((int)(L > 40 ? 40 : L));
    if (cut < L) { char u[64]; memcpy(u, t, cut); u[cut] = 0; snprintf(s, sizeof s, "%s%s", u, ex); emit_D(2, s); }
  }
  /* 3. specials */
  static const char *SP[] = {"1e", "1e+", "1e-", "1E+x", ".5", "5.", "-.", ".", "-", "+", "", " ",
    "inf", "-inf", "+INF", "Infinity", "infinityx", "infin", "INFINITE", "iNfInItY", "in", "nan",
    "-nan", "NaN", "nan()", "nan(123)", "nan(0x1f)", "nan(0X1F)", "nan(abc)", "nan(abc", "nan(-1)",
    "nan(1_2)", "nan(077)", "nan(099)", "nan(99999999999999999999999)", "nan(0x)", "nan(0xfffffffffffff)",
    "nan(0x8000000000000)", "-nan(5)", "nanx", "0x", "0x.", "0x.8", "0X1P-3", "0x1.8p3", "0x1p",
    "0x1p+", "0xp1", "0x0p1", "-0x", "0x1.fffffffffffff8p1023", "0x1.fffffffffffff7p1023",
    "0x1p-1074", "0x1p-1075", "0x1.8p-1075", "0x3p-1076", "0x123456789abcdef0123p-80", "0x0.0",
    "0x00000.00001p0", "0xG", "0x1.ffffffffffffffffffffffffffp0", "0x1.00000000000008p0",
    "0x1.000000000000080000000001p0", "0x1.00000000000018p0", "1e400", "1e-400", "0e9999999999",
    "0.0e100000", "1e99999999999999999999", "-1e-99999999999999999999", "4.9406564584124654e-324",
    "2.4703282292062327e-324", "2.4703282292062328e-324", "2.2250738585072011e-308",
    "2.2250738585072012e-308", "2.2250738585072014e-308", "1.7976931348623157e308",
    "1.7976931348623158e308", "1.7976931348623159e308", "179769313486231580793728971405301e276",
    "000000000000001", "0000.0000", "-0", "+0.0e5", "1.e5", " \t\n\v\f\r42", "\v1", "0e", "00e+",
    "123456789012345678901234567890", "0.000000000000000000000000000001", "9007199254740993",
    "9007199254740992.5", "9007199254740993.0000000000000000000001", "1.5e-45", "7e-46",
    "3.4028235677973366e38", "1e23", "8.98846567431158e307", "5e-324", "3e-324", "2e-324",
    "1e-323", "1E1", "1e01", "1e-0", "-0e-0", "0.", "00.00e-00", "1_000", "1,5", "0x1,8p3"};
  for (size_t i = 0; i < sizeof SP / sizeof *SP; i++) emit_D(3, SP[i]);
  /* 4. random hex floats */
  for (int i = 0; i < 20000; i++) {
    s[0] = 0;
    if (chance(30)) appc(s, '-');
    app(s, chance(50) ? "0x" : "0X");
    int nd = irand(22), dot = chance(40) ? irand(nd + 1) : -1;
    for (int k = 0; k < nd; k++) { if (k == dot) appc(s, '.'); appc(s, "0123456789abcdefABCDEF"[irand(22)]); }
    if (chance(70)) { char t[16]; sprintf(t, "%c%d", chance(50) ? 'p' : 'P', irand(2300) - 1150); app(s, t); }
    app(s, JUNK[irand(16)]);
    emit_D(4, s);
  }
  /* 5. subnormal and boundary decimals */
  for (int i = 0; i < 20000; i++) {
    s[0] = 0;
    rnum_spelling(s, 20, -330, -300);
    emit_D(5, s);
    s[0] = 0;
    char t[64];
    int nd = 1 + irand(19);
    for (int k = 0; k < nd; k++) appc(s, '0' + (k == 0 ? 1 + irand(9) : irand(10)));
    sprintf(t, "e%d", 300 + irand(12) - nd);
    app(s, t);
    emit_D(5, s);
  }
  /* 6. long digit strings */
  for (int i = 0; i < 2000; i++) {
    s[0] = 0;
    int nd = 30 + irand(1200);
    if (chance(50)) app(s, "0.");
    for (int k = 0; k < nd; k++) appc(s, '0' + (k == 0 ? 1 + irand(9) : (chance(50) ? 0 : irand(10))));
    char t[16]; sprintf(t, "e%d", irand(1400) - 1000); app(s, t);
    emit_D(6, s);
  }
  /* 7. short junk */
  const char *al = "0123456789.eE+-xXpPinfatyINFATY() \t_";
  for (int i = 0; i < 20000; i++) {
    s[0] = 0;
    int n = irand(12);
    for (int k = 0; k < n; k++) appc(s, al[irand((int)strlen(al))]);
    emit_D(7, s);
  }
}

/* sscanf %f / %lf over number spellings, including float halfway points */
static void gen_scan_numbers(void) {
  int idlf = ssf_id[35], idf = ssf_id[36], idlfs = ssf_id[48], idfs = ssf_id[49], id3 = ssf_id[37], id5 = ssf_id[38];
  char s[4096];
  for (int i = 0; i < 40000; i++) {
    s[0] = 0;
    if (chance(40)) appc(s, chance(50) ? '-' : '+');
    rnum_spelling(s, 25, -60, 50);
    app(s, JUNK[irand(16)]);
    emit_S(idlf, s); emit_S(idf, s); emit_S(idlfs, s); emit_S(idfs, s); emit_S(id3, s); emit_S(id5, s);
  }
  for (int i = 0; i < 15000; i++) {
    float a;
    if (i % 4 == 0) a = bitsf((uint32_t)(rnd() >> (41 + irand(23))));
    else do a = bitsf((uint32_t)rnd() & 0x7fffffffu); while (!isfinite(a) || a == FLT_MAX);
    float b = nextafterf(a, INFINITY);
    double mid = ((double)a + (double)b) / 2;
    char t[512];
    snprintf(t, sizeof t, "%.300e", mid);
    char *e = strchr(t, 'e');
    char ex[16]; strcpy(ex, e); *e = 0;
    size_t L = strlen(t);
    while (t[L - 1] == '0') t[--L] = 0;
    if (t[L - 1] == '.') t[--L] = 0;
    snprintf(s, sizeof s, "%s%s", t, ex); emit_S(idf, s); emit_S(idlf, s);
    snprintf(s, sizeof s, "%s%s1%s", t, strchr(t, '.') ? "" : ".", ex); emit_S(idf, s);
    size_t cut = 3 + irand((int)(L > 20 ? 20 : L));
    if (cut < L) { char u[64]; memcpy(u, t, cut); u[cut] = 0; snprintf(s, sizeof s, "%s%s", u, ex); emit_S(idf, s); }
  }
  static const char *SP[] = {"inf", "-inf", "infinity", "infinx", "infin", "nan", "-nan", "nan(12)",
    "NAN", "-", "+", ".", "-.", "0x", "0x1p3", "0xg", "1e", "1e+", "1ex", "3.4028235e38",
    "3.40282357e38", "3.4028236e38", "1e39", "1.4e-45", "7e-46", "7.1e-46", "1e-46", "0", "-0"};
  for (size_t i = 0; i < sizeof SP / sizeof *SP; i++) {
    emit_S(idlf, SP[i]); emit_S(idf, SP[i]); emit_S(idlfs, SP[i]); emit_S(idfs, SP[i]);
  }
}

int main(int argc, char **argv) {
  gen_doubles(argc > 1 ? argv[1] : NULL);
  gen_ints();
  gen_strings();
  gen_stars();
  gen_mixed();
  gen_sscanf_structured();
  gen_scan_numbers();
  gen_strtod();
  rec();
  p8('E');
  flush();
  uint32_t z = 0;
  fwrite(&z, 4, 1, stdout);
  fflush(stdout);
  fprintf(stderr, "gen_ref: %d formats\n", nfmt);
  return 0;
}
