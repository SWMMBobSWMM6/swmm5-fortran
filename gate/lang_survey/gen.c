// gen.c N : write N arguments per function and glibc's results as hex bit patterns:
// fn x y result   (y = 0 for one-argument functions). Bases log-uniform, as SWMM's pow calls are.
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <string.h>
static uint64_t s = 1729;
static double u(void) { s ^= s << 13; s ^= s >> 7; s ^= s << 17; return (s >> 11) * 0x1.0p-53; }
static uint64_t b(double d) { uint64_t r; memcpy(&r, &d, 8); return r; }
int main(int c, char **v) {
  int n = atoi(v[1]);
  for (int i = 0; i < n; i++) {
    double x = pow(10, -3 + 6 * u()), y = -3 + 6 * u();
    printf("pow %016llx %016llx %016llx\n", (unsigned long long)b(x), (unsigned long long)b(y), (unsigned long long)b(pow(x, y)));
    double e = -40 + 80 * u(); printf("exp %016llx 0 %016llx\n", (unsigned long long)b(e), (unsigned long long)b(exp(e)));
    double l = pow(10, -6 + 12 * u()); printf("log %016llx 0 %016llx\n", (unsigned long long)b(l), (unsigned long long)b(log(l)));
    printf("log10 %016llx 0 %016llx\n", (unsigned long long)b(l), (unsigned long long)b(log10(l)));
    double t = -20 + 40 * u(); printf("sin %016llx 0 %016llx\n", (unsigned long long)b(t), (unsigned long long)b(sin(t)));
    printf("cos %016llx 0 %016llx\n", (unsigned long long)b(t), (unsigned long long)b(cos(t)));
  }
  return 0;
}
