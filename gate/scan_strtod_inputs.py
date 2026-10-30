#!/usr/bin/env python3
"""scan_strtod_inputs.py - do any gate models contain the two number spellings glibc's strtod reads and the
Java runtime's scanner (which the Go one was ported from) did not: hexadecimal floats (0x1p3) and NaN payloads
(nan(123))? Comments (after ;) are ignored.   gate/scan_strtod_inputs.py > results/strtod_inputs.txt
Written by Claude (Anthropic); see AI-USE.md."""
import os, re
HERE = os.path.dirname(os.path.abspath(__file__))
models = [l.rstrip('\n').split('\t', 1) for l in open(os.path.join(HERE, 'models_all.tsv'))]
corpus = os.environ.get('SWMM_CORPUS', os.path.join(HERE, '..', '..', '1729-SWMM5-Models-2030'))
hx = re.compile(rb'(?<![\w.])[-+]?0[xX][0-9a-fA-F.]')
nn = re.compile(rb'(?i)(?<!\w)[-+]?nan\(')
hits = []
for mid, p in models:
    p = p if os.path.isabs(p) else os.path.join(corpus, p)
    body = b'\n'.join(l.split(b';', 1)[0] for l in open(p, 'rb').read().split(b'\n'))
    m = hx.search(body) or nn.search(body)
    if m:
        hits.append('%s %s %r' % (mid, p, m.group(0)))
print('%d gate models; %d contain a hexadecimal float or a NaN payload outside comments' % (len(models), len(hits)))
for h in hits:
    print('  ' + h)
