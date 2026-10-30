#include <stdio.h>
#include <stdlib.h>
int main(void){ char f[32], x[64]; while (scanf("%31s %63s", f, x) == 2) { char o[128]; snprintf(o, sizeof o, f, strtod(x, 0)); printf("%s %s -> [%s]\n", f, x, o); } }
