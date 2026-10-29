#!/usr/bin/env python3
"""Collect the measured results the engines app shows into tools/app/data/app_data.json.

Every number comes from a file on disk: the EPA 5.2.4 reference outputs (gate/ref_outputs), each
engine's gate results (gate/results/<run>.json and its output folders), the benchmark
(gate/results/bench.json), the controls and the formatter test log.  Nothing is typed in.
Written by Claude (Anthropic); see AI-USE.md.
"""
import collections, hashlib, json, math, os, re, statistics, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '../..'))
GATE = os.path.join(ROOT, 'gate')
sys.path.insert(0, HERE)
from swmmout import SwmmOut

# engine label -> gate run names (merged in order) ; None = not run here
RUNS = collections.OrderedDict([
    ('EPA 5.2.4 (C)', None),
    ('C++ swmm5-cplus', ['cplus']),
    ('Rust swmm5-rust', ['rust']),
    ('Fortran', ['fortran3']),
    ('C#', ['csharp3']),
    ('Python', ['py_final', 'py_final_slow']),
    ('TypeScript', ['ts_final_q1', 'ts_final_q2', 'ts_final_q3', 'ts_final_q4']),
    ('Java', ['java_final_a', 'java_final_b']),
])
TS = re.compile(rb'Analysis begun|Analysis ended|Total elapsed time')


def md5(p):
    try:
        return hashlib.md5(open(p, 'rb').read()).hexdigest()
    except FileNotFoundError:
        return None


def rpt_md5(p):
    try:
        lines = [l for l in open(p, 'rb').read().split(b'\n') if not TS.search(l)]
    except FileNotFoundError:
        return None, 0
    return hashlib.md5(b'\n'.join(lines)).hexdigest(), len(lines)


def parse_rpt(p):
    t = open(p, 'rb').read().decode('latin-1')
    d = {}
    m = re.search(r'Flow Units \.+ (\S+)', t)
    d['units'] = m.group(1) if m else None
    m = re.search(r'Flow Routing Method \.+ (\S+)', t)
    d['routing'] = m.group(1) if m else ('NONE' if 'Flow Routing ........... NO' in t else None)
    def ce(section):
        i = t.find(section)
        if i < 0:
            return None
        m = re.search(r'Continuity Error \(%\) \.+\s+(\S+)', t[i:i + 3000])
        try:
            return float(m.group(1)) if m else None
        except ValueError:
            return None
    d['ce_runoff'] = ce('Runoff Quantity Continuity')
    d['ce_routing'] = ce('Flow Routing Continuity')
    d['errors'] = len(re.findall(r'^\s*ERROR \d+', t, re.M))
    d['warnings'] = len(re.findall(r'^\s*WARNING \d+', t, re.M))
    d['nan_cells'] = len(re.findall(r'(?<![A-Za-z])-nan(?![A-Za-z(])', t))
    d['pos_nan_cells'] = len(re.findall(r'(?<![A-Za-z-])nan(?![A-Za-z(])', t))
    for k in ('Rainfall/Runoff', 'RDII', 'Snowmelt', 'Groundwater', 'Flow Routing', 'Water Quality'):
        m = re.search(re.escape(k) + r' \.+ (YES|NO)', t)
        d['proc_' + k.split('/')[0].replace(' ', '_').lower()] = (m.group(1) == 'YES') if m else None
    return d


def census_features(path):
    """sections of the .inp that select code paths (names as SWMM spells them)"""
    try:
        t = open(path, encoding='latin-1').read()
    except OSError:
        return {}
    secs = set()
    cur = None
    opts = {}
    shapes = collections.Counter()
    for raw in t.splitlines():
        line = raw.split(';', 1)[0].strip()
        if not line:
            continue
        if line.startswith('['):
            cur = line.upper().strip()
            continue
        if cur:
            secs.add(cur)
            parts = line.split()
            if cur == '[OPTIONS]' and len(parts) > 1:
                opts[parts[0].upper()] = parts[1].upper()
            if cur == '[XSECTIONS]' and len(parts) > 1:
                shapes[parts[1].upper()] += 1
    return dict(sections=sorted(s.strip('[]') for s in secs), routing=opts.get('FLOW_ROUTING', 'KINWAVE'),
                infiltration=opts.get('INFILTRATION', 'HORTON'), shapes=dict(shapes))


def main():
    models = [l.rstrip('\n').split('\t', 1) for l in open(os.path.join(GATE, 'models_all.tsv'))]
    res = {}
    for label, runs in RUNS.items():
        if not runs:
            continue
        for r in runs:
            p = os.path.join(GATE, 'results', r + '.json')
            if os.path.exists(p):
                for row in json.load(open(p)):
                    res.setdefault(label, {})[row['id']] = dict(row, run=r)
    out_models = []
    tot = collections.defaultdict(lambda: collections.Counter())
    for mid, path in models:
        rel = path.split('1729-swmm5-models-2030/')[1]
        ref = os.path.join(GATE, 'ref_outputs', mid)
        rp = parse_rpt(os.path.join(ref, 'r.rpt'))
        refsec = float(open(os.path.join(ref, 'sec')).read())
        ref_out = os.path.join(ref, 'r.out')
        has_out = os.path.exists(ref_out) and os.path.getsize(ref_out) > 0
        counts = None
        if has_out:
            try:
                o = SwmmOut(ref_out)
                counts = [o.nsub, o.nnode, o.nlink, o.npoll, o.nperiods]
            except Exception:
                counts = None
        rmd5, rlines = rpt_md5(os.path.join(ref, 'r.rpt'))
        omd5 = md5(ref_out) if has_out else None
        m = dict(id=mid, folder=rel.split('/')[0], file=rel.split('/', 1)[1], kb=round(os.path.getsize(path) / 1024, 1),
                 epa_sec=round(refsec, 3), rpt=rp, counts=counts, rpt_lines=rlines,
                 out_bytes=os.path.getsize(ref_out) if has_out else 0, feat=census_features(path), eng={})
        for label in RUNS:
            if label.startswith('EPA'):
                m['eng'][label] = dict(s='REF', sec=round(refsec, 3), ho=(omd5 or '')[:10], hr=(rmd5 or '')[:10])
                continue
            row = res.get(label, {}).get(mid)
            if row is None:
                m['eng'][label] = dict(s='NOTRUN')
                tot[label]['NOTRUN'] += 1
                continue
            d = os.path.join(GATE, 'results', row['run'], mid)
            em, _ = rpt_md5(os.path.join(d, 'r.rpt'))
            eo = md5(os.path.join(d, 'r.out')) if has_out else None
            st = row['status']
            # the gate's verdict, re-derived from the files themselves
            same = em == rmd5 and (not has_out or eo == omd5)
            if st == 'PASS' and not same:
                st = 'RECHECK-FAIL'
            m['eng'][label] = dict(s=st, sec=row['sec'], ho=(eo or '')[:10], hr=(em or '')[:10])
            tot[label][st] += 1
            if st == 'PASS':
                tot[label]['rpt_lines'] += rlines
                tot[label]['out_bytes'] += m['out_bytes']
        out_models.append(m)
    data = dict(models=out_models, totals={k: dict(v) for k, v in tot.items()}, engines=list(RUNS))
    os.makedirs(os.path.join(HERE, 'data'), exist_ok=True)
    json.dump(data, open(os.path.join(HERE, 'data', 'models.json'), 'w'))
    for k, v in tot.items():
        print(k, dict(v))


if __name__ == '__main__':
    main()
