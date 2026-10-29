#!/usr/bin/env python3
"""Summarize a gate run in progress: compare whatever result dirs already have both files."""
import os, sys, re
sys.path.insert(0, os.path.dirname(__file__))
from gate import rpt_lines, HERE
name = sys.argv[1]
d = os.path.join(HERE, 'results', name)
ok = bad = 0; bads = []
for mid in sorted(os.listdir(d)):
    p = os.path.join(d, mid)
    if not os.path.isdir(p): continue
    ref = os.path.join(HERE, 'ref_outputs', mid)
    a, b = rpt_lines(ref + '/r.rpt'), rpt_lines(p + '/r.rpt')
    if b is None or not any(l.startswith(b'  Total elapsed') or b'Total elapsed' in l for l in open(p + '/r.rpt','rb').read().split(b'\n')):
        continue   # still running
    ro = ref + '/r.out'
    same = a == b
    if same and os.path.exists(ro) and os.path.getsize(ro) > 0:
        same = os.path.exists(p + '/r.out') and open(ro, 'rb').read() == open(p + '/r.out', 'rb').read()
    if same: ok += 1
    else: bad += 1; bads.append(mid)
print('%s: done %d  pass %d  fail %d' % (name, ok + bad, ok, bad), ' '.join(bads[:20]))
