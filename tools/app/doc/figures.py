"""figures.py - the essay's figures as SVG, drawn once and used twice (Doc tab and .docx).

Each function takes the measured data D and a palette P.  In the app P maps to CSS custom
properties (so a figure repaints with the theme); for Word it maps to the light theme's hex values.
Charts are drawn only from numbers in D, never from sketched values.
Written by Claude (Anthropic); see AI-USE.md.
"""
import html, math

FONT = "IBM Plex Sans, Helvetica, Arial, sans-serif"
MONO = "IBM Plex Mono, Menlo, Consolas, monospace"

APP_PALETTE = {k: 'var(--f-%s)' % k for k in
               ('ink', 'dim', 'line', 'face', 'soft', 'a', 'ok', 'bad', 'warn', 'epa', 'cpp', 'rust', 'f90', 'cs', 'py', 'ts', 'java', 'go')}
DOCX_PALETTE = dict(ink='#1b2733', dim='#5a6878', line='#cfd8e3', face='#ffffff', soft='#eef3f8', a='#1f6fd1',
                    ok='#1d8a4c', bad='#c2352b', warn='#b45309', epa='#b45309', cpp='#1f6fd1', rust='#c2410c',
                    f90='#6b4fbb', cs='#1d8a4c', py='#0e7490', ts='#be185d', java='#4d7c0f', go='#803a71')
ENGINE_KEY = {'EPA 5.2.4 (C)': 'epa', 'C++ swmm5-cplus': 'cpp', 'Rust swmm5-rust': 'rust', 'Fortran': 'f90',
              'C#': 'cs', 'Python': 'py', 'TypeScript': 'ts', 'Java': 'java', 'Go': 'go'}


def esc(s):
    return html.escape(str(s), quote=True)


class S:
    """tiny SVG builder"""
    def __init__(self, w, h, P, label):
        self.w, self.h, self.P = w, h, P
        self.parts = ['<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %d %d" width="100%%" role="img" '
                      'aria-label="%s" style="max-width:%dpx;display:block;margin:0 auto">' % (w, h, esc(label), w)]
        self.rect(0, 0, w, h, fill='face', stroke='line', rx=8)

    def c(self, k):
        return self.P.get(k, k) if k else 'none'

    def rect(self, x, y, w, h, fill='soft', stroke=None, rx=4, sw=1, op=None):
        self.parts.append('<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" rx="%s" style="fill:%s;stroke:%s;stroke-width:%s%s"/>'
                          % (x, y, w, h, rx, self.c(fill), self.c(stroke), sw, ';fill-opacity:%s' % op if op is not None else ''))

    def line(self, x1, y1, x2, y2, stroke='line', sw=1, dash=None, arrow=False):
        self.parts.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" style="stroke:%s;stroke-width:%s%s"/>'
                          % (x1, y1, x2, y2, self.c(stroke), sw, ';stroke-dasharray:%s' % dash if dash else ''))
        if arrow:
            a = math.atan2(y2 - y1, x2 - x1)
            p1 = (x2 - 8 * math.cos(a - 0.4), y2 - 8 * math.sin(a - 0.4))
            p2 = (x2 - 8 * math.cos(a + 0.4), y2 - 8 * math.sin(a + 0.4))
            self.parts.append('<path d="M%.1f %.1f L%.1f %.1f L%.1f %.1f Z" style="fill:%s"/>'
                              % (x2, y2, p1[0], p1[1], p2[0], p2[1], self.c(stroke)))

    def text(self, x, y, s, size=12, fill='ink', anchor='start', weight=400, mono=False, italic=False):
        self.parts.append('<text x="%.1f" y="%.1f" style="fill:%s;font-family:%s;font-size:%spx;font-weight:%s;%s" '
                          'text-anchor="%s">%s</text>' % (x, y, self.c(fill), MONO if mono else FONT, size, weight,
                                                          'font-style:italic' if italic else '', anchor, esc(s)))

    def circle(self, x, y, r, fill='a', stroke=None):
        self.parts.append('<circle cx="%.1f" cy="%.1f" r="%.1f" style="fill:%s;stroke:%s"/>' % (x, y, r, self.c(fill), self.c(stroke)))

    def path(self, d, stroke='a', sw=1.5, fill=None):
        self.parts.append('<path d="%s" style="fill:%s;stroke:%s;stroke-width:%s"/>' % (d, self.c(fill), self.c(stroke), sw))

    def done(self):
        return ''.join(self.parts) + '</svg>'


# --------------------------------------------------------------------------- 1. the pipeline
def fig_pipeline(D, P):
    s = S(760, 420, P, 'How the six ports are made and judged')
    s.text(20, 28, 'One front end, six back ends, one gate', 15, weight=600)
    # C source
    s.rect(20, 60, 150, 92, fill='soft', stroke='line')
    s.text(95, 84, 'EPA SWMM 5.2.4', 13, anchor='middle', weight=600)
    s.text(95, 104, '%s lines of C' % format(D['c_lines'], ','), 12, 'dim', 'middle')
    s.text(95, 122, '%d files' % D['front']['files'], 12, 'dim', 'middle')
    s.text(95, 140, 'USEPA v5.2.4 tag', 11, 'dim', 'middle')
    s.line(170, 106, 210, 106, 'dim', 1.5, arrow=True)
    # front end
    s.rect(210, 50, 190, 112, fill='soft', stroke='a', sw=1.5)
    s.text(305, 72, 'front.py (libclang)', 13, anchor='middle', weight=600)
    for i, t in enumerate(['%d functions, %d globals' % (D['front']['functions'], D['front']['globals']),
                           '%d structs and unions' % D['front']['records'],
                           'every implicit conversion',
                           '%s pointers classified' % format(sum(D['front']['modes'].values()), ',')]):
        s.text(305, 94 + 18 * i, t, 11.5, 'dim', 'middle')
    # back ends
    ys = [40, 88, 136, 184, 232, 280]
    names = [('emit_f90.py', 'Fortran 2008 module', 'f90'), ('emit_cs.py', 'C# static class', 'cs'), ('emit_py.py', 'pure Python', 'py'),
             ('emit_ts.py', 'TypeScript module', 'ts'), ('emit_java.py', 'Java classes', 'java'), ('emit_go.py', 'Go package', 'go')]
    for y, (n, what, k) in zip(ys, names):
        s.line(400, 106, 450, y + 20, 'dim', 1.2, arrow=True)
        s.rect(450, y, 140, 40, fill='soft', stroke=k, sw=2)
        s.text(520, y + 17, n, 12.5, anchor='middle', weight=600, mono=True)
        s.text(520, y + 32, what, 11, 'dim', 'middle')
        s.line(590, y + 20, 630, 160, 'dim', 1.2, arrow=True)
    s.text(520, 394, '+ hand-written runtime per language (printf, sscanf,', 10.5, 'dim', 'middle')
    s.text(520, 409, 'FILE, odesolve); TS, Java and Go also carry glibc\'s math', 10.5, 'dim', 'middle')
    # gate
    s.rect(630, 120, 115, 80, fill='soft', stroke='ok', sw=2)
    s.text(687, 146, 'gate', 13, anchor='middle', weight=600)
    s.text(687, 166, '.out: every byte', 11, 'dim', 'middle')
    s.text(687, 184, '.rpt: every line', 11, 'dim', 'middle')
    s.text(687, 228, 'a mismatch is fixed', 11, 'bad', 'middle')
    s.text(687, 244, 'in the translator or runtime,', 11, 'bad', 'middle')
    s.text(687, 260, 'never in the output', 11, 'bad', 'middle')
    s.path('M687 270 C 687 392, 330 392, 305 166', stroke='bad', sw=1.2)
    s.line(305, 172, 305, 164, 'bad', 1.2, arrow=True)
    return s.done()


# --------------------------------------------------------------------------- 2. pointer modes
def fig_pointers(D, P):
    modes = D['front']['modes']
    order = [('array', 'indexed array', 'pointer(0:)', 'T[]', 'list', 'Float64Array', 'double[]', '[]T'),
             ('obj', 'one object', 'type(T),pointer', 'class ref', 'object', 'object', 'object', '*T'),
             ('char', 'string', 'CPtr', 'CPtr', 'CPtr', 'CPtr', 'CPtr', 'R.CPtr'),
             ('ref', 'reference to a number', 'intent(inout)', 'ref double', 'Box', 'Box/ElemRef', 'DRef', '*float64'),
             ('file', 'FILE*', 'CFile', 'CFile', 'CFile', 'CFile', 'CFile', '*R.CFile'),
             ('void', 'untyped void*', 'type(c_ptr)', 'object', 'object', 'any', 'Object', 'any'),
             ('func', 'function pointer', 'interface', 'delegate', 'function', 'function', 'FPn::call', 'func type')]
    s = S(760, 330, P, 'What each C pointer became')
    s.text(20, 28, 'One C pointer type, seven jobs: pointer and array declarations by kind, and what each became', 14, weight=600)
    mx = max(modes.values())
    x0, bw = 170, 66
    cols = [(276, 'Fortran', 'f90'), (370, 'C#', 'cs'), (436, 'Python', 'py'), (490, 'TypeScript', 'ts'), (572, 'Java', 'java'), (636, 'Go', 'go')]
    s.text(x0, 54, 'declarations', 11, 'dim')
    for x, lab, k in cols:
        s.text(x, 54, lab, 11, k, weight=600)
    for i, row in enumerate(order):
        k, lab = row[0], row[1]
        y = 66 + i * 36
        n = modes.get(k, 0)
        s.text(160, y + 17, lab, 11.5, anchor='end')
        s.rect(x0, y + 4, max(2, bw * n / mx), 20, fill='a', rx=3, op=0.85)
        s.text(x0 + bw * n / mx + 4, y + 19, str(n), 10.5, 'ink', mono=True)
        for (x, _, _), t in zip(cols, row[2:]):
            s.text(x, y + 18, t, 9.5, 'dim', mono=True)
    s.text(20, 318, 'Counted by tools/c2x/front.py over the 54 C files. Strings, files, void* and callbacks go by type; the rest by use.', 11, 'dim')
    return s.done()


# --------------------------------------------------------------------------- 3. CPtr and strtok
def fig_cptr(D, P):
    line = 'J1  100.0  4.5'
    s = S(760, 250, P, 'A C string is an offset into bytes')
    s.text(20, 28, 'strtok() writes NULs into the line and hands back offsets into the same bytes', 14, weight=600)
    x0, cw, y = 40, 34, 70
    toks = []
    cur = None
    for i, ch in enumerate(line):
        if ch != ' ' and cur is None:
            cur = i
        if ch == ' ' and cur is not None:
            toks.append(cur); cur = None
    if cur is not None:
        toks.append(cur)
    for i, ch in enumerate(line + '\0'):
        after = ch
        if ch == ' ' and i > 0 and line[i - 1] != ' ':
            after = '\\0'
        s.rect(x0 + i * cw, y, cw - 2, 34, fill='soft', stroke='line', rx=3)
        s.text(x0 + i * cw + cw / 2 - 1, y + 22, after if after != '\0' else '\\0', 13, 'bad' if after == '\\0' else 'ink', 'middle', mono=True)
        s.text(x0 + i * cw + cw / 2 - 1, y + 50, str(i), 10, 'dim', 'middle', mono=True)
    s.text(x0, y - 10, 'b(0:15)  the line buffer, after strtok', 11, 'dim')
    for j, t in enumerate(toks):
        cx = x0 + t * cw + cw / 2
        s.line(cx, 190, cx, y + 58, 'a', 1.5, arrow=True)
        s.rect(cx - 52, 192, 104, 40, fill='soft', stroke='a', rx=4)
        s.text(cx, 209, 'Tok[%d]' % j, 11.5, 'ink', 'middle', mono=True)
        s.text(cx, 225, 'b => line, o = %d' % t, 10, 'dim', 'middle', mono=True)
    return s.done()


# --------------------------------------------------------------------------- 4. rounding
def fig_rounding(D, P):
    rows = D['rounding']
    s = S(760, 300, P, 'printf rounds the binary value, not the decimal you typed')
    s.text(20, 28, 'What "%.2f" sees: the exact value of the double, rounded half to even', 14, weight=600)
    s.text(20, 56, 'you typed', 11, 'dim', weight=600)
    s.text(84, 56, 'the double actually stored (exact decimal expansion)', 11, 'dim', weight=600)
    s.text(470, 56, '%.2f', 11, 'dim', weight=600)
    s.text(530, 56, 'why', 11, 'dim', weight=600)
    for i, r in enumerate(rows):
        y = 84 + i * 34
        s.line(20, y + 10, 740, y + 10, 'line', 0.6)
        s.text(20, y, r['typed'], 13, mono=True)
        ex = r['exact']
        s.text(84, y, ex if len(ex) <= 56 else ex[:53] + '...', 10, 'ink', mono=True)
        s.text(470, y, r['out'], 13, 'a', mono=True, weight=600)
        s.text(530, y, r['why'], 11, 'dim')
    s.text(20, 290, 'Values printed by gcc 13.3 / glibc 2.39 on this machine; expansions from Python decimal.Decimal(float).', 10.5, 'dim')
    return s.done()


# --------------------------------------------------------------------------- 5. short-circuit
def fig_shortcircuit(D, P):
    s = S(760, 290, P, 'C short-circuit and its Fortran translation')
    s.text(20, 28, 'C promises the right side of && is skipped; Fortran does not, so the port spells it out', 14, weight=600)
    c = ['k = Evap.recoveryPattern;', 'if ( k >= 0 &&', '     Pattern[k].type == MONTHLY_PATTERN )', '{', '  Evap.recoveryFactor =', '     Pattern[k].factor[mon-1];', '}']
    f = ['k_l = Evap%recoveryPattern', 'b1_ = k_l >= 0', 'if (b1_) then', '   b1_ = Pattern(k_l)%type == MONTHLY_PATTERN', 'end if', 'if (b1_) then',
         '   Evap%recoveryFactor = Pattern(k_l)%factor(mon - 1)', 'end if']
    s.rect(20, 46, 300, 220, fill='soft', stroke='epa', rx=6)
    s.text(32, 66, 'climate.c:914, setEvap()', 11, 'epa', weight=600)
    for i, t in enumerate(c):
        s.text(32, 92 + i * 20, t, 11.5, mono=True)
    s.line(323, 156, 343, 156, 'dim', 1.5, arrow=True)
    s.rect(346, 46, 394, 220, fill='soft', stroke='f90', rx=6)
    s.text(358, 66, 'swmm5_engine.f90, generated', 11, 'f90', weight=600)
    for i, t in enumerate(f):
        s.text(358, 92 + i * 20, t, 11, mono=True)
    s.text(32, 256, 'k = -1 means no pattern: Pattern[-1] is never read', 10.5, 'dim', italic=True)
    s.text(358, 256, 'kept as .and. only when the right side cannot fault', 10.5, 'dim', italic=True)
    return s.done()


# --------------------------------------------------------------------------- 6. gate matrix
def fig_matrix(D, P):
    eng = D['engines']
    models = D['matrix_order']
    s = S(760, 80 + 34 * len(eng) + 40, P, 'Gate result for every model and engine')
    s.text(20, 28, 'Every model, every engine: one column per model (%d), grouped by corpus folder' % len(models), 14, weight=600)
    x0, x1 = 170, 740
    cw = (x1 - x0) / len(models)
    y0 = 52
    folders = []
    for i, m in enumerate(models):
        if not folders or folders[-1][0] != m['folder']:
            folders.append([m['folder'], i, i])
        folders[-1][2] = i
    for f, a, b in folders:
        s.line(x0 + a * cw, y0 - 4, x0 + a * cw, y0 + 34 * len(eng), 'line', 0.8)
        s.text(x0 + (a + b + 1) / 2 * cw, y0 + 34 * len(eng) + 16, f.replace('OWA_', 'OWA '), 9.5, 'dim', 'middle')
    for j, e in enumerate(eng):
        y = y0 + j * 34
        s.text(x0 - 10, y + 19, e, 11.5, anchor='end', weight=600 if e.startswith('EPA') else 400)
        runs = []
        for i, m in enumerate(models):
            st = m['eng'][e]['s']
            col = {'REF': 'epa', 'PASS': 'ok', 'NOTRUN': 'line'}.get(st, 'bad')
            if runs and runs[-1][0] == col and runs[-1][2] == i - 1:
                runs[-1][2] = i
            else:
                runs.append([col, i, i])
        for col, a, b in runs:
            s.rect(x0 + a * cw, y + 4, (b - a + 1) * cw, 24, fill=col, rx=0, op=0.9 if col != 'line' else 0.6)
        tot = D['totals'].get(e, {})
        if e.startswith('EPA'):
            lab = 'reference'
        else:
            lab = '%d identical' % tot.get('PASS', 0) if tot.get('PASS') else 'not run here'
    s.rect(x0, y0 + 34 * len(eng) + 26, 12, 10, fill='ok', rx=2)
    s.text(x0 + 16, y0 + 34 * len(eng) + 35, 'byte-identical .out and .rpt', 10.5, 'dim')
    s.rect(x0 + 200, y0 + 34 * len(eng) + 26, 12, 10, fill='line', rx=2)
    s.text(x0 + 216, y0 + 34 * len(eng) + 35, 'not run in this session', 10.5, 'dim')
    s.rect(x0 + 380, y0 + 34 * len(eng) + 26, 12, 10, fill='bad', rx=2)
    nbad = sum(1 for m in models for e in eng if m['eng'][e]['s'] not in ('REF', 'PASS', 'NOTRUN'))
    s.text(x0 + 396, y0 + 34 * len(eng) + 35, 'any difference' + (' (none occurred)' if not nbad else ' (%d)' % nbad), 10.5, 'dim')
    return s.done()


# --------------------------------------------------------------------------- 7. controls
def fig_controls(D, P):
    C = D['controls']
    rows = [('EPA 5.2.4 run twice', C['epa_rerun_same'], C['epa_rerun_n'], 'null control: should be all identical'),
            ('Fortran, FMA allowed (40 models)', C['fma40_same'], C['fma40_n'], 'positive control: should differ somewhere'),
            ('Fortran, FMA allowed (all %d)' % C['fma_all_n'], C['fma_all_same'], C['fma_all_n'], 'how many models notice one rounding change')]
    s = S(760, 230, P, 'The gate can fail, and does when the arithmetic changes')
    s.text(20, 28, 'Controls: identical where nothing changed, different where one rounding rule changed', 14, weight=600)
    x0, w = 280, 420
    for i, (lab, same, n, note) in enumerate(rows):
        y = 56 + i * 54
        s.text(x0 - 10, y + 17, lab, 12, anchor='end')
        if n:
            s.rect(x0, y + 4, w * same / n, 20, fill='ok', rx=2)
            s.rect(x0 + w * same / n, y + 4, w * (n - same) / n, 20, fill='bad', rx=2)
            s.text(x0 + 6, y + 19, '%d identical' % same, 11, 'face', weight=600)
            if n - same:
                s.text(x0 + w + 6, y + 19, '%d differ' % (n - same), 11, 'bad', weight=600)
        else:
            s.text(x0, y + 19, 'not run', 11, 'dim')
        s.text(x0, y + 42, note, 10.5, 'dim', italic=True)
    return s.done()


# --------------------------------------------------------------------------- 8. speed
def fig_speed(D, P):
    B = D.get('bench')
    s = S(760, 378, P, 'CPU time of each engine relative to EPA')
    s.text(20, 28, 'CPU time per run, relative to EPA on the same model (log scale; each dot is one model, median of reps)', 13.5, weight=600)
    if not B:
        s.text(380, 170, 'benchmark not run yet', 13, 'dim', 'middle')
        return s.done()
    eng = [e for e in B['engines'] if e != 'EPA']
    lo, hi = 0.5, max(2.0, max(max(B['per_model'][e]) for e in eng) * 1.3)
    x0, x1 = 150, 730
    def X(v):
        return x0 + (x1 - x0) * (math.log10(v) - math.log10(lo)) / (math.log10(hi) - math.log10(lo))
    ticks = [t for t in (0.5, 1, 2, 5, 10, 20, 50, 100, 200, 500) if lo <= t <= hi]
    for t in ticks:
        s.line(X(t), 46, X(t), 290, 'line', 0.7, dash='3 3' if t != 1 else None)
        s.text(X(t), 306, ('%g' % t) + 'x', 10.5, 'dim', 'middle', mono=True)
    nf = B['noise']
    s.rect(X(nf[0]), 46, max(2, X(nf[1]) - X(nf[0])), 244, fill='warn', rx=0, op=0.18)
    for j, e in enumerate(eng):
        y = 64 + j * min(44, 210 / max(1, len(eng) - 1))
        k = ENGINE_KEY.get(e, {'EPA again': 'epa', 'C++': 'cpp', 'Rust': 'rust'}.get(e, 'a'))
        if e in ('TypeScript', 'Java') and B.get('tsj_noise'):
            s.rect(X(B['tsj_noise'][0]), y - 9, max(2, X(B['tsj_noise'][1]) - X(B['tsj_noise'][0])), 18, fill='warn', rx=0, op=0.12)
        if e == 'Go' and B.get('go_noise'):
            s.rect(X(B['go_noise'][0]), y - 9, max(2, X(B['go_noise'][1]) - X(B['go_noise'][0])), 18, fill='warn', rx=0, op=0.12)
        s.text(x0 - 10, y + 5, e, 12, anchor='end')
        for v in B['per_model'][e]:
            s.circle(X(v), y, 4, fill=k)
        med = B['median'][e]
        s.line(X(med), y - 12, X(med), y + 12, 'ink', 2)
        s.text(X(med) + 6, y - 9, '%.2fx' % med, 10.5, 'ink', mono=True)
    s.text(x0, 322, 'Shaded band: EPA against itself (noise floor %.2f-%.2fx). Vertical tick: median over models.' % (nf[0], nf[1]), 10.5, 'dim')
    if B.get('rust_noise'):
        s.text(x0, 338, 'Rust was timed in a separate run on another machine; EPA against itself there: %.2f-%.2fx.' % tuple(B['rust_noise']), 10.5, 'dim')
    if B.get('tsj_noise'):
        s.text(x0, 354, 'TypeScript and Java were timed in a later run of their own (row bands: EPA against itself there, %.2f-%.2fx).' % tuple(B['tsj_noise']), 10.5, 'dim')
    if B.get('go_noise'):
        s.text(x0, 370, 'Go was timed last, in a run of its own (row band: EPA against itself there, %.2f-%.2fx).' % tuple(B['go_noise']), 10.5, 'dim')
    return s.done()


# --------------------------------------------------------------------------- 9. coverage (limits)
def fig_coverage(D, P):
    cov = D['coverage']
    ran = D['census']['ran']
    s = S(760, 40 + 22 * len(cov) + 40, P, 'What the gate models exercise')
    s.text(20, 28, 'Coverage: how many of the %d models that ran (no input error) use each feature' % ran, 13.5, weight=600)
    x0, w = 260, 420
    mx = ran
    for i, (lab, n) in enumerate(cov):
        y = 46 + i * 22
        s.text(x0 - 10, y + 13, lab, 11, anchor='end')
        s.rect(x0, y + 2, max(1.5, w * n / mx), 15, fill='a' if n >= 10 else 'warn', rx=2, op=0.9)
        s.text(x0 + w * n / mx + 6, y + 14, str(n) if n else '0, not exercised', 10.5, 'ink' if n else 'bad', mono=True)
    return s.done()


# --------------------------------------------------------------------------- 5. libm census and the CPU control
def fig_libm(D, P):
    L = D.get('libm') or {}
    cen = [c for c in L.get('census', []) if c['calls'] > 0]
    s = S(760, 300, P, 'libm calls EPA makes, and what the CPU-dependent version changes')
    s.text(20, 28, 'What EPA asks of the math library, and what changes when glibc picks its generic versions', 14, weight=600)
    s.text(20, 52, 'calls across the %d gate models (log scale)' % D['n_models'], 11, 'dim')
    x0, w = 90, 300
    mx = max([c['calls'] for c in cen] or [1])
    for i, c in enumerate(cen):
        y = 64 + i * 22
        v = math.log10(c['calls']) / math.log10(mx)
        s.text(x0 - 8, y + 13, c['fn'], 11.5, anchor='end', mono=True)
        s.rect(x0, y + 2, max(2, w * v), 15, fill='a', rx=2, op=0.85)
        s.text(x0 + w * v + 6, y + 14, format(c['calls'], ','), 10.5, 'ink', mono=True)
    xs = 520
    n, same = L.get('generic_n', 0), L.get('generic_same', 0)
    s.text(xs, 52, 'EPA 5.2.4 itself, same input files', 11, 'dim')
    s.text(xs, 72, 'FMA versions (this CPU): the reference', 11.5, 'ink')
    s.rect(xs, 80, 220, 20, fill='ok', rx=2)
    s.text(xs + 6, 95, '%d of %d' % (n, n), 11, 'face', weight=600)
    s.text(xs, 128, 'generic versions (no FMA/AVX2)', 11.5, 'ink')
    if n:
        s.rect(xs, 136, 220 * same / n, 20, fill='ok', rx=2)
        s.rect(xs + 220 * same / n, 136, 220 * (n - same) / n, 20, fill='bad', rx=2)
        s.text(xs + 6, 151, '%d identical' % same, 11, 'face', weight=600)
        s.text(xs, 176, '%d models change' % (n - same), 11.5, 'bad', weight=600)
    s.text(xs, 206, 'TypeScript, Java and Go carry the FMA', 10.5, 'dim', italic=True)
    s.text(xs, 221, 'versions, translated from GCC\'s GIMPLE', 10.5, 'dim', italic=True)
    s.text(xs, 236, 'and checked bit for bit against libm.', 10.5, 'dim', italic=True)
    s.text(20, 290, 'Census: LD_PRELOAD interposer around glibc 2.39 (tools/libm/census.c). sqrt is an instruction and never calls libm; atan is never called.', 10, 'dim')
    return s.done()


FIGURES = dict(pipeline=fig_pipeline, libm=fig_libm, pointers=fig_pointers, cptr=fig_cptr, rounding=fig_rounding,
               shortcircuit=fig_shortcircuit, matrix=fig_matrix, controls=fig_controls, speed=fig_speed,
               coverage=fig_coverage)
