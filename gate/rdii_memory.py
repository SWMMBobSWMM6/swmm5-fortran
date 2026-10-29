#!/usr/bin/env python3
"""rdii_memory.py MODEL.inp - how much memory EPA's rdii.c allocates for unit-hydrograph rainfall history.

Follows rdii.c (EPA 5.2.4): each UH group's rainfall interval is getRainInterval(): WET_STEP, reduced to the
shortest rising or falling limb of any of its unit hydrographs; each response k keeps
getMaxPeriods() = tBase / rainInterval + 1 past values, tBase = T * (1 + K) hours, as a double (pastRain)
plus a char (pastMonth). Used to explain why Hydrology/sewer_rdii_problem.inp needs a large Java heap.
Written by Claude (Anthropic); see AI-USE.md.
"""
import collections, sys


def hms(s):
    p = [int(x) for x in s.split(':')]
    while len(p) < 3:
        p.append(0)
    return p[0] * 3600 + p[1] * 60 + p[2]


lines = open(sys.argv[1], encoding='latin-1').read().split('\n')
sec, uh, wet = None, collections.defaultdict(dict), 300
for line in lines:
    s = line.split(';')[0].strip()
    if not s:
        continue
    if s.startswith('['):
        sec = s.upper()
        continue
    p = s.split()
    if sec == '[OPTIONS]' and p[0].upper() == 'WET_STEP':
        wet = hms(p[1])
    if sec == '[HYDROGRAPHS]' and len(p) >= 6:
        uh[p[0]][p[2].upper()] = (float(p[4]), float(p[5]))      # T (hours), K
total, longest = 0, 0
for name, d in uh.items():
    limbs = [(int(t * 3600), int(t * (1 + k) * 3600)) for t, k in d.values()]
    ri = wet
    for tp, tb in limbs:
        if tp > 0:
            ri = min(ri, tp)
            if tb - tp > 0:
                ri = min(ri, tb - tp)
    for tp, tb in limbs:
        total += (tb // ri + 1) * (8 + 1)
        longest = max(longest, tb)
print('%s: %d unit-hydrograph groups, WET_STEP %d s, longest UH base %.0f hours' % (sys.argv[1], len(uh), wet, longest / 3600))
print('pastRain + pastMonth arrays: %d bytes (%.2f GB)' % (total, total / 1e9))
