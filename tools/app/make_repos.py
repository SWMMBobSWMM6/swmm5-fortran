#!/usr/bin/env python3
"""Lay out the three repositories (swmm5-fortran, swmm5-csharp, swmm5-python) from this workspace.

  make_repos.py OUTDIR

Each repository gets its own engine plus everything needed to regenerate and re-gate it: the EPA source,
the translator, the gate scripts, the stored results, the app, the essay (.docx) and the lessons.
README numbers come from tools/app/data/summary.json, written by build_app.py from the measurements.
Written by Claude (Anthropic); see AI-USE.md.
"""
import json, os, shutil, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '../..'))
CORPUS_PREFIX = '/home/claude/swmmbobswmm6/1729-swmm5-models-2030/'


def n(x):
    return format(x, ',')


def copytree(src, dst, ignore=()):
    shutil.copytree(src, dst, ignore=shutil.ignore_patterns('__pycache__', '*.pyc', *ignore), dirs_exist_ok=True)


LANG = {
    'swmm5-fortran': dict(name='Fortran', label='Fortran', dir='f90', run='fortran3', emitter='emit_f90.py',
                          gen='f90/gen/swmm5_engine.f90', build='cd f90 && ./build.sh', exe='f90/bin/runswmm',
                          need='gfortran 13 (any Fortran 2008 compiler with `iso_c_binding` should do; only gfortran was tested)',
                          lang_notes=[
                              'One module, `swmm5_engine`, with derived types for SWMM\'s structs and pointer arrays (lower bound 0) for its object arrays.',
                              'C strings are `type(CPtr)`: an int8 buffer and an offset, so `strtok` and friends behave exactly as glibc\'s.',
                              'Fortran may evaluate both sides of `.and.`/`.or.`, so every C `&&`/`||` whose right side could fault or change state is written as nested IFs.',
                              '`f90/runtime/crt_format.f90` is printf/sscanf/strtod in pure Fortran, tested against glibc 2.39 by `f90/runtime/tests/run_tests.sh`.',
                              'Build flags that matter: `-fwrapv` (C\'s wrapping int arithmetic) and `-ffp-contract=off` (no fused multiply-add).']),
    'swmm5-csharp': dict(name='C#', label='C#', dir='cs', run='csharp3', emitter='emit_cs.py',
                         gen='cs/gen/*.cs', build='cd cs && ./build.sh', exe='dotnet cs/bin/runswmm.dll',
                         need='.NET 8 SDK (build.sh calls its Roslyn compiler directly; no NuGet restore)',
                         lang_notes=[
                             'One static partial class `S` per C file; SWMM\'s structs are sealed classes with a `Clone()` that copies like C.',
                             'C strings are `CPtr` structs (byte buffer + offset); printf, sscanf and strtod are reimplemented to glibc\'s rules in `cs/runtime/CRuntime.cs`.',
                             'Every double-to-int conversion goes through `R.D2I`, which spells out x86\'s rule (NaN and out-of-range give int.MinValue).']),
    'swmm5-python': dict(name='Python', label='Python', dir='py', run='py_final', emitter='emit_py.py',
                         gen='py/swmm5/engine.py', build='(nothing to build)', exe='python3 py/runswmm.py',
                         need='Python 3.10 or newer, standard library only',
                         lang_notes=[
                             'Pure Python, standard library only: `py/swmm5/engine.py` is generated, `crt.py` is the C runtime, `overrides.py` holds the hand ports.',
                             'Scalars whose address C takes are boxed; C\'s integer division, modulo and 32-bit wraparound are spelled out.',
                             'Floating division by zero returns C\'s infinities and the x86 NaN (sign bit set, printed `-nan`) instead of raising.']),
}


def readme(repo, S):
    L = LANG[repo]
    T = S['totals']
    C = S['controls']
    P = S['python']
    B = S['bench']
    e = L['label']
    t = T.get(e, {})
    if repo == 'swmm5-python':
        gate_line = ('%s of the %s fast models (EPA within 1.5 s) identical, and %s of a %s-model sample of the %s slower ones identical'
                     % (n(P['fast_pass']), n(P['fast_n']), n(P['slow_done']), n(P['slow_run']), n(P['slow_n'])))
    else:
        gate_line = '%s of %s models identical' % (n(t.get('PASS', 0)), n(S['n_models']))
    speed = ''
    if B and e in B['median']:
        lo, hi = B['range'][e]
        speed = ('Median CPU time %.2f times EPA\'s (%.2f to %.2f over %d models, %d interleaved repetitions; EPA against '
                 'itself spans %.2f to %.2f).' % (B['median'][e], lo, hi, B['n_models'], B['reps'], B['noise'][0], B['noise'][1]))
    lines = S['lines']
    rust_ok = bool((S.get('rust') or {}).get('commit')) and bool(T.get('Rust swmm5-rust', {}).get('PASS'))
    rust_desc = ('swmm5-rust (safe Rust, built from its repository at %s and gated here)' % S['rust']['commit'][:7]
                 if rust_ok else 'the Rust engine (not run here)')
    gl = {'swmm5-fortran': lines['f90_gen'], 'swmm5-csharp': lines['cs_gen'], 'swmm5-python': lines['py_gen']}[repo]
    rl = {'swmm5-fortran': lines['f90_rt'], 'swmm5-csharp': lines['cs_rt'], 'swmm5-python': lines['py_rt']}[repo]
    others = '\n'.join('| %s | %s |' % (k, ('%s of %s identical' % (n(v.get('PASS', 0)), n(S['n_models']))) if v.get('PASS') and k != 'Python'
                                         else ('%s identical (%s fast models, then a %s-model sample of the %s slow ones)' % (n(v.get('PASS', 0)), n(P['fast_n']), n(P['slow_run']), n(P['slow_n'])) if k == 'Python' and v.get('PASS') else 'not run here'))
                       for k, v in T.items())
    return f"""# {repo}

EPA SWMM 5.2.4 in {L['name']}, written by a translator that reads EPA's C, and judged against EPA itself:
the binary `.out` file byte for byte, and the `.rpt` report line for line except the three lines that
print the wall clock.

**Result: {gate_line}.** {speed}

It is not a new engine. Every number it writes is EPA 5.2.4's, including the results of EPA's own defects
wherever EPA's behaviour is defined (see `lessons/02-epa-defects-found.md`).

## The parity contract

- Reference: EPA SWMM 5.2.4 built from the [USEPA v5.2.4 tag](https://github.com/USEPA/Stormwater-Management-Model/tree/v5.2.4)
  with gcc 13.3 `-O2` and `_FORTIFY_SOURCE` off (`ref/Makefile`), on x86-64 Linux with glibc 2.39.
- Each model runs in its own folder, as EPA's command line runs it.
- Pass = `.out` byte-identical (when EPA writes one) and `.rpt` identical after removing the lines
  `Analysis begun on`, `Analysis ended on` and `Total elapsed time`. When an input error stops EPA before it
  writes results, the engine must not write a results file either. Nothing else is excused.
- Corpus: [SWMMBobSWMM6/1729-SWMM5-Models-2030](https://github.com/SWMMBobSWMM6/1729-SWMM5-Models-2030),
  folders EPA, Hydraulics, Hydrology, LID, OWA_EXTRAN and OWA_ROUTING. {S['corpus_note']}
- {S['census']['error_decks']} of the {n(S['n_models'])} stop on an input error. For {S['census']['error_decks'] - S['census']['error_decks_with_out']} of them EPA writes no
  results file and the report is the whole comparison; the other {S['census']['error_decks_with_out']} write a short one, which is compared.

| Engine | Gate result on the same {n(S['n_models'])} models |
|---|---|
{others}

Controls: EPA run twice gives {C['epa_rerun_same']} of {C['epa_rerun_n']} identical files (null control). The Fortran
engine rebuilt with `-ffp-contract=fast -mfma` in place of `-ffp-contract=off` (`gate/build_fma_control.sh`)
differs from EPA on {C['fma_all_n'] - C['fma_all_same']} of {C['fma_all_n']} models (positive control): the gate catches a
one-rounding-step change, and those {C['fma_all_n'] - C['fma_all_same']} models are the ones that noticed it.

## Build and run

Requires {L['need']}.

```sh
{L['build']}
{L['exe']} model.inp model.rpt model.out
```

## How it was made

`tools/c2x/front.py` parses EPA's 54 C files with libclang, builds the program's tables and classifies all
{n(sum(S['front']['modes'].values()))} pointer and array declarations by kind (array, single object, string, reference to a number, file,
`void*`, function). `tools/c2x/{L['emitter']}` writes the {L['name']} engine ({n(gl)} lines, generated: `{L['gen']}`); a
hand-written runtime ({n(rl)} lines) supplies the C library pieces SWMM uses and hand ports of `odesolve.c`,
`mempool.c` and six helper functions. When the port disagreed with EPA, the fix went into the translator or the
runtime, never into the generated file.

""" + '\n'.join('- ' + x for x in L['lang_notes']) + f"""

To regenerate: `python3 tools/c2x/{L['emitter']}{' cs/gen' if repo == 'swmm5-csharp' else (' py/swmm5' if repo == 'swmm5-python' else '')}` from the repository root (needs `pip install libclang==18.1.1`
and the clang 18 headers at `/usr/lib/llvm-18/lib/clang/18/include`).

## Re-running the gate

```sh
make -C ref                                   # EPA 5.2.4 reference build
SWMM_CORPUS=/path/to/1729-SWMM5-Models-2030 gate/make_ref.sh       # reference outputs (about 1.2 GB)
SWMM_CORPUS=/path/to/1729-SWMM5-Models-2030 python3 gate/gate.py mine "{L['exe'].replace('f90/', '$PWD/f90/').replace('cs/', '$PWD/cs/').replace('py/', '$PWD/py/')}"
```

`gate/gate.py` prints a summary and writes `gate/results/mine.json`; the stored runs behind the numbers above
are in `results/`.

## The six-engine app and the essay

`app/six-engines.html` compares EPA 5.2.4, swmm5-cplus, {rust_desc}, and the Fortran, C# and
Python ports on the stored corpus runs: gate results per model, report statistics, graphs with each engine's
difference from EPA, the benchmark, the controls and the defect register. Its Doc tab is the essay
*{S.get('essay_title', 'Six Engines, One Answer')}*, also in `docs/six-engines.docx`. Rebuild both with
`python3 tools/app/build_aux_data.py && python3 tools/app/build_data.py && python3 tools/app/build_app.py` and `node tools/app/doc/build_docx.js docs/six-engines.docx`.

## What this does not show

- That SWMM is right: identical to EPA means EPA's answers, good or bad. No observed data enter anywhere.
- Other platforms: the math library differs on Windows and macOS, and a port matches EPA built there only if its
  math library matches too.
- Paths no gate model exercises (counting only models that ran without an input error):
  {', '.join(S['census']['not_exercised'])}. Street and inlet hydraulics appear in one deck, which stops on
  input errors; snowmelt runs in {S['census']['snow']}.
- Speed ratios come from 12 short models (EPA 0.01 to 0.72 s); long runs were not timed.
- The stepping API (`swmm_open`/`swmm_step`/...) is translated but only the command line was gated.
- No person has reviewed the generated code line by line; the evidence is the gate and the controls.

## Licence and credit

EPA SWMM is a work of the U.S. Environmental Protection Agency and is in the public domain; its engine is Lewis
Rossman's design, and this port keeps every algorithm as he wrote it. No licence has been chosen yet for the
translator and the runtime.

## AI use

See `AI-USE.md`.
"""


def ai_use(repo, S=None):
    L = LANG[repo]
    S = S or {}
    rust_note = ('swmm5-cplus and swmm5-rust, shown in the app, were made in earlier Claude sessions for Bob and are '
                 'only built and gated here.' if (S.get('rust') or {}).get('commit') else
                 'The Rust engine shown in the app was not run in this session.')
    extra = (' A Claude subagent wrote `f90/runtime/crt_format.f90` (printf, sscanf and strtod in pure Fortran) and '
             'its glibc test suite; the main session reran that suite before using the module.') if repo == 'swmm5-fortran' else ''
    return f"""# AI use

This repository was made with Claude, Anthropic's AI model (Claude Opus 5.5), in Claude Code sessions on
28 and 29 October 2026, under the direction of Robert (Bob) Dickinson. He asked for Fortran, C# and Python
engines, chose byte-identical ports over bindings, chose one repository per language and the six-engine app,
and supplied the model corpus. Responsibility for publishing the work is his.

**What Claude did.** It wrote the translator (`tools/c2x/`: the libclang front end and the {L['name']} back end),
the hand-written runtime and overrides, the gate, benchmark and data scripts, ran every test and control,
diagnosed and fixed every mismatch, built the six-engine app, and wrote the essay, this README and the
lessons.{extra}

**How the results were checked.** The checks are mechanical: byte comparison of every `.out` and `.rpt` with EPA
5.2.4 built from the tag, a null control (EPA run twice) and a positive control (a build that fuses
multiply-adds). No person has yet reviewed the generated code or the runtime line by line, or rerun the gate
on another machine. {rust_note}
"""


def main():
    out = os.path.abspath(sys.argv[1])
    S = json.load(open(os.path.join(HERE, 'data', 'summary.json')))
    for repo, L in LANG.items():
        d = os.path.join(out, repo)
        if os.path.exists(d):
            for x in os.listdir(d):
                if x != '.git':
                    p = os.path.join(d, x)
                    shutil.rmtree(p) if os.path.isdir(p) else os.remove(p)
        os.makedirs(d, exist_ok=True)
        # engine
        if L['dir'] == 'f90':
            copytree(os.path.join(ROOT, 'f90'), os.path.join(d, 'f90'), ignore=('bin', 'obj', 'work'))
        elif L['dir'] == 'cs':
            copytree(os.path.join(ROOT, 'cs'), os.path.join(d, 'cs'), ignore=('bin', 'obj'))
        else:
            copytree(os.path.join(ROOT, 'py'), os.path.join(d, 'py'))
        # shared
        copytree(os.path.join(ROOT, 'tools/c2x'), os.path.join(d, 'tools/c2x'))
        copytree(os.path.join(ROOT, 'tools/app'), os.path.join(d, 'tools/app'), ignore=('fig',))
        copytree(os.path.join(ROOT, 'ref/epa524'), os.path.join(d, 'ref/epa524'))
        shutil.copy(os.path.join(ROOT, 'ref/Makefile'), os.path.join(d, 'ref/Makefile'))
        copytree(os.path.join(ROOT, 'lessons'), os.path.join(d, 'lessons'))
        os.makedirs(os.path.join(d, 'gate'), exist_ok=True)
        for f in ('gate.py', 'partial.py', 'bench.py', 'run_one.sh', 'cmp1.sh', 'make_ref.sh', 'ids_py_fast.txt',
                  'ids_py_slow.txt', 'ids_py_slow_sample.txt', 'smoke40.txt', 'bench_ids.txt',
                  'build_fma_control.sh', 'profile_fortran.sh', 'excluded_38_times.tsv', 'csharp_run1.txt'):
            if os.path.exists(os.path.join(ROOT, 'gate', f)):
                shutil.copy(os.path.join(ROOT, 'gate', f), os.path.join(d, 'gate', f))
        with open(os.path.join(ROOT, 'gate/models_all.tsv')) as fi, open(os.path.join(d, 'gate/models_all.tsv'), 'w') as fo:
            for line in fi:
                fo.write(line.replace(CORPUS_PREFIX, ''))
        os.makedirs(os.path.join(d, 'results'), exist_ok=True)
        runs = {'swmm5-fortran': ['fortran3'], 'swmm5-csharp': ['csharp3'], 'swmm5-python': ['py_final', 'py_final_slow']}[repo]
        # python.json / python_slow.json: the first Python runs, which the defect register and lesson 08 cite
        for r in runs + ['cplus', 'ctl_epa_rerun', 'ctl_fma2', 'ctl_fma_all2', 'bench', 'fma_control_build',
                         'python', 'python_slow', 'rust', 'bench_rust']:
            p = os.path.join(ROOT, 'gate/results', r + '.json')
            if os.path.exists(p):
                shutil.copy(p, os.path.join(d, 'results', r + '.json'))
        gp = os.path.join(ROOT, 'gate/results/fortran_gprof.txt')
        if os.path.exists(gp):
            shutil.copy(gp, os.path.join(d, 'results', 'fortran_gprof.txt'))
        fr = os.path.join(ROOT, 'f90/runtime/tests/work/results.txt')
        if os.path.exists(fr):
            shutil.copy(fr, os.path.join(d, 'results', 'crt_format_tests.txt'))
        shutil.copy(os.path.join(HERE, 'data', 'summary.json'), os.path.join(d, 'results', 'summary.json'))
        os.makedirs(os.path.join(d, 'app'), exist_ok=True)
        shutil.copy(os.path.join(ROOT, 'app/six-engines.html'), os.path.join(d, 'app/six-engines.html'))
        os.makedirs(os.path.join(d, 'docs'), exist_ok=True)
        dx = os.path.join(ROOT, 'docs/six-engines.docx')
        if os.path.exists(dx):
            shutil.copy(dx, os.path.join(d, 'docs/six-engines.docx'))
        open(os.path.join(d, 'README.md'), 'w').write(readme(repo, S))
        open(os.path.join(d, 'AI-USE.md'), 'w').write(ai_use(repo, S))
        open(os.path.join(d, '.gitignore'), 'w').write('gate/ref_outputs/\ngate/results/\n*/bin/\n*/obj/\n__pycache__/\n*.pyc\nref/runswmm\nf90/runtime/tests/work/\n')
        print('laid out', d)


if __name__ == '__main__':
    main()
