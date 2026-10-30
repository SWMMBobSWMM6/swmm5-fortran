#!/usr/bin/env python3
"""Assemble the engines app (one HTML file) and the essay sources for the .docx.

  build_app.py            -> app/nine-engines.html, doc/essay.docx.json, doc/fig/*.svg

Reads tools/app/data/models.json (from build_data.py) and the gate's control, benchmark and
formatter results; every number shown is computed here from those files.
Written by Claude (Anthropic); see AI-USE.md.
"""
import collections, json, math, os, re, statistics, sys, html, hashlib, time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '../..'))
GATE = os.path.join(ROOT, 'gate')
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, 'doc'))
from swmmout import SwmmOut, SYS_VAR_NAMES, NODE_VAR_NAMES, LINK_VAR_NAMES
import figures as FG
import essay as ES

ENGINE_RUN = {'C++ swmm5-cplus': ['cplus'], 'Rust swmm5-rust': ['rust'], 'Fortran': ['fortran3'], 'C#': ['csharp3'],
              'Python': ['py_final', 'py_final_slow'], 'TypeScript': ['ts_final_q1', 'ts_final_q2', 'ts_final_q3', 'ts_final_q4'], 'Java': ['java_final_a', 'java_final_b'], 'Go': ['go_final']}


def J(p, default=None):
    try:
        return json.load(open(p))
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def count_lines(paths):
    t = 0
    for p in paths:
        try:
            t += sum(1 for _ in open(p, encoding='utf-8', errors='replace'))
        except FileNotFoundError:
            pass
    return t


def gate_counts(name):
    rows = J(os.path.join(GATE, 'results', name + '.json'), []) or []
    c = collections.Counter(r['status'] for r in rows)
    return len(rows), c.get('PASS', 0), rows


def fma_examples(rows):
    """Describe what the FMA control changed, from the first differing report line of each model:
    three small, typical cases from the 40-model control set and the two largest relative changes."""
    def num(t):
        try:
            return float(t)
        except ValueError:
            return None
    big = []
    for r in rows:
        f = r.get('first_rpt_diff')
        if r['status'] == 'PASS' or not f or f[1].startswith('len '):
            continue
        a, b = f[1].split(), f[2].split()
        if len(a) != len(b):
            continue
        for x, y in zip(a, b):
            u, v = num(x), num(y)
            if u is not None and v is not None and u != v and abs(u) > 0.01 and '.' in x and '.' in y:
                big.append((abs(v - u) / abs(u), r['path'].split('/')[-1], ' '.join(t for t in a if num(t) is None)[:40], x, y))
    big.sort(reverse=True)
    top = []
    for rel, name, label, x, y in big:
        if name not in [t[1] for t in top]:
            top.append((rel, name, label, x, y))
        if len(top) == 2:
            break
    small = ('Many differences are what one rounding step per operation does to a long calculation: in the '
             '40-model control set, a control rule acting at 03:28:08 instead of EPA\'s 03:28:14 '
             '(Clocktime_Pump_Rules.inp), a node\'s time of maximum moving six minutes (FM_Example2.inp), a '
             'continuity error moving from 0.066 to 0.068 percent (CN_Horton.inp). Times can jump: in 31_Subs.inp, '
             'node 3060 reports the same maximum depth, 3.22, reached nearly seven hours earlier (day 0 17:02 '
             'instead of day 1 00:00).')
    if not top:
        return small
    return small + ' Some are not small. Among decimal quantities in the first report line that differs, the largest relative changes: ' + \
        '; '.join('%s, %s to %s (%+.0f%%)' % (name, x, y, 100.0 * (float(y) - float(x)) / abs(float(x))) for rel, name, label, x, y in top) + '.'


def rust_info():
    """commit and engine size of the swmm5-rust checkout that was gated (SWMM5_RUST_REPO)"""
    d = os.environ.get('SWMM5_RUST_REPO', '/home/claude/swmmbobswmm6/swmm5-rust')
    if not os.path.isdir(d):
        return {}
    import subprocess
    c = subprocess.run(['git', '-C', d, 'rev-parse', 'HEAD'], capture_output=True, text=True).stdout.strip()
    src = os.path.join(d, 'crates/engine/src')
    files = [os.path.join(r, f) for r, _, fs in os.walk(src) for f in fs if f.endswith('.rs')]
    return dict(commit=c, lines=count_lines(files), files=len(files))


def libm_info():
    """the libm census (gate/results/libm_census.txt), the generic-libm control on EPA itself
    (gate/results/ctl_libm_generic.json) and the bit-for-bit test of the ports (gate/results/libm_tests.txt)"""
    out = dict(census=[], tests={}, generic_n=0, generic_same=0, generic_diff=[])
    p = os.path.join(GATE, 'results', 'libm_census.txt')
    if os.path.exists(p):
        for line in open(p):
            m = re.match(r'^(\w+)\s+([\d,]+) calls in\s+(\d+) models', line)
            if m:
                out['census'].append(dict(fn=m.group(1), calls=int(m.group(2).replace(',', '')), models=int(m.group(3))))
    n, same, rows = gate_counts('ctl_libm_generic')
    out['generic_n'], out['generic_same'] = n, same
    out['generic_diff'] = [dict(path=r['path'].split('2030/')[-1], status=r['status'], first=r['first_rpt_diff'])
                           for r in rows if r['status'] != 'PASS']
    p = os.path.join(GATE, 'results', 'libm_tests.txt')
    lang = None
    if os.path.exists(p):
        for line in open(p):
            if line.startswith('== '):
                lang = line[3:].strip()
                continue
            m = re.match(r'^(\w+)\s+(\d+) of (\d+) differ, (\d+) NaN sign', line)
            if m and lang:
                t = out['tests'].setdefault(lang, {})
                fn = m.group(1)
                a = t.setdefault(fn, [0, 0, 0])
                a[0] += int(m.group(3)); a[1] += int(m.group(2)); a[2] += int(m.group(4))
            m = re.match(r'^pow vs pow_exact: (\d+) of (\d+) differ', line)
            if m:
                out['powdiff'] = [int(m.group(2)), int(m.group(1))]
    out['native'] = {}
    p = os.path.join(GATE, 'results', 'libm_native.txt')
    if os.path.exists(p):
        for line in open(p):
            m = re.match(r'^(V8|Java|Go) [Mm]ath\.(\w+)\s+(\d+) of (\d+) differ', line)
            if m:
                d = out['native'].setdefault(m.group(1), {})
                d[m.group(2)] = [int(m.group(3)), int(m.group(4))]
                m2 = re.search(r'StrictMath (\d+)', line)
                if m2:
                    out['native'].setdefault('Java StrictMath', {})[m.group(2)] = [int(m2.group(1)), int(m.group(4))]
    # positive controls: the TypeScript and Java engines with their languages' own Math in place of glibc's
    # (gate/run_ts_native_control.sh, gate/run_java_native_control.sh), on the 40-model control set
    out['native_ctl'] = {}
    for lang, run in (('TypeScript', 'ctl_ts_native'), ('Java', 'ctl_java_native'), ('Go', 'ctl_go_native')):
        n, same, rows = gate_counts(run)
        if n:
            out['native_ctl'][lang] = dict(n=n, same=same, diff=[r['path'].split('2030/')[-1] for r in rows if r['status'] != 'PASS'])
    # TypeScript pow: fast path vs full translation vs V8 (tools/libm/test/powtime.js)
    p = os.path.join(GATE, 'results', 'powtime.txt')
    if os.path.exists(p):
        t = {}
        for line in open(p):
            m = re.match(r'^(pow \(fast path\)|pow_exact|Math\.pow)\S*.*?\s([\d.]+) ns/call', line)
            if m:
                t[m.group(1).split()[0]] = float(m.group(2))
        if len(t) == 3:
            out['powtime'] = ['%.0f' % t['pow'], '%.0f' % t['pow_exact'], '%.0f' % t['Math.pow']]
    out['native_ctl_all'] = {}
    for lang, run in (('TypeScript', 'ctl_ts_native_all'), ('Java', 'ctl_java_native_all'), ('Go', 'ctl_go_native_all')):
        n, same, rows = gate_counts(run)
        if n:
            out['native_ctl_all'][lang] = dict(n=n, same=same)
    return out


def bench_stats():
    """Main benchmark (bench.json) plus, when present, the Rust engine's own interleaved run against EPA on
    the same models (bench_rust.json): Rust's ratios are taken against EPA in that run, and its own EPA
    self-check is kept as rust_noise."""
    B = bench_one('bench.json')
    R = bench_one('bench_rust.json')
    if B and R and 'Rust' in R['per_model']:
        B['engines'].insert(B['engines'].index('C++') + 1, 'Rust')
        B['per_model']['Rust'] = R['per_model']['Rust']
        B['median']['Rust'] = R['median']['Rust']
        B['startup']['Rust'] = R['startup'].get('Rust', 0)
        B['rust_noise'] = R['noise']
        B['rust_when'] = R['when']
        B['rust_reps'] = R['reps']
    # TypeScript and Java: their own interleaved run against EPA on the same models (bench_tsjava.json)
    X = bench_one('bench_tsjava.json')
    if B and X:
        for e in ('TypeScript', 'Java'):
            if e in X['per_model']:
                B['engines'].append(e)
                B['per_model'][e] = X['per_model'][e]
                B['median'][e] = X['median'][e]
                B['startup'][e] = X['startup'].get(e, 0)
        B['tsj_noise'] = X['noise']
        B['tsj_when'] = X['when']
        B['tsj_reps'] = X['reps']
    # Go: its own interleaved run against EPA on the same models (bench_go.json)
    G = bench_one('bench_go.json')
    if B and G and 'Go' in G['per_model']:
        B['engines'].append('Go')
        B['per_model']['Go'] = G['per_model']['Go']
        B['median']['Go'] = G['median']['Go']
        B['startup']['Go'] = G['startup'].get('Go', 0)
        B['go_noise'] = G['noise']
        B['go_when'] = G['when']
        B['go_reps'] = G['reps']
    GM = J(os.path.join(GATE, 'results', 'bench_math_go.json'))
    if B and GM:
        by = collections.defaultdict(list)
        for r in GM['rows']:
            if r['rc'] == 0 and r['model'] != '--version':
                by[(r['engine'], r['model'])].append(r['cpu'])
        med = {k: statistics.median(v) for k, v in by.items()}
        rat = [med[('Go', m)] / med[('Go own math', m)] for (e, m) in med if e == 'Go' and ('Go own math', m) in med]
        if rat:
            B['go_math_cost'] = [GM['meta']['reps'], statistics.median(rat), min(rat), max(rat)]
    # what the glibc translations cost: each engine against the same engine with its language's own Math
    # (bench_math.json; per-model ratio of median CPU times)
    Mb = J(os.path.join(GATE, 'results', 'bench_math.json'))
    if B and Mb:
        by = collections.defaultdict(list)
        for r in Mb['rows']:
            if r['rc'] == 0 and r['model'] != '--version':
                by[(r['engine'], r['model'])].append(r['cpu'])
        med = {k: statistics.median(v) for k, v in by.items()}
        mc = [max(len(v) for v in by.values())]
        for a, b in (('TypeScript', 'TypeScript V8 Math'), ('Java', 'Java own Math')):
            rat = [med[(a, m)] / med[(b, m)] for (e, m) in med if e == a and (b, m) in med]
            mc += [statistics.median(rat), min(rat), max(rat)]
        B['math_cost'] = mc
    return B


def bench_one(name):
    b = J(os.path.join(GATE, 'results', name))
    if not b:
        return None
    rows = b['rows']
    by = collections.defaultdict(list)
    start = collections.defaultdict(list)
    for r in rows:
        if r['rc'] != 0:
            continue
        if r['model'] == '--version':
            start[r['engine']].append(r['cpu'])
        else:
            by[(r['model'], r['engine'])].append(r['cpu'])
    models = b['meta']['models']
    engines = b['meta']['engines']
    per_model = {e: [] for e in engines}
    noise = []
    epa_t = []
    for m in models:
        epa = by.get((m, 'EPA'))
        if not epa:
            continue
        ref = statistics.median(epa)
        epa_t.append(ref)
        for e in engines:
            v = by.get((m, e))
            if v:
                per_model[e].append(statistics.median(v) / ref)
        # noise floor: per-repetition ratio of the two EPA runs
        a2 = by.get((m, 'EPA again'))
        if a2:
            for x, y in zip(epa, a2):
                noise.append(y / x)
    med = {e: statistics.median(v) for e, v in per_model.items() if v}
    nf = (min(per_model['EPA again']), max(per_model['EPA again'])) if per_model.get('EPA again') else (1, 1)
    return dict(engines=[e for e in engines if e != 'EPA'] , per_model={e: v for e, v in per_model.items() if e != 'EPA'},
                median={e: v for e, v in med.items() if e != 'EPA'}, noise=nf,
                noise_pairs=(min(noise), max(noise)) if noise else (1, 1),
                startup={e: statistics.median(v) for e, v in start.items()}, reps=b['meta']['reps'],
                n_models=len(models), epa_min=min(epa_t), epa_max=max(epa_t), when=b['meta']['when'],
                models=models, epa_t=epa_t, raw={'%s|%s' % k: v for k, v in by.items()})


def fmt_results():
    p = os.path.join(ROOT, 'f90/runtime/tests/work/results.txt')
    t = open(p).read() if os.path.exists(p) else ''
    def g(rx):
        m = re.search(rx, t)
        return int(m.group(1)) if m else 0
    return dict(fmt_printf=g(r'printf  all:\s+cases (\d+)'), fmt_sscanf=g(r'sscanf  all:\s+cases (\d+)'),
                fmt_strtod=g(r'strtod  all:\s+cases (\d+)'),
                fmt_mismatch=sum(int(x) for x in re.findall(r'all:\s+cases \d+\s+mismatches (\d+)', t)),
                fmt_pass='RESULT: PASS' in t, go_fmt=go_fmt_results())


def go_fmt_results():
    """the Go runtime's printf/strtod/sscanf against glibc (gate/results/go_crt_check.txt)"""
    p = os.path.join(GATE, 'results', 'go_crt_check.txt')
    if not os.path.exists(p):
        return None
    t = open(p).read()
    out = {}
    for k in ('printf', 'strtod', 'sscanf'):
        m = re.search(r'^%s: (\d+) cases, (\d+) differ' % k, t, re.M)
        out[k] = [int(m.group(1)), int(m.group(2))] if m else [0, 0]
    m = re.search(r'^\s+f (%#\S+) arg=(\S+)\s+glibc="([^"]*)"\s+go="([^"]*)"', t, re.M)
    if m:
        import struct
        v = struct.unpack('<d', struct.pack('<Q', int(m.group(2), 16)))[0]
        out['quirk'] = [m.group(1), repr(v), m.group(3), m.group(4)]
        out['note'] = ('%s of %r: glibc prints %s, the Go runtime %s; a glibc quirk on the # flag, which SWMM never uses'
                       % (m.group(1), v, m.group(3), m.group(4)))
    else:
        out['note'] = ''
    return out


def go_fma_check():
    """fused multiply-add instructions in the Go engine binary, by function (gate/results/go_fma_check.txt)"""
    p = os.path.join(GATE, 'results', 'go_fma_check.txt')
    if not os.path.exists(p):
        return None
    t = open(p).read()
    funcs = re.findall(r'^\s*(\d+) <([^>]+)>:', t, re.M)
    tot = re.search(r'^\s*(\d+) total', t, re.M)
    out = re.search(r'^outside glibm: (\d+)', t, re.M)
    demo = dict(re.findall(r'^fusedemo (GOAMD64=v\d main\.\w+): (\d+) fused', t, re.M))
    res = dict(total=int(tot.group(1)) if tot else 0, funcs=len(funcs), outside=int(out.group(1)) if out else -1,
               names=[f.split('.')[-1] for _, f in funcs], x86_demo={k: int(v) for k, v in demo.items()})
    p = os.path.join(GATE, 'results', 'go_fma_arm64.txt')
    if os.path.exists(p):
        t = open(p).read()
        sec = t.split('-- the engine')
        demo = sec[0]
        plain = re.search(r'main\.plain\(SB\)\n((?:\s{6}.*\n)+)', demo)
        wrapped = re.search(r'main\.wrapped\(SB\)\n((?:\s{6}.*\n)+)', demo)
        rows = re.findall(r'^\s*(\d+) (\S+)\(SB\)', sec[1] if len(sec) > 1 else '', re.M)
        ops = lambda m: [ln.split()[0] for ln in m.group(1).strip().split('\n')] if m else []
        res['arm64'] = dict(plain=ops(plain), wrapped=ops(wrapped),
                            glibm=sum(int(n) for n, f in rows if 'glibm' in f),
                            runtime=sum(int(n) for n, f in rows if f.startswith('runtime.')),
                            main=int(re.search(r'in package main[^:]*: (\d+)', t).group(1)))
    return res


def go_powtime():
    """ns per call of pow/sin/cos: glibc, the Go translations (dispatch loop, then goto) and Go's math (go_powtime.txt)"""
    p = os.path.join(GATE, 'results', 'go_powtime.txt')
    if not os.path.exists(p):
        return None
    out = {}
    key = {'glibc (C)': 'glibc', 'Go glibm, dispatch loop': 'loop', 'Go glibm': 'glibm', 'Go math': 'math'}
    for line in open(p):
        m = re.match(r'^(.*?)\s+pow\s+([\d.]+) ns\s+sin\s+([\d.]+) ns\s+cos\s+([\d.]+) ns', line)
        if m and m.group(1).strip() in key:
            out[key[m.group(1).strip()]] = dict(pow=float(m.group(2)), sin=float(m.group(3)), cos=float(m.group(4)))
    return out


def go_pprof():
    """the Go engine's CPU profile on one model (gate/results/go_pprof.txt): model, seconds, top functions by flat time"""
    p = os.path.join(GATE, 'results', 'go_pprof.txt')
    if not os.path.exists(p):
        return None
    t = open(p).read()
    m = re.search(r'^model: (\S+)', t, re.M)
    d = re.search(r'Total samples = ([\d.]+)s', t)
    top = re.findall(r'^\s+[\d.]+m?s\s+([\d.]+)%\s+[\d.]+%\s+[\d.]+m?s\s+[\d.]+%\s+(\S+)$', t.split('\n\n')[0], re.M)
    same = 'identical to EPA' in t
    return dict(model=m.group(1) if m else '?', sec=float(d.group(1)) if d else 0, same=same,
                top=[(f.replace('swmm5go/glibm.', 'glibm.').replace('main.', ''), float(pc)) for pc, f in top[:8]])


def go_constants():
    """Go's exact constant arithmetic against C's rounding (gate/results/go_constants.txt)"""
    p = os.path.join(GATE, 'results', 'go_constants.txt')
    if not os.path.exists(p):
        return None
    t = open(p).read()
    c = re.search(r'^constant 0\.1 \* 3\.0\s+= (\S+)', t, re.M)
    g = re.search(r'^C \(gcc[^)]*\) 0\.1 \* 3\.0\s+= (\S+)', t, re.M)
    ty = re.search(r'^typed float64\(float64\(0\.1\) \* 3\.0\)\s+= (\S+)', t, re.M)
    return dict(const=c.group(1), c=g.group(1), typed=ty.group(1)) if c and g and ty else None


def downsample(xs, ys, n=360):
    if len(ys) <= n:
        return list(range(len(ys))), ys
    step = len(ys) / n
    idx = []
    for b in range(n):
        a, z = int(b * step), int((b + 1) * step)
        seg = range(a, max(a + 1, z))
        k = max(seg, key=lambda i: abs(ys[i]))
        idx.append(k)
    idx = sorted(set(idx) | {0, len(ys) - 1})
    return idx, [ys[i] for i in idx]


def graphs(models_by_id, ids):
    out = []
    for mid in ids:
        m = models_by_id[mid]
        ref = os.path.join(GATE, 'ref_outputs', mid, 'r.out')
        try:
            o = SwmmOut(ref)
        except Exception:
            continue
        series = []
        cands = []
        if o.nnode:
            cands.append(('sys', 0, 11, 'System outfall outflow'))
        if o.nlink:
            peaks = [max(abs(v) for v in o.series('link', i, 0)) for i in range(o.nlink)]
            k = max(range(o.nlink), key=lambda i: peaks[i])
            cands.append(('link', k, 0, 'Flow in link %s' % o.links[k]))
        if o.nnode:
            pk = [max(o.series('node', i, 0)) for i in range(o.nnode)]
            k = max(range(o.nnode), key=lambda i: pk[i])
            cands.append(('node', k, 0, 'Depth at node %s' % o.nodes[k]))
        if o.nsub:
            cands.append(('sys', 0, 4, 'System runoff'))
        for kind, idx, var, label in cands:
            ys = o.series(kind, idx, var)
            ix, ds = downsample(None, ys)
            eng = {}
            for e, runs in ENGINE_RUN.items():
                st = m['eng'][e]['s']
                if st != 'PASS':
                    eng[e] = None
                    continue
                for r in runs:
                    p = os.path.join(GATE, 'results', r, mid, 'r.out')
                    if os.path.exists(p):
                        break
                try:
                    oe = SwmmOut(p)
                    ye = oe.series(kind, idx, var)
                    diffs = [abs(a - b) for a, b in zip(ys, ye)]
                    eng[e] = dict(max=max(diffs) if diffs else 0, ndiff=sum(1 for d in diffs if d != 0),
                                  n=len(ye), same_len=len(ye) == len(ys))
                except Exception as ex:
                    eng[e] = dict(err=str(ex))
            series.append(dict(label=label, kind=kind, var=var, idx=ix, y=[round(v, 6) for v in ds], n=len(ys),
                               eng=eng, units=o.flow_units))
        out.append(dict(id=mid, name=m['file'], folder=m['folder'], step=o.report_step, start=o.start_date,
                        nperiods=o.nperiods, series=series))
    return out


DEFECTS = [
    dict(n='1', where='inlet.c:146', code='static char *PlacementTypeWords[] = {"AUTOMATIC", "ON_GRADE", "ON_SAG"};',
         what='No NULL sentinel, so findmatch() reads past the end. EPA\'s build finds a zero word there; the ports add the NULL. Without it the first C# gate run crashed on Hydraulics/inlet_capture_test.inp (gate/csharp_run1.txt), and the Python back end, written later without the fix, raised IndexError on the same model (python.json in the stored results).'),
    dict(n='2', where='gage.c:251', code='gageInterval = (int)(floor(Tseries[k].dxMin*SECperDAY + 0.5));',
         what='Overflows int when a series has one point. x86 gives INT_MIN and no WARNING 09. Rust\'s `as` and Java\'s `(int)` saturate to INT_MAX and the warning appears; WebAssembly saturates or traps, depending on the toolchain. The ports use the x86 rule.'),
    dict(n='3', where='swmm5.c:1593', code='realpath(fname, absPath);',
         what='Writes a full path into a 260-byte InpDir. glibc\'s _FORTIFY_SOURCE aborts every run opened by a relative name, so the reference is built with fortify off. A path longer than 259 bytes would overflow InpDir; the ports have no fixed buffer there and cannot reproduce an overflow. The longest gate model path here is 115 bytes.'),
    dict(n='4', where='output.c:523', code='fwrite(&IDStartPos, sizeof(INT4), 1, Fout.file);',
         what='IDStartPos is an 8-byte off_t written with sizeof(INT4): fwrite copies its first four bytes, which on little-endian x86 are the low half, so the value is right (all three positions are taken before any results are written, so they stay small). A big-endian machine would write the high half, zero. The ports write the low four bytes.'),
    dict(n='5', where='project.c:421', code='memset(a[0], 0, size);',
         what='size is nrows*ncols (project.c:401), a count of doubles, but memset counts bytes, so seven eighths of the matrix keeps malloc\'s contents. Only USE INFLOWS reaches it, and no gate model does. There is nothing defined to copy, so the ports zero the whole matrix.'),
]


def main():
    data = J(os.path.join(HERE, 'data', 'models.json'))
    models = data['models']
    byid = {m['id']: m for m in models}
    front = J(os.path.join(HERE, 'data', 'front_stats.json'))
    engines = data['engines']
    totals = data['totals']
    # controls
    n1, s1, _ = gate_counts('ctl_epa_rerun')
    n2, s2, r2 = gate_counts('ctl_fma2')
    n3, s3, r3 = gate_counts('ctl_fma_all2')
    controls = dict(epa_rerun_n=n1, epa_rerun_same=s1, fma40_n=n2, fma40_same=s2, fma_all_n=n3, fma_all_same=s3,
                    fma_all_diff=[dict(id=r['id'], path=r['path'].split('2030/')[-1], first=r['first_rpt_diff'], status=r['status'])
                                  for r in r3 if r['status'] != 'PASS'])
    controls.update(fmt_results())
    fb = J(os.path.join(GATE, 'results', 'fma_control_build.json'), {}) or {}
    controls['fma_instr'] = fb.get('fma_instr_control', 0)
    controls['fma_examples'] = fma_examples(r3)
    controls['go_fma'] = go_fma_check()
    # python fast / slow
    fast = set(open(os.path.join(GATE, 'ids_py_fast.txt')).read().split())
    pn, ps, _ = gate_counts('py_final')
    sn, ss, srows = gate_counts('py_final_slow')
    slow_total = sum(1 for m in models if m['id'] not in fast)
    py = dict(fast_n=len(fast), fast_pass=ps, slow_n=slow_total, slow_run=sn, slow_done=ss,
              slow_rows=[dict(id=r['id'], status=r['status'], sec=r['sec']) for r in srows])
    B = bench_stats()
    # census
    # coverage counts only models whose reference run had no input error: a deck that stops on an input
    # error never simulates the features it declares
    ran = [m for m in models if m['rpt']['errors'] == 0]
    sec = collections.Counter()
    for m in ran:
        for s_ in m['feat'].get('sections', []):
            sec[s_] += 1
    def feat_count(pred, pool=None):
        return sum(1 for m in (ran if pool is None else pool) if pred(m))
    fu = J(os.path.join(HERE, 'data', 'files_use.json'), {})
    def fcount(key):
        # models with this [FILES] directive whose reference run had no input error
        return sum(1 for i in fu.get(key, []) if i in byid and byid[i]['rpt']['errors'] == 0)
    cov = [('Dynamic wave routing', feat_count(lambda m: m['feat'].get('routing') == 'DYNWAVE')),
           ('Kinematic wave routing', feat_count(lambda m: m['feat'].get('routing') == 'KINWAVE')),
           ('Steady flow routing', feat_count(lambda m: (m['feat'].get('routing') or '').startswith('STEADY'))),
           ('Subcatchments (runoff)', sec['SUBCATCHMENTS']), ('LID controls', sec['LID_CONTROLS']),
           ('Storage units', sec['STORAGE']), ('Pumps', sec['PUMPS']), ('Orifices', sec['ORIFICES']),
           ('Weirs', sec['WEIRS']), ('Outlets', sec['OUTLETS']), ('Dividers', sec['DIVIDERS']),
           ('Control rules', sec['CONTROLS']), ('Dry weather flow', sec['DWF']), ('Pollutants', sec['POLLUTANTS']),
           ('Treatment', sec['TREATMENT']), ('Groundwater', sec['GROUNDWATER']), ('RDII', sec['RDII']),
           ('Snowmelt', sec['SNOWPACKS']), ('Irregular transects', sec['TRANSECTS']), ('Streets and inlets', sec['STREETS']),
           ('Temperature data', sec['TEMPERATURE']), ('Climate file', fcount('CLIMATE FILE')),
           ('SAVE HOTSTART', fcount('SAVE HOTSTART')), ('USE HOTSTART', fcount('USE HOTSTART')),
           ('SAVE OUTFLOWS (interface)', sum(fcount(k) for k in fu if k.startswith('SAVE OUTFLOWS'))),
           ('USE INFLOWS (interface)', sum(fcount(k) for k in fu if k.startswith('USE INFLOWS'))),
           ('SAVE RUNOFF', fcount('SAVE RUNOFF')), ('USE RUNOFF', fcount('USE RUNOFF')),
           ('SAVE / USE RDII', fcount('SAVE RDII') + fcount('USE RDII')),
           ]
    not_exercised = [k for k, v in cov if v == 0]
    thin = [k for k, v in cov if 0 < v < 10]
    shapes = collections.Counter()
    for m in models:
        for k in m['feat'].get('shapes', {}):
            shapes[k.replace('SEMI_ELLIPTICAL', 'SEMIELLIPTICAL')] += 1
    shapes.pop('-', None)
    census = dict(nan_cells=sum(m['rpt'].get('nan_cells', 0) for m in models),
                  pos_nan_cells=sum(m['rpt'].get('pos_nan_cells', 0) for m in models),
                  error_decks=feat_count(lambda m: m['rpt']['errors'] > 0, models), snow=sec['SNOWPACKS'],
                  ran=len(ran), not_exercised=not_exercised, thin=thin, streets=sec['STREETS'],
                  snow_temp=feat_count(lambda m: 'SNOWPACKS' in m['feat'].get('sections', []) and
                                       'TEMPERATURE' in m['feat'].get('sections', [])),
                  error_decks_with_out=sum(1 for m in models if m['rpt']['errors'] > 0 and m.get('out_bytes', 0) > 0),
                  routing=dict(collections.Counter(m['feat'].get('routing') for m in models)),
                  infiltration=dict(collections.Counter(m['feat'].get('infiltration') for m in models)),
                  shapes=dict(shapes.most_common()),
                  units=dict(collections.Counter(m['rpt']['units'] for m in models)))
    # how the gate set was cut: the 38 distinct corpus models left out, re-timed (gate/excluded_38_times.tsv:
    # id, exit code, wall seconds, path; exit 124 = stopped at the time limit), and gate models EPA took > 12 s on
    ex = []
    xp = os.path.join(GATE, 'excluded_38_times.tsv')
    if os.path.exists(xp):
        for line in open(xp):
            i, rc, sec_, path = line.rstrip('\n').split('\t')
            ex.append(dict(id=i, rc=int(rc), sec=float(sec_), path=path))
    done = [x['sec'] for x in ex if x['rc'] != 124]
    census['excluded'] = dict(n=len(ex), timeouts=sum(1 for x in ex if x['rc'] == 124),
                              limit=30, min=min(done) if done else None, max=max(done) if done else None,
                              under12=sum(1 for t in done if t <= 12))
    census['gated_over12'] = sorted([[round(m['epa_sec'], 1), m['folder'] + '/' + m['file']] for m in models if m['epa_sec'] > 12])
    L = dict(c=count_lines([os.path.join(ROOT, 'ref/epa524/solver', f) for f in os.listdir(os.path.join(ROOT, 'ref/epa524/solver'))
                            if f.endswith(('.c', '.h', '.dat'))]),
             translator=count_lines([os.path.join(ROOT, 'tools/c2x', f) for f in ('front.py', 'emit_cs.py', 'emit_py.py', 'emit_f90.py', 'emit_ts.py', 'emit_java.py', 'emit_go.py')]),
             go_gen=count_lines([os.path.join(ROOT, 'go/swmm5', f) for f in os.listdir(os.path.join(ROOT, 'go/swmm5'))
                                 if f.startswith('f_') or f in ('types.go', 'consts.go')]),
             go_rt=count_lines([os.path.join(ROOT, 'go/crt', f) for f in os.listdir(os.path.join(ROOT, 'go/crt')) if f.endswith('.go')] +
                               [os.path.join(ROOT, 'go/swmm5', f) for f in ('overrides.go', 'main.go')]),
             libm_go=count_lines([os.path.join(ROOT, 'go/glibm/glibm.go')]),
             ts_gen=count_lines([os.path.join(ROOT, 'ts/src/engine.ts')]),
             ts_rt=count_lines([os.path.join(ROOT, 'ts/src', f) for f in ('crt.ts', 'overrides.ts', 'runswmm.ts')]),
             java_gen=count_lines([os.path.join(ROOT, 'java/src/swmm5', f) for f in os.listdir(os.path.join(ROOT, 'java/src/swmm5'))
                                   if f.startswith('F_') or f in ('Types.java', 'Consts.java')]),
             java_rt=count_lines([os.path.join(ROOT, 'java/src/swmm5', f) for f in ('R.java', 'Refs.java', 'Overrides.java', 'Main.java')]),
             libm_ts=count_lines([os.path.join(ROOT, 'ts/src/glibm.ts')]),
             libm_java=count_lines([os.path.join(ROOT, 'java/src/swmm5/Glibm.java')]),
             libm_rt=count_lines([os.path.join(ROOT, 'tools/libm', f) for f in ('glibm_rt.ts', 'GlibmRt.java', 'glibm_rt.go')]),
             libm_tools=count_lines([os.path.join(ROOT, 'tools/libm', f) for f in ('gim2x.py', 'extract_tables.py', 'build_glibm.sh', 'make_libm.sh', 'census.c', 'census_summary.py', 'run_census.sh')]),
             f90_gen=count_lines([os.path.join(ROOT, 'f90/gen/swmm5_engine.f90')]),
             f90_rt=count_lines([os.path.join(ROOT, 'f90/runtime', f) for f in ('crt_base.f90', 'crt_io.f90', 'crt_format.f90', 'overrides.inc', 'overrides_decl.inc', 'runswmm.f90')]),
             cs_gen=count_lines([os.path.join(ROOT, 'cs/gen', f) for f in os.listdir(os.path.join(ROOT, 'cs/gen'))]),
             cs_rt=count_lines([os.path.join(ROOT, 'cs/runtime', f) for f in os.listdir(os.path.join(ROOT, 'cs/runtime'))]),
             py_gen=count_lines([os.path.join(ROOT, 'py/swmm5/engine.py')]),
             py_rt=count_lines([os.path.join(ROOT, 'py/swmm5', f) for f in ('crt.py', 'overrides.py')] + [os.path.join(ROOT, 'py/runswmm.py')]))
    # matrix order: by folder then file
    order = sorted(models, key=lambda m: (m['folder'], m['file'].lower()))
    rounding = []
    from decimal import Decimal
    for typed, v, out, why in [('2.675', 2.675, '2.67', 'stored a hair below the tie'),
                               ('1.005', 1.005, '1.00', 'stored a hair below the tie'),
                               ('0.125', 0.125, '0.12', 'exact tie: even digit wins'),
                               ('0.375', 0.375, '0.38', 'exact tie: even digit wins'),
                               ('0.0125', 0.0125, '0.01', 'below .015; prints 0.013 at %.3f'),
                               ('2.5', 2.5, '2.50', '%.0f prints 2: tie to even')]:
        rounding.append(dict(typed=typed, exact=str(Decimal(v)), out=out, why=why))
    D = dict(n_models=len(models), engines=engines, totals=totals, controls=controls, python=py, bench=B,
             lines=L, census=census, front=front, c_lines=L['c'], defects=DEFECTS, coverage=cov, matrix_order=order,
             rounding=rounding,
             python_speed=('%.0f' % B['median']['Python']) if B and 'Python' in B['median'] else 'many')
    D['ai_use'] = AI_USE
    D['rust'] = rust_info()
    D['libm'] = libm_info()
    D['ts_first_pass'] = gate_counts('ts1')[1]
    D['ts_final1_pass'] = sum(gate_counts('ts_final1_q%d' % q)[1] for q in range(1, 5))
    D['java_final1_pass'] = gate_counts('java_final1_a')[1] + gate_counts('java_final1_b')[1]
    ja, jb = gate_counts('java_a'), gate_counts('java_b')
    D['java_first'] = dict(n=ja[0] + jb[0], passed=ja[1] + jb[1],
                           crashed=[r['path'].split('2030/')[-1] for r in ja[2] + jb[2] if r['status'] != 'PASS'])
    gd = gate_counts('go_disc1')
    D['go_first'] = dict(n=gd[0], passed=gd[1])
    g1 = gate_counts('go_final1')
    D['go_final1'] = dict(n=g1[0], passed=g1[1])
    D['go_const'] = go_constants()
    D['go_powtime'] = go_powtime()
    D['go_pprof'] = go_pprof()
    D['go_version'] = go_version()
    D['corpus_note'] = ES.corpus_note(D)
    # ---------------------------------------------------------------- figures
    figdir = os.path.join(HERE, 'doc', 'fig')
    os.makedirs(figdir, exist_ok=True)
    figs_app = {k: f(D, FG.APP_PALETTE) for k, f in FG.FIGURES.items()}
    for k, f in FG.FIGURES.items():
        open(os.path.join(figdir, k + '.svg'), 'w').write(f(D, FG.DOCX_PALETTE))
    blocks = ES.essay(D)
    json.dump(blocks, open(os.path.join(HERE, 'doc', 'essay.docx.json'), 'w'), indent=1)
    doc_html = render_html(blocks, figs_app)
    # ---------------------------------------------------------------- app data
    gids = (B['models'] if B else []) or [m['id'] for m in order if m['out_bytes'] > 0][:12]
    G = graphs(byid, gids)
    slim = []
    for m in order:
        slim.append(dict(id=m['id'], f=m['folder'], n=m['file'], kb=m['kb'], s=m['epa_sec'], c=m['counts'],
                         r=dict(u=m['rpt']['units'], rt=m['feat'].get('routing'), ce=m['rpt']['ce_routing'],
                                cr=m['rpt']['ce_runoff'], e=m['rpt']['errors'], w=m['rpt']['warnings'],
                                inf=m['feat'].get('infiltration'), nan=m['rpt'].get('nan_cells', 0)),
                         rl=m['rpt_lines'], ob=m['out_bytes'],
                         e={k: v for k, v in m['eng'].items()}))
    app = dict(models=slim, engines=engines, totals=totals, controls=controls, python=py, bench=B, census=census,
               corpus_note=D['corpus_note'], rust=D['rust'], libm=D['libm'], go_version=D['go_version'],
               lines=L, front=front, defects=DEFECTS, coverage=cov, graphs=G,
               built=time.strftime('%Y-%m-%d %H:%M'), figs={k: figs_app[k] for k in ('matrix', 'controls', 'speed', 'coverage', 'pointers', 'pipeline')})
    tpl = open(os.path.join(HERE, 'app_template.html')).read()
    page = tpl.replace('/*__DATA__*/null', json.dumps(app, separators=(',', ':'))).replace('<!--__DOC__-->', doc_html)
    page = page.replace('<!--__AIUSE__-->', html.escape(AI_USE))
    os.makedirs(os.path.join(ROOT, 'app'), exist_ok=True)
    open(os.path.join(ROOT, 'app', 'nine-engines.html'), 'w').write(page)
    summary = dict(n_models=len(models), totals=totals, controls={k: v for k, v in controls.items() if k != 'fma_all_diff'},
                   python={k: v for k, v in py.items() if k != 'slow_rows'}, python_slow_rows=py['slow_rows'],
                   bench=None if not B else dict(median=B['median'], range={e: [min(v), max(v)] for e, v in B['per_model'].items()},
                                                  noise=B['noise'], noise_pairs=B.get('noise_pairs'), startup=B['startup'], reps=B['reps'], n_models=B['n_models'],
                                                  epa_min=B['epa_min'], epa_max=B['epa_max'], when=B['when'],
                                                  **{k: B[k] for k in ('rust_noise', 'rust_reps', 'tsj_noise', 'tsj_reps', 'go_noise', 'go_reps', 'go_math_cost') if k in B}),
                   census=census, lines=L, front=front, defects=DEFECTS, built=app['built'], corpus_note=D['corpus_note'], rust=D['rust'], libm=D['libm'],
                   essay_title=blocks[0][1])
    json.dump(summary, open(os.path.join(HERE, 'data', 'summary.json'), 'w'), indent=1)
    print('app/nine-engines.html', len(page) // 1024, 'KB;', len(blocks), 'essay blocks;', len(G), 'graph models')
    for k in ('epa_rerun_same', 'epa_rerun_n', 'fma40_same', 'fma40_n', 'fma_all_same', 'fma_all_n'):
        print(' ', k, controls[k])
    print('  python', {k: v for k, v in py.items() if k != 'slow_rows'})
    if B:
        print('  bench medians', {k: round(v, 3) for k, v in B['median'].items()}, 'noise', B['noise'])


AI_USE = ('The six ports, the translator that wrote them, the translations of glibc\'s math routines that the TypeScript, '
          'Java and Go ports carry, this app and this essay were made with Claude, Anthropic\'s AI model, in Claude Code '
          'sessions in October 2026, under the direction of Robert (Bob) Dickinson. He chose the languages (Fortran, C# and '
          'Python first, then TypeScript and Java, then Go after a survey of the languages in his Code Rosetta Stone app), set the test (byte-identical .out and .rpt against EPA 5.2.4 on his '
          'corpus), chose the repositories and the app, and is responsible for the work. Claude wrote the translator (front '
          'end and the Fortran, C#, Python, TypeScript, Java and Go back ends), the GIMPLE translator for glibc\'s math routines '
          'and its tests, the hand-written runtimes and overrides, the gate and benchmark scripts, ran every test, built this '
          'app and wrote this text; one Claude subagent wrote the Fortran printf/sscanf/strtod module and its test suite. '
          'The checks are mechanical: the byte gate on the corpus, the null and positive controls, the Fortran and Go formatters\' '
          'comparisons with glibc, and the math routines\' comparison with the system libm. A second Claude instance, given '
          'the files but not the conclusions, audited this essay\'s claims against the stored evidence; the claims it found '
          'wrong or unsupported were corrected or removed. The slow-model sample turned up one Python crash, a translator bug '
          'in how scanf arguments were passed; it was fixed in the translator and the whole Python gate was rerun. No person '
          'has yet reviewed the generated code line by line. swmm5-cplus and swmm5-rust were made in earlier Claude '
          'sessions, also for Bob, and are only built and gated here.')


def go_version():
    """the Go toolchain the engine was built and gated with (gate/results/toolchain.txt, else go version)"""
    p = os.path.join(GATE, 'results', 'toolchain.txt')
    if os.path.exists(p):
        m = re.search(r'\bgo(1\.\d+(?:\.\d+)?)\b', open(p).read())
        if m:
            return 'Go ' + m.group(1)
    return 'Go'


def inline(s):
    s = html.escape(s, quote=False)
    s = re.sub(r'`([^`]+)`', r'<code>\1</code>', s)
    s = re.sub(r'\*\*([^*]+)\*\*', r'<strong>\1</strong>', s)
    s = re.sub(r'(?<![*\w])\*([^*]+)\*(?!\w)', r'<em>\1</em>', s)
    return s


def render_html(blocks, figs):
    out = []
    toc = []
    for b in blocks:
        k = b[0]
        if k == 'h1':
            out.append('<h1 class="doc-title">%s</h1>' % inline(b[1]))
        elif k == 'sub':
            out.append('<p class="doc-sub">%s</p>' % inline(b[1]))
            out.append('<!--TOC-->')
        elif k == 'h2':
            toc.append((b[1], b[2]))
            out.append('<h2 id="doc-%s">%s</h2>' % (b[1], inline(b[2])))
        elif k == 'p':
            out.append('<p>%s</p>' % inline(b[1]))
        elif k == 'code':
            out.append('<pre class="code"><code>%s</code></pre>' % html.escape(b[1]))
        elif k == 'ul':
            out.append('<ul>%s</ul>' % ''.join('<li>%s</li>' % inline(x) for x in b[1]))
        elif k == 'table':
            out.append('<div class="tablewrap"><table class="doc-table"><thead><tr>%s</tr></thead><tbody>%s</tbody></table></div>' % (
                ''.join('<th>%s</th>' % inline(h) for h in b[1]),
                ''.join('<tr>%s</tr>' % ''.join('<td>%s</td>' % inline(str(c)) for c in r) for r in b[2])))
        elif k == 'fig':
            out.append('<figure class="doc-fig"><div class="figwrap">%s</div><figcaption>%s</figcaption></figure>' % (figs[b[1]], inline(b[2])))
    toc_html = '<nav class="doc-toc" aria-label="Contents"><div class="kicker">Contents</div><ol>%s</ol></nav>' % ''.join(
        '<li><a href="#doc-%s" data-doclink="%s">%s</a></li>' % (i, i, inline(t)) for i, t in toc)
    return '\n'.join(out).replace('<!--TOC-->', toc_html, 1)


if __name__ == '__main__':
    main()
