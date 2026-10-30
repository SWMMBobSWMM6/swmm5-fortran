#!/usr/bin/env python3
"""Interleaved run-time benchmark of several SWMM5 engines on the same models.

  bench.py IDS_FILE OUT.json [--reps N] [--seed S]

Each repetition visits every model once and runs every engine on it in a fresh random order, so
slow drifts of the machine fall on all engines alike.  EPA runs twice per visit ("EPA" and
"EPA again"): the spread between those two is the noise floor, and a ratio inside it is not a
result.  CPU time (user + system of the child) and wall time are both recorded.  A start-up row
runs each engine with --version so its fixed cost can be separated from simulation work.
Written by Claude (Anthropic); see AI-USE.md.
"""
import argparse, json, os, random, resource, shutil, subprocess, sys, tempfile, time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
ENGINES = {
    'EPA': [os.path.join(ROOT, 'ref/runswmm')],
    'EPA again': [os.path.join(ROOT, 'ref/runswmm')],
    'C++': ['/home/claude/swmmbobswmm6/swmm5-cplus/build/native/runswmm_cp'],
    'Fortran': [os.path.join(ROOT, 'f90/bin/runswmm')],
    'C#': ['dotnet', os.path.join(ROOT, 'cs/bin/runswmm.dll')],
    'Python': ['python3', os.path.join(ROOT, 'py/runswmm.py')],
    'Rust': [os.environ.get('SWMM5_RUST', '/home/claude/swmmbobswmm6/swmm5-rust/target/release/runswmm-rs')],
    'TypeScript': ['node', os.path.join(ROOT, 'ts/dist/runswmm.js')],
    'Java': [os.path.join(ROOT, 'java/runswmm')],
    'Go': [os.path.join(ROOT, 'go/bin/runswmm')],
    # the math-library controls (built by gate/run_ts_native_control.sh and gate/run_java_native_control.sh):
    # the same engines with their language's own Math in place of the glibc translations, timed to price the math
    'TypeScript V8 Math': ['node', os.path.join(ROOT, 'build/ts_native/runswmm.js')],
    'Java own Math': ['java', '-XX:+UseParallelGC', '-XX:MaxRAMPercentage=75', '-cp',
                       os.path.join(ROOT, 'build/java_native/classes'), 'swmm5.Main'],
    'Go own math': [os.path.join(ROOT, 'build/go_native/bin/runswmm')],   # gate/run_go_native_control.sh
}


def timed(cmd, cwd):
    r0 = resource.getrusage(resource.RUSAGE_CHILDREN)
    t0 = time.perf_counter()
    p = subprocess.run(cmd, cwd=cwd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    wall = time.perf_counter() - t0
    r1 = resource.getrusage(resource.RUSAGE_CHILDREN)
    cpu = (r1.ru_utime - r0.ru_utime) + (r1.ru_stime - r0.ru_stime)
    return wall, cpu, p.returncode


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('ids'); ap.add_argument('out')
    ap.add_argument('--reps', type=int, default=5); ap.add_argument('--seed', type=int, default=1729)
    ap.add_argument('--engines', default=','.join(e for e in ENGINES if e not in ('Rust', 'TypeScript', 'Java', 'Go', 'TypeScript V8 Math', 'Java own Math', 'Go own math')))
    a = ap.parse_args()
    names = a.engines.split(',')
    paths = dict(l.rstrip('\n').split('\t', 1) for l in open(os.path.join(HERE, 'models_all.tsv')))
    corpus = os.environ.get('SWMM_CORPUS', os.path.join(HERE, '..', '..', '1729-SWMM5-Models-2030'))
    paths = {m: p if os.path.isabs(p) else os.path.join(corpus, p) for m, p in paths.items()}
    ids = open(a.ids).read().split()
    rng = random.Random(a.seed)
    rows = []
    tmp = tempfile.mkdtemp(prefix='bench_')
    for rep in range(a.reps):
        for e in rng.sample(names, len(names)):
            w, c, rc = timed(ENGINES[e] + ['--version'], tmp)
            rows.append(dict(rep=rep, model='--version', engine=e, wall=w, cpu=c, rc=rc))
        for mid in rng.sample(ids, len(ids)):
            inp = paths[mid]
            for e in rng.sample(names, len(names)):
                out = os.path.join(tmp, 'r')
                w, c, rc = timed(ENGINES[e] + [os.path.basename(inp), out + '.rpt', out + '.out'], os.path.dirname(inp))
                rows.append(dict(rep=rep, model=mid, engine=e, wall=w, cpu=c, rc=rc))
                for x in ('.rpt', '.out'):
                    try: os.remove(out + x)
                    except FileNotFoundError: pass
        print('rep %d done' % rep, flush=True)
    shutil.rmtree(tmp, ignore_errors=True)
    meta = dict(reps=a.reps, seed=a.seed, engines=names, models=ids, host=os.uname().nodename,
                cpus=os.cpu_count(), when=time.strftime('%Y-%m-%d %H:%M:%S'))
    json.dump(dict(meta=meta, rows=rows), open(a.out, 'w'), indent=0)


if __name__ == '__main__':
    main()
