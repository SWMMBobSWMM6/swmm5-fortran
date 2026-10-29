"""essay.py - the one source of the Doc tab and of the .docx.

essay(D) returns a list of blocks; every number in it is read from D, the measured data, at build
time.  Block kinds: ('h1', text) ('sub', text) ('h2', id, text) ('p', text) ('fig', name, caption)
('code', text) ('table', header, rows) ('ul', items).  Inline markup: **bold**, *italic*, `code`.
Written by Claude (Anthropic); see AI-USE.md.
"""


def n(x):
    return format(x, ',')


def corpus_note(D):
    """how the gate set was cut, from the re-timing of the models left out (census['excluded'])"""
    c = D['census']
    x = c.get('excluded') or {}
    over = c.get('gated_over12', [])
    s = ('The gate set is %s of the 518 distinct models (distinct by content) in six folders of the corpus, which '
         'holds 4,540 .inp files. The other 38 were left out by an early timing survey with a 12-second limit, '
         'whose records were not kept. ' % n(D['n_models']))
    if x.get('n'):
        s += ('The cut is rough. Re-timed for this essay on a busy machine, %d of the 38 ran past a %d-second limit '
              'and the rest took %.1f to %.1f seconds, %d of them within 12; and %d gate models took longer than 12 '
              'seconds in the reference run (%s).'
              % (x['timeouts'], x['limit'], x['min'], x['max'], x['under12'], len(over),
                 ', '.join('%s, %.0f s' % (p.split('/')[-1], t) for t, p in over)))
    return s


def essay(D):
    T = D['totals']
    C = D['controls']
    B = D.get('bench')
    py = D['python']
    L = D['lines']
    cens = D['census']
    out = []
    A = out.append

    ran = [e for e in D['engines'] if e.startswith('EPA') or any(k != 'NOTRUN' for k in T.get(e, {}))]
    word = {3: 'Three', 4: 'Four', 5: 'Five', 6: 'Six', 7: 'Seven', 8: 'Eight'}.get(len(ran), str(len(ran)))
    LM = D.get('libm') or {}
    new_ran = [e for e in ('TypeScript', 'Java') if e in ran]
    rust_ran = any(e.startswith('Rust') for e in ran)
    RU = D.get('rust') or {}
    A(('h1', '%s Engines, One Answer' % word))
    A(('sub', 'How EPA SWMM 5.2.4 was carried into Fortran, C#, Python, TypeScript and Java without changing one bit of what it computes'))

    # ------------------------------------------------------------------ 1
    A(('h2', 'question', 'The question, and the only honest way to answer it'))
    A(('p', 'Bob Dickinson asked how many languages the SWMM5 engine could be carried into. He already had two '
            'answers in hand: a C++ restructuring called swmm5-cplus, and a Rust engine. The survey that followed sorted '
            'the candidates into languages that can run the engine one way or another and the smaller set that can '
            'hold a native port matching EPA byte for byte on Linux. Then he asked for three from that set: Fortran, '
            'C# and Python. When those three matched, he asked for two more, TypeScript and Java, and they turned out '
            'to need something the first three did not: a copy of the C library\'s mathematics.'))
    A(('p', 'There is an easy way to do that job. You write a new engine in each language and show that it "agrees '
            'with EPA to three decimals." What you have then is a new program. It has bugs of its own, and nobody can '
            'tell them from EPA\'s, because agreement to three decimals hides everything in the fourth.'))
    A(('p', 'The other way sets the bar where nobody can argue with it. The same input file must produce the same '
            'binary results file, every byte, and the same report file, every character, except the three lines that '
            'print the wall clock. One bit different and the port is wrong. No bits different, on hundreds of models, '
            'and whatever else the port may be, it computes what EPA computes.'))
    A(('p', 'That is a hard bar. It is also the only one a machine can check for you, and a check you can hand to a '
            'machine is worth ten you have to argue about.'))

    # ------------------------------------------------------------------ 2
    A(('h2', 'what', 'What this is'))
    A(('p', '%s engines are lined up against %s models from Bob\'s 1729-SWMM5-Models-2030 corpus: EPA SWMM 5.2.4 compiled from '
            'the USEPA v5.2.4 tag, which is the reference; swmm5-cplus; the Rust engine; and the five new ports. The app '
            'shows, model by model, whether each engine\'s `.out` and `.rpt` match the reference, what the models '
            'contain, what their results look like, and what each engine costs to run. This essay explains how the '
            'ports were built, how they were judged, and how far the evidence reaches.' % (word, n(D['n_models']))))
    if rust_ran:
        A(('p', 'Two of the eight were not built here. swmm5-cplus is EPA restructured as a C++ class, and swmm5-rust is '
                'a translation into safe Rust (the engine crate forbids `unsafe` code), made in separate sessions and '
                'kept in their own repositories. Both were built from those repositories (swmm5-rust at commit %s) and '
                'put through the same gate as the five new ports, with the same reference and the same %s models.'
                % (RU.get('commit', '?')[:7], n(D['n_models']))))
    else:
        A(('p', 'The Rust engine\'s repository was not reachable from this session, so its row is marked as not run '
                'rather than guessed at. %s engines ran; hence the title.' % word))

    # ------------------------------------------------------------------ 3
    A(('h2', 'translator', 'Don\'t translate by hand'))
    A(('p', 'EPA\'s engine is %s lines of C, headers included, with the code in %d .c files. Suppose a careful engineer translates a thousand lines a '
            'day and slips once in every few hundred. That is two months of work and a couple of hundred slips, and '
            'every slip is a place where the port quietly disagrees with EPA. You would then spend another two months '
            'finding them, one model at a time.' % (n(D['c_lines']), D['front']['files'])))
    A(('p', 'So nobody translated by hand. We wrote a translator instead. It reads EPA\'s C through libclang, the '
            'parser inside the Clang compiler, which means it sees the program exactly as a compiler does: every '
            'macro expanded, every type resolved, every conversion the C language performs without saying so. One '
            'front end builds the tables (%s functions, %s global variables, %d structs and unions, %s enum '
            'constants) and works out what every pointer is for. Five back ends then write Fortran, C#, Python, '
            'TypeScript and Java.'
            % (n(D['front']['functions']), n(D['front']['globals']), D['front']['records'], n(D['front']['enums']))))
    A(('fig', 'pipeline', 'Figure 1. The C source goes through one front end and five back ends; each engine is then '
                          'judged on bytes. Mismatches were fixed in the translator or the hand-written runtime, '
                          'never in the generated code.'))
    A(('p', 'One rule did more good than any other: when a port disagreed with EPA, the fix went into the '
            'translator (or, for a C library function, the hand-written runtime), never into the generated code. Patch the generated file and the next regeneration quietly '
            'undoes your patch. Patch the translator and every function that shared the mistake is fixed at the same '
            'time, including the ones no test had reached yet.'))
    A(('table', ['Piece', 'Lines', 'Made by'],
       [['EPA SWMM 5.2.4 solver (C)', n(L['c']), 'EPA; untouched'],
        ['Translator: front end + five back ends (Python)', n(L['translator']), 'written for this job'],
        ['Fortran engine (one module)', n(L['f90_gen']), 'generated'],
        ['Fortran runtime + printf/scanf/strtod', n(L['f90_rt']), 'hand-written'],
        ['C# engine', n(L['cs_gen']), 'generated'],
        ['C# runtime', n(L['cs_rt']), 'hand-written'],
        ['Python engine', n(L['py_gen']), 'generated'],
        ['Python runtime', n(L['py_rt']), 'hand-written'],
        ['TypeScript engine', n(L['ts_gen']), 'generated'],
        ['TypeScript runtime', n(L['ts_rt']), 'hand-written'],
        ['Java engine (one class per C file)', n(L['java_gen']), 'generated'],
        ['Java runtime', n(L['java_rt']), 'hand-written'],
        ['glibc math routines in TypeScript / in Java', '%s / %s' % (n(L['libm_ts']), n(L['libm_java'])),
         'generated from GCC\'s GIMPLE; glibc\'s wrappers and TypeScript\'s pow fast path come from hand-written text in the translator'],
        ['Math translator (with that hand-written text), census and table tools', n(L['libm_tools']), 'written for this job'],
        ['Math runtimes (fma, bit casts, branred)', n(L['libm_rt']), 'hand-written']]))
    A(('p', 'The hand-written parts are small and dull on purpose: the C library functions SWMM calls (printf, '
            'sscanf, strtod, the FILE functions, strtok), plus two whole C files whose pointer tricks are easier to port '
            'by hand than to teach a translator, `odesolve.c` and `mempool.c`, and six helper functions. Everything '
            'else, %s functions of engineering, came out of the translator.' % n(D['front']['functions'] - 17)))

    # ------------------------------------------------------------------ 4
    A(('h2', 'pointers', 'A pointer is seven different things'))
    A(('p', 'C has one pointer type, and SWMM uses it for seven different jobs. `double* x` may be an array you '
            'index as `x[i]`. It may be one number passed by address so the callee can change it, as in '
            '`findroot_Newton(..., &d, ...)`. `TNode* node` may be a single object you reach through with `->`. A '
            '`char*` is a string. A `FILE*` is a file. A `void*` is "whatever the caller had in mind." And a pointer to '
            'a function is a callback. In C these are one thing. In Fortran, C#, Python, TypeScript and Java they are seven different '
            'things, and the translator has to know which one it is looking at before it writes a single line.'))
    A(('p', 'Some of the seven are settled by the declaration alone: a `char*` is a string, a `FILE*` a file, '
            '`void*` and function pointers are what they say, and an array declared as an array is an array. The '
            'rest, pointers to numbers, to structs and to other pointers, are where the type tells you nothing. For '
            'those the translator watches what the program does with each pointer, everywhere in all %d files: '
            'whether it is indexed, moved with pointer arithmetic, assigned from `malloc`, or handed an array. A '
            'pointer that is ever used as an array is an array, and so is every parameter it is passed into; a '
            'struct pointer that never is, is one object. Callbacks bound to the same function-pointer type must '
            'agree on their parameters, so the translator makes them agree.' % D['front']['files']))
    A(('fig', 'pointers', 'Figure 2. %s pointer and array declarations sorted by kind (%s of them are arrays '
                          'declared as arrays). Strings, files, `void*`, callbacks and declared arrays are known from '
                          'the declaration; for pointers to numbers, structs and pointers the uses decide.'
                          % (n(sum(D['front']['modes'].values())), n(D['front'].get('declared_arrays', 0)))))

    # ------------------------------------------------------------------ 5
    A(('h2', 'strings', 'A string is an address into bytes'))
    A(('p', 'SWMM reads its input one line at a time and chops each line into tokens with `strtok`, which writes '
            'zero bytes into the line and hands back pointers into the middle of it. A Fortran CHARACTER variable, '
            'a C# string, a Python str, a JavaScript string and a Java String cannot do any of that. They are values, not addresses.'))
    A(('p', 'So each port carries C\'s idea of a string with it: a byte buffer plus an offset. The Fortran version '
            'is `type(CPtr)`, an int8 pointer array and an integer. `strtok` works on it exactly as glibc\'s does. It '
            'writes the zeros and returns offsets into the same buffer, so a later `strcpy` into that buffer sees '
            'precisely what EPA\'s would see. When you want a byte-identical port, you carry the machine model along '
            'with it, not just the algorithm.'))
    A(('fig', 'cptr', 'Figure 3. After strtok, the tokens are not copies. They are offsets into the original line, '
                      'and the separators have become zero bytes. The ports reproduce this layout, because '
                      'SWMM\'s parser depends on it.'))

    # ------------------------------------------------------------------ 6
    A(('h2', 'bits', 'Same numbers means the same bits'))
    A(('p', 'IEEE 754 double arithmetic is the same on every machine you are likely to meet. Add, subtract, multiply, '
            'divide and square root give the correctly rounded answer, everywhere. If that were the whole story, '
            'byte-identical ports would be easy. It is not, and the trouble always comes from the places where a '
            'language leaves the result up to the implementation.'))
    A(('p', '**Conversions.** C says converting a double that is too large into an `int` is undefined. The x86 '
            'instruction gcc emits returns the most negative integer. SWMM hits this by accident in gage.c, line '
            '251, when a rain time series has a single point and `dxMin` is still its initial huge value:'))
    A(('code', 'gageInterval = (int)(floor(Tseries[k].dxMin*SECperDAY + 0.5));'))
    A(('p', 'On x86 that gives -2,147,483,648, and EPA prints no warning. Rust\'s `as` and Java\'s `(int)` '
            'saturate to +2,147,483,647 instead, and the same model prints WARNING 09; WebAssembly saturates or traps, '
            'depending on whether the toolchain emits its non-trapping conversion. Fortran\'s `int()` and C#\'s `(int)` make no '
            'promise either way, so every port routes every double-to-integer conversion through a function that '
            'spells out the x86 rule.'))
    A(('p', '**The math library.** `exp`, `log`, `pow`, `sin` and the rest are not required to round correctly, and '
            'different libraries disagree in the last bit. Fortran, C# and Python call the same glibc library EPA calls: C# '
            'through the .NET runtime on Linux, Python through its math module, Fortran through gfortran\'s built-ins. '
            'JavaScript and Java do not; V8 and the Java virtual machine bring math functions of their own. That story '
            'needs a section to itself, further on.'))
    A(('p', '**Fused multiply-add.** A compiler that turns `a*b + c` into one fused instruction rounds once instead '
            'of twice. That is more accurate and it is a different answer. EPA\'s build does not fuse. The Fortran '
            'build says `-ffp-contract=off` so it never does, and the controls below show what happens when it does.'))
    A(('p', '**NaN.** Zero divided by zero on x86 produces a NaN with its sign bit set, and glibc prints it as '
            '`-nan`. EPA\'s reports carry such cells in plain sight, in tables such as the node depth summary. The '
            'reference reports in this gate contain %s of them. Python\'s `float(\'nan\')` and JavaScript\'s `NaN` '
            'have the sign bit clear and would print `nan`. The ports carry the x86 NaN instead.' % n(cens['nan_cells'])))

    # ------------------------------------------------------------------ 7
    A(('h2', 'printf', 'The report is arithmetic too'))
    A(('p', 'The `.rpt` file is text written by `fprintf`, so it is a second calculation stacked on the first. '
            '`%.2f` does not mean "the number to two decimals." It means: take the exact value of the double, which is '
            'a binary fraction, and round that, with ties going to the even digit. The double nearest 2.675 is a hair '
            'below 2.675, so it prints 2.67. 0.125 is exact in binary and sits on the tie, so it prints 0.12.'))
    A(('fig', 'rounding', 'Figure 4. The number you type is not the number the machine holds. glibc rounds what is '
                          'held, so a formatter that rounds the decimal you meant gets these cases wrong.'))
    A(('p', 'The ports do not leave this to luck. The C# port carries its own exact formatter built on big-integer '
            'arithmetic. The Python port uses Python\'s own `%%` formatting, which rounds the exact binary value half '
            'to even just as glibc does, and adds glibc\'s spellings of infinity and NaN. The Fortran port carries a '
            'formatter written in pure Fortran, and that one was checked against glibc 2.39 directly: %s printf '
            'cases, %s sscanf cases and %s strtod cases, with %s mismatches. Those cases cover random magnitudes, '
            'exact binary ties, decimal spellings like the ones in SWMM input files, subnormals, infinities and both '
            'kinds of NaN. The Java port rounds with `new BigDecimal(x).setScale(p, RoundingMode.HALF_EVEN)`, which is '
            'glibc\'s rule stated in Java. The TypeScript port uses JavaScript\'s `toFixed`, which is exact but breaks '
            'ties away from zero, and repairs the ties: one can only occur when x times 2 to the power p+1 is an odd '
            'integer, a test that costs one multiplication. The C#, Python, TypeScript and Java formatters were checked '
            'by the gate alone.'
            % (n(C['fmt_printf']), n(C['fmt_sscanf']), n(C['fmt_strtod']), n(C['fmt_mismatch']))))

    # ------------------------------------------------------------------ 7b
    cen_by = {c['fn']: c for c in LM.get('census', [])}
    def calls(fn):
        c = cen_by.get(fn)
        return c['calls'] if c else 0
    def mods(fn):
        c = cen_by.get(fn)
        return c['models'] if c else 0
    tests = LM.get('tests', {})
    tot_args = {lang: sum(v[0] for v in t.values()) for lang, t in tests.items()}
    tot_bad = {lang: sum(v[1] + v[2] for v in t.values()) for lang, t in tests.items()}
    A(('h2', 'libm', 'Carrying the math library along'))
    A(('p', 'Before copying a library it pays to know which parts of it are used. A small interposer, loaded in front '
            'of glibc while EPA ran all %s models, counted every call. `pow` was called %s times, in %d models; `sin` '
            'and `cos` %s and %s times; `exp` %s; `log` %s; `log10` %s; `acos` and `asin` %s and %s, in three models; '
            '`tan` %s times, once per model; `atan` never. `sqrt` never reaches the library at all, because the compiler '
            'turns it into a single instruction, which is correctly rounded everywhere.'
            % (n(D['n_models']), n(calls('pow')), mods('pow'), n(calls('sin')), n(calls('cos')), n(calls('exp')),
               n(calls('log')), n(calls('log10')), n(calls('acos')), n(calls('asin')), n(calls('tan')))))
    A(('p', 'Then came a surprise. glibc does not have one `pow`. On x86-64 it has several, and it picks one when '
            'the program starts, according to the processor: on one with fused multiply-add and AVX2, as this machine '
            'has, it takes a version compiled to use fused multiply-add, which rounds once where the generic version '
            'rounds twice. The same goes for `exp`, `log`, `sin`, `cos`, `tan`, `asin`, `acos` and `atan`. So EPA\'s own '
            'answers depend on the processor. Told to use the generic versions, as glibc would on an older machine, the '
            'same EPA binary on the same input files gave %d of %d models identical and changed %d.'
            % (LM.get('generic_same', 0), LM.get('generic_n', 0), LM.get('generic_n', 0) - LM.get('generic_same', 0))))
    A(('fig', 'libm', 'Figure 5. Left: libm calls EPA made across the gate models (log scale). Right: EPA itself, run '
                      'on glibc\'s generic math routines instead of the FMA versions this processor selects. The only '
                      'setting changed was glibc\'s processor-feature switch, so every change came from the math library.'))
    NV = LM.get('native', {})
    def pct(lib, fn):
        v = NV.get(lib, {}).get(fn)
        return '%.2f%%' % (100.0 * v[0] / v[1]) if v else '?'
    A(('p', 'For Fortran, C# and Python this should change nothing: they call the same library EPA calls, so on a '
            'given machine they should get the version EPA gets (only EPA was run on the generic routines). JavaScript '
            'and Java bring their own. Held against glibc on the random and census arguments of the test described '
            'below, V8\'s `Math.pow` returns a different double on %s of them and its '
            '`Math.exp` on %s; Java\'s `Math.pow` on %s, and `StrictMath.pow`, Java\'s port of the old Sun library '
            'fdlibm, on %s. One argument in %s sounds harmless until you remember that `pow` is called a billion '
            'times. The TypeScript and Java engines therefore carry glibc\'s routines with them, and not the generic '
            'ones: the fused versions EPA actually runs here.'
            % (pct('V8', 'pow'), pct('V8', 'exp'), pct('Java', 'pow'), pct('Java StrictMath', 'pow'),
               n(int(round(NV['Java']['pow'][1] / NV['Java']['pow'][0], -2))) if NV.get('Java', {}).get('pow') else '?')))
    NC, NCA = LM.get('native_ctl') or {}, LM.get('native_ctl_all') or {}
    if NC.get('TypeScript') and NC.get('Java'):
        t, j = NC['TypeScript'], NC['Java']
        txt = ('Was that necessary, or only careful? Each engine was built a second time with its own language\'s '
               '`Math` in place of the translations, and gated on the 40 control models. The TypeScript copy differed '
               'from EPA on %d of them; the Java copy on %d' % (t['n'] - t['same'], j['n'] - j['same']))
        if NCA.get('Java'):
            ja = NCA['Java']
            txt += (', and on %d of all %d when it was run on the whole set, about as many as EPA itself changes '
                    'on glibc\'s generic routines' % (ja['n'] - ja['same'], ja['n']))
        txt += ('. Java\'s `Math` comes much closer than V8\'s, as its rate on `pow`, the function called most, promised (on '
                '`log10` it is the worse of the two), but neither would '
                'have passed the gate. (`gate/run_ts_native_control.sh`, `gate/run_java_native_control.sh`.)')
        A(('p', txt))
    A(('p', 'Translating them by hand from glibc\'s C would not do, for the same reason that matters everywhere '
            'else in this essay. The source says `a*b + c`; whether that becomes one fused instruction or two rounded '
            'ones is the compiler\'s decision, and the answer is in the compiled code, not the source. So the '
            'translation starts from the compiler. glibc 2.39\'s sources were compiled with the flags glibc uses for '
            'its FMA versions, plus two that turn vectorization off so that every operation stays scalar (whether that '
            'changed any result is exactly what the comparison below would catch), and GCC was asked to print its '
            'optimized intermediate form, GIMPLE, in which every '
            'fusion it chose is spelled out as `.FMA`, `.FMS` or `.FNMA`. A second translator turns that GIMPLE into '
            'TypeScript and Java, block by block. The constant tables were copied out of the compiled objects byte '
            'for byte. Java has an exactly rounded `Math.fma`; JavaScript has none, so the TypeScript runtime builds '
            'one from Dekker\'s exact product and Boldo and Melquiond\'s rounding to odd, with a slow exact path for '
            'the awkward cases. Nothing compiled from glibc was ever run: the reference is the system\'s own library.'))
    if tests:
        A(('p', 'Then the translations were held against the real library, argument by argument: random arguments over '
                'the ranges SWMM uses, every argument the census sampled from the real models, and a set of edge cases '
                '(huge angles, negative bases with integer powers, overflow, underflow, subnormals, domain errors). '
                '%s. Every function, both languages: not one bit different, and not one NaN with the wrong sign.'
                % '; '.join('%s: %s arguments, %s differences' % (lang, n(tot_args[lang]), n(tot_bad[lang])) for lang in sorted(tests))))
    A(('p', 'The comparison earned its keep twice, and both times the fault was the translator\'s. `pow` came out '
            'wrong for negative bases raised to even powers, though `exp` and `log` were already exact. glibc\'s source '
            'asks whether the lowest integer bit of the exponent is set. GCC rewrote that test as a conversion to a '
            'one-bit boolean, and in GIMPLE such a conversion keeps the low bit; the translator had read it as C\'s '
            '"not zero" (`gate/results/checkint_evidence.txt`):'))
    A(('code', 'if (iy & (1ULL << (0x3ff + 52 - e)))   /* glibc 2.39 e_pow.c:264, checkint */\n\n'
               '_119 = _54 >> _115;                     /* GCC 13.3 GIMPLE of the FMA build */\n'
               '_10 = (_Bool) _119;'))
    A(('p', 'The second: to skip `if (...)` statements, the translator skipped every line that began with "if", '
            'including assignments to GCC\'s temporaries, which are named `iftmp`. That one failed loudly, but only on '
            '`pow`\'s special cases. The first would not have shown up in a spot check of positive bases.'))
    tot_calls = sum(c['calls'] for c in LM.get('census', [])) or 1
    A(('p', 'One more thing came out of the census. %d percent of the calls are `pow`, and JavaScript has no ' % round(100.0 * calls('pow') / tot_calls) +
            '64-bit integers except BigInt, in which the translation does its 64-bit steps. So TypeScript\'s `pow` has a '
            'hand-written fast path for the common case that does exactly what the translation does, with the 64-bit steps done on 32-bit halves and '
            'four of the fused multiply-adds replaced by cheaper operations that give the same bits (an exact product, '
            'and the exact rounding error of a product). Everything else falls through to the full translation. The two '
            'were compared on %s further arguments: %s differences.'
            % (n((LM.get('powdiff') or [0, 0])[0]), n((LM.get('powdiff') or [0, 0])[1]))
            + (' The saving is smaller than I expected. On two million arguments the fast path takes %s nanoseconds a '
               'call and the full translation %s; V8\'s own `Math.pow` takes %s (`gate/results/powtime.txt`). What '
               'remains includes the sixteen fused multiply-adds the runtime must still build out of ordinary arithmetic.'
               % tuple(LM['powtime']) if LM.get('powtime') else '')))

    # ------------------------------------------------------------------ 8
    A(('h2', 'fortran', 'What Fortran made hard'))
    A(('p', 'C# and Python are near cousins of C, in the ways that matter here. Fortran is older and stricter, and '
            'it brought four problems of its own.'))
    A(('p', '**No short-circuit.** In C, `p != NULL && p->x > 0` never touches `p->x` when `p` is NULL. Fortran\'s '
            '`.and.` makes no such promise, and gfortran will evaluate both sides when it pleases. An early test at '
            '-O0 crashed on exactly SWMM\'s kind of guard. So the translator keeps a plain `.and.` only when the right '
            'side provably cannot fault or change anything. Otherwise it evaluates the right side inside an IF on the '
            'left side.'))
    A(('fig', 'shortcircuit', 'Figure 6. A real guard from climate.c and the Fortran the translator wrote for it. '
                              'With k = -1 the Fortran never subscripts Pattern, which is what the C promises.'))
    A(('p', '**Names ignore case.** C\'s `node` and `Node` are two variables. To Fortran they are one. The '
            'translator renames every clash, and it also keeps clear of Fortran\'s intrinsic names, so a C local '
            'called `index` or `size` does not hide the intrinsic of the same name.'))
    A(('p', '**Statements are statements.** C lets you assign inside a condition, `if ((f = fopen(...)) == NULL)`, '
            'and lets a `switch` fall through from one case into the next. Fortran allows neither. The translator '
            'hoists the assignment into its own statement and turns fall-through into numbered labels, so the order '
            'of execution is exactly C\'s.'))
    A(('p', '**Small surprises.** gfortran numbers the units it opens with negative integers. The first Fortran run '
            'simulated a whole model and wrote two empty files, because the runtime took a negative unit to mean '
            '"closed." The lesson is in the repository: never encode state in a value the compiler picks for you.'))

    # ------------------------------------------------------------------ 8b
    A(('h2', 'jsjava', 'What JavaScript and Java made hard'))
    A(('p', 'TypeScript and Java look more like C than Fortran does, and each still found its own ways to be different.'))
    A(('p', '**In JavaScript every number is a double.** An `int` is a double that happens to hold a whole number, '
            'and doubles have a negative zero. In C, `-i` for `i = 0` is zero; in JavaScript it is -0, and so are '
            '`0 * -3`, `-3 % 3` and `Math.trunc(-0.5)`. Nothing goes wrong until that value becomes a double in a '
            'report, where glibc prints it as -0.00. So the TypeScript back end writes integer negation as `(0 - x)`, '
            'multiplication as `Math.imul(a, b)`, division as `(a / b) | 0` and remainder as `(a % b) | 0`, each of '
            'which can only give +0, and keeps unsigned values in range with `>>> 0`.'))
    A(('p', '**NaN has two signs, and JavaScript\'s literal has the wrong one.** At run time V8 computes 0/0 the way '
            'the processor does and keeps the bits, through arrays and object fields alike (checked by `tools/libm/test/nan_bits.js`), but the literal '
            '`NaN` is the other pattern. So the runtime never writes the literal where C would compute a NaN. The '
            'same care turned up a small fact about glibc itself: its `log10`, `asin` and `acos` on x86-64 still go '
            'through old compatibility wrappers, which answer a domain error with a NaN whose sign bit is clear, '
            'while the routine underneath would have set it. The ports copy the wrappers.'))
    A(('p', '**Neither has pointers or `ref` parameters, and Java will not let a lambda change a local.** A C '
            'function that takes `double *f` gets a small object with a value in it: a box for a local whose address '
            'is taken, an element reference for `&a[i]`, a field reference for `&link->flow`. Arrays of numbers become '
            '`Float64Array` and its kin in TypeScript, `double[]` in Java. In Java a field reference is a pair of '
            'lambdas over the object, `__o -> __o.depth`, because a lambda may read the object it is given but may not '
            'assign a local it captures.'))
    A(('p', '**Java has no unsigned integers and rejects code C allows.** SWMM\'s one hash function uses unsigned '
            'arithmetic, which Java does in a `long` masked to 32 bits. Java\'s `(int)` of a huge double saturates '
            'where x86 gives the most negative integer (defect 2 below), so every conversion goes through `R.D2I`, '
            'exactly as in the other ports. And Java refuses a statement it can prove unreachable, such as the '
            '`break` after a `return` that C programmers write out of habit; the Java back end applies Java\'s own '
            'reachability rules to the C and leaves such statements out.'))

    # ------------------------------------------------------------------ 9
    A(('h2', 'gate', 'The gate'))
    A(('p', 'Each engine runs every model in the model\'s own folder, the way EPA\'s command line does, so that '
            'relative file names resolve the same way. The gate then compares the `.out` byte for byte, and the '
            '`.rpt` line for line after removing three lines: "Analysis begun on", "Analysis ended on" and "Total '
            'elapsed time". Nothing else is excused. When an input error stops EPA before it writes any results, '
            'the engine\'s results file must be empty or absent too (%d of the %s models are like that; this rule was made explicit '
            'in the gate after the runs, and the stored outputs of every engine pass it). The reference is EPA '
            '5.2.4 built from the v5.2.4 tag with gcc '
            '13.3 at -O2, with `_FORTIFY_SOURCE` off, because Ubuntu\'s fortify check aborts EPA on a relative input '
            'path (defect 3 in the register below).' % (cens['error_decks'] - cens['error_decks_with_out'], n(D['n_models']))))
    ndiff = sum(v for t in T.values() for k, v in t.items() if k not in ('PASS', 'NOTRUN', 'rpt_lines', 'out_bytes'))
    A(('fig', 'matrix', 'Figure 7. Every model against every engine, drawn from the gate\'s own results. Green is '
                        'byte-identical .out and .rpt; grey is not run. '
                        + ('There is no red because no difference remained.' if not ndiff else
                           'Red marks the %d runs that differ.' % ndiff)))
    rows = []
    for e in D['engines']:
        t = T.get(e, {})
        if e.startswith('EPA'):
            rows.append([e, 'reference', '-', '-'])
        elif t.get('PASS'):
            rows.append([e, '%s of %s identical' % (n(t['PASS']), n(t['PASS'] + sum(v for k, v in t.items() if k not in ('PASS', 'rpt_lines', 'out_bytes', 'NOTRUN')))),
                         n(t.get('out_bytes', 0)), n(t.get('rpt_lines', 0))])
        else:
            rows.append([e, 'not run in this session', '-', '-'])
    A(('table', ['Engine', 'Models', '.out bytes compared', '.rpt lines compared'], rows))
    A(('p', 'Python is the one engine that did not run everything. It is the slow one (the benchmark below puts '
            'its median CPU time at %s times EPA\'s), so the gate gave it the %s models EPA finishes in 1.5 seconds or less, then a sample of the %s '
            'slower ones: the %s that EPA finishes within 4.1 seconds. %s of those %s were identical.'
            % (D['python_speed'], n(py['fast_n']), n(py['slow_n']), n(py['slow_run']), n(py['slow_done']), n(py['slow_run']))))
    A(('p', 'The sample earned its keep. Its first run crashed on one model, Horton_Continuous_Model.inp, where '
            'rain.c hands `sscanf` pointers it was itself given (`int *year`) instead of `&year`. The Python back '
            'end wrapped the second kind for the runtime and passed the first bare. The C# back end had tripped on '
            'the same construct in its own first gate run and been given a special case for it; the Python back '
            'end, written afterwards, never inherited it. The fix went into the '
            'translator, the regenerated engine changed in exactly four calls, and the whole Python gate, fast set '
            'and sample, was run again; the numbers above are from that rerun.'))
    if new_ran:
        A(('p', 'TypeScript and Java ran every model. An earlier build of the TypeScript engine, before its `pow` fast '
                'path, was gated first (%s of %s identical; the stored run does not say which build ran, so that rests '
                'on the session\'s account in `gate/RUNS.md`), then the final build, in four quarters so that no single job ran '
                'longer than the session allows. Both final engines were then gated a second time, because I had '
                'deleted the first final runs\' output files to free disk before the app could re-check them (the app '
                're-hashes every engine\'s files and does not take the gate\'s word). %s; the table gives the second.'
                % (n(D.get('ts_first_pass', 0)), n(D['n_models']),
                   ('The first final runs were identical on all %s models in both languages' % n(D['n_models'])
                    if D.get('ts_final1_pass') == D.get('java_final1_pass') == D['n_models'] else
                    'The first final runs gave %s (TypeScript) and %s (Java) of %s'
                    % (n(D.get('ts_final1_pass', 0)), n(D.get('java_final1_pass', 0)), n(D['n_models']))))))
        jf = D.get('java_first') or {}
        if jf.get('crashed'):
            A(('p', 'Java\'s first run, started (by the session\'s account in `gate/RUNS.md`) with a plain `java -jar`, passed %s of %s and crashed on %s with "Java heap '
                    'space". That model has 613 RDII unit-hydrograph groups whose slow response lasts 9,900 hours, and rdii.c keeps '
                    'the rainfall history of each at the one-minute wet step: 3.38 GB of arrays (`gate/rdii_memory.py`). EPA\'s own '
                    'peak resident size on it is 3.11 GB (`gate/results/peak_memory.txt`), and the Java virtual machine\'s default heap is a quarter of the '
                    'machine\'s memory. The repository\'s launcher, `java/runswmm`, gives it three quarters and the '
                    'parallel collector, and the final Java run in the table went through that launcher (`gate/RUNS.md`). '
                    'Run again for this essay with a plain `java -jar`, the model still stops with "Java heap space" '
                    '(`gate/results/peak_memory.txt`).'
                    % (n(jf['passed']), n(jf['n']), ', '.join(jf['crashed']))))

    # ------------------------------------------------------------------ 10
    A(('h2', 'controls', 'Proving the gate can fail'))
    A(('p', 'A test that cannot fail tells you nothing, so the gate had to prove it would catch a difference when '
            'there was one, and stay quiet when there was not.'))
    A(('p', 'The quiet case first. EPA was run a second time on a %d-model control set, and every file came out '
            'identical to the stored reference: %d of %d. The reference is repeatable, so any difference the gate '
            'finds belongs to the engine under test.' % (C['epa_rerun_n'], C['epa_rerun_same'], C['epa_rerun_n'])))
    A(('p', 'Then the loud case. The Fortran engine was rebuilt with fused multiply-add allowed: `-ffp-contract=fast '
            '-mfma` in place of `-ffp-contract=off`, and nothing else (`gate/build_fma_control.sh`). The first flag '
            'lets the compiler fuse; the second gives it the instruction to fuse with, which the x86-64 baseline '
            'lacks. The control build holds %d fused instructions and the shipped build none. It differed from EPA '
            'on %d of the %d control models and on %d of all %d models.'
            % (C.get('fma_instr', 0), C['fma40_n'] - C['fma40_same'], C['fma40_n'], C['fma_all_n'] - C['fma_all_same'],
               C['fma_all_n'])))
    A(('p', C.get('fma_examples', '')))
    A(('fig', 'controls', 'Figure 8. The null control comes back identical. The positive control, one rounding rule '
                          'changed, is caught on some models and missed on the rest.'))
    A(('p', 'That second number deserves a moment, because it cuts both ways. Under this one perturbation, most '
            'models came back identical: rounding once instead of twice never reached what they print or store. A '
            'model that cannot notice such a change proves little on its own about last-bit agreement. The '
            'evidence that the ports compute bit for bit what EPA computes rests on the %d models that would have '
            'noticed, and on how many different code paths they cover. That is why the gate runs the whole set and '
            'not a handful.' % (C['fma_all_n'] - C['fma_all_same'])))

    # ------------------------------------------------------------------ 11
    A(('h2', 'defects', 'What EPA got wrong'))
    A(('p', 'A byte-exact port is a hard reader of the code it copies. Five defects in EPA 5.2.4 came to light along '
            'the way. Where EPA\'s behaviour is defined, even when it is wrong, as with the integer overflow, each '
            'port copies it, because the job was to match EPA, not to fix it. Where it is undefined (reading past '
            'the end of an array, writing past a buffer, using memory it never cleared) there is nothing defined to '
            'copy; the ports do the safe thing, and the register says which gate models, if any, reach that code. '
            'The register lists them so they can be fixed upstream deliberately.'))
    A(('table', ['#', 'Where', 'The code', 'What happens'], [[d['n'], d['where'], d['code'], d['what']] for d in D['defects']]))

    # ------------------------------------------------------------------ 12
    A(('h2', 'speed', 'What it costs to run'))
    if B:
        A(('p', 'Speed was measured on %d models chosen to span EPA run times from %.2f to %.2f seconds. In each of %d '
                'repetitions, every engine ran every model in a fresh random order, and EPA ran twice. Each ratio is '
                'the engine\'s median CPU time over the repetitions divided by EPA\'s. EPA\'s second copy, measured the same way, lands between %.2f and '
                '%.2f of the first on every model: that is the noise floor. Single runs scatter much wider, %.2f to '
                '%.2f, which is why nothing here rests on one run. All %d models are short; the long ones were not '
                'timed, so these are ratios for short runs. The Python timings are from the engine before the scanf '
                'fix described above, which changed four calls that none of these models reaches.'
                % (B['n_models'], B['epa_min'], B['epa_max'], B['reps'], B['noise'][0], B['noise'][1],
                   B['noise_pairs'][0], B['noise_pairs'][1], B['n_models'])))
        A(('fig', 'speed', 'Figure 9. CPU time against EPA on the same model. C++, ' + ('Rust ' if 'Rust' in B['median'] else '') + 'and Fortran sit near EPA, C# pays for '
                           'its runtime on short models, and Python pays for being Python.'
                           + (' TypeScript and Java pay for a virtual machine and for doing glibc\'s arithmetic in it.' if 'TypeScript' in B['median'] else '')))
        A(('table', ['Engine', 'Median CPU time vs EPA', 'Range over models', 'Start-up (s)'],
           [[e, '%.2fx' % B['median'][e], '%.2f-%.2fx' % (min(B['per_model'][e]), max(B['per_model'][e])),
             '%.3f' % B['startup'].get(e, 0)] for e in B['engines']]))
        A(('p', 'Read the first row first: EPA against itself, %.2f to %.2f. swmm5-cplus, built with link-time '
                'optimization, has a median of %.2f, just below that band, but model by model it runs from %.2f to '
                '%.2f and is slower than EPA on %d of the %d. Call it a tie with a slight lean its way.'
                % (B['noise'][0], B['noise'][1], B['median']['C++'], min(B['per_model']['C++']),
                   max(B['per_model']['C++']), sum(1 for v in B['per_model']['C++'] if v > 1.0), B['n_models'])))
        if 'Rust' in B['median']:
            rv = B['per_model']['Rust']
            A(('p', 'swmm5-rust joined later, after the session had moved to a fresh machine, so it was timed in a run '
                    'of its own: interleaved with EPA on the same %d models, %d repetitions, every ratio against EPA on '
                    'that same machine. EPA against itself spread wider there, %.2f to %.2f. Rust\'s median is %.2f '
                    'times EPA, from %.2f to %.2f model by model, and above EPA\'s band on %d of the %d: a tenth or so '
                    'slower. Its own repository, measured separately, reports 1.12 times at the median, and its '
                    'instruction-count profile puts over a third of the extra work on one model in xsect.c\'s '
                    '`lookup()`, the same table lookup that leads the Fortran profile below.'
                    % (B['n_models'], B['rust_reps'], B['rust_noise'][0], B['rust_noise'][1], B['median']['Rust'],
                       min(rv), max(rv), sum(1 for v in rv if v > B['rust_noise'][1]), B['n_models'])))
        A(('p', 'The Fortran port is the one that should make you raise an eyebrow: %.2f times EPA, between %.2f and '
                '%.2f on every model timed. Same arithmetic, same library, and a quarter more work. I did not run '
                'that down. A gprof profile of the longest benchmark model, 10_Subs_Continuous.inp (kept with the stored '
                'results as `fortran_gprof.txt`), spreads the time over the engineering routines (the cross-section '
                'table lookup is called twelve million times), with the runtime\'s helpers showing up beside them: '
                'the checked double-to-integer conversion is called thirteen million times. EPA was not profiled, so '
                'this says where the Fortran spends its time, not where it spends more than EPA. '
                'The run is short, well under a second of samples, so the percentages are rough; the call counts are '
                'exact. No single culprit; a translation that buys sameness pays for it in small coin, everywhere.'
                % (B['median']['Fortran'], min(B['per_model']['Fortran']), max(B['per_model']['Fortran']))))
        cs_long = [c for t, c in zip(B['epa_t'], B['per_model']['C#']) if t >= 0.17]
        cs_short = [c for t, c in zip(B['epa_t'], B['per_model']['C#']) if t < 0.17]
        A(('p', 'C# has no typical ratio; its models fall into two groups. On the %d that EPA runs in 0.17 seconds or '
                'more, C# costs %.1f to %.1f times EPA. On the %d shorter ones it costs %.1f to %.0f times, climbing '
                'as the run gets shorter, because fixed costs swamp the work: starting .NET alone takes %.2f seconds '
                '(timed with `--version`), and compiling the engine\'s methods just in time comes on top of that; I '
                'did not time the compiling separately. The median of all twelve, %.1f, falls between the groups and '
                'describes neither. Python\'s median is %.0f times EPA, and its models stay between %.0f and %.0f. '
                'That is the price of byte identity in a language where every number is an object: the answer is the '
                'same, and it takes longer to get it.'
                % (len(cs_long), min(cs_long), max(cs_long), len(cs_short), min(cs_short), max(cs_short),
                   B['startup']['C#'], B['median']['C#'], B['median']['Python'], min(B['per_model']['Python']),
                   max(B['per_model']['Python']))))
        if 'TypeScript' in B['median'] and 'Java' in B['median']:
            tv, jv = B['per_model']['TypeScript'], B['per_model']['Java']
            ts_long = [c for t, c in zip(B['epa_t'], tv) if t >= 0.17]
            j_long = [c for t, c in zip(B['epa_t'], jv) if t >= 0.17]
            A(('p', ('TypeScript and Java were timed last, in a run of their own: the same %d models, %d repetitions, '
                    'interleaved with EPA and EPA again, every ratio against EPA in that run (EPA against itself there: '
                    '%.2f to %.2f). Java\'s median is %.2f times EPA, from %.2f to %.2f; starting the Java virtual '
                    'machine alone takes %.2f seconds, and on the %d models EPA runs in 0.17 seconds or more (in the main benchmark) Java costs '
                    '%.1f to %.1f times. TypeScript\'s median is %.2f, from %.2f to %.2f (%.1f to %.1f on those same '
                    'models), with %.2f seconds to start Node. Part of TypeScript\'s price is the mathematics: a '
                    'fused multiply-add the hardware does in one instruction costs the TypeScript runtime a few dozen '
                    'floating-point operations, and its `pow` makes sixteen of them on its common path.'
                    % (B['n_models'], B['tsj_reps'], B['tsj_noise'][0], B['tsj_noise'][1], B['median']['Java'], min(jv), max(jv),
                       B['startup'].get('Java', 0), len(j_long), min(j_long), max(j_long), B['median']['TypeScript'],
                       min(tv), max(tv), min(ts_long), max(ts_long), B['startup'].get('TypeScript', 0)))
                    + (' Timed against the same engines built with their own languages\' `Math` (%d repetitions, '
                       '`gate/results/bench_math.json`), the copy of glibc makes TypeScript a median %.2f times as slow (%.2f '
                       'to %.2f by model) and Java %.2f times (%.2f to %.2f): about a quarter of TypeScript\'s time and a '
                       'tenth of Java\'s. That run had no EPA-against-itself control; a Java ratio below 1 shows its '
                       'noise is at least that large.'
                       % tuple(B['math_cost']) if B.get('math_cost') else '')))
    else:
        A(('p', 'The benchmark has not been run yet.'))

    # ------------------------------------------------------------------ 13
    A(('h2', 'limits', 'What this does not show'))
    A(('fig', 'coverage', 'Figure 10. How many of the %s gate models that ran without an input error use each '
                          'feature. Orange bars are features exercised by fewer than ten models; %d are not exercised '
                          'at all: %s.' % (n(cens['ran']), len(cens['not_exercised']), ', '.join(cens['not_exercised']))))
    A(('ul', [
        'It does not show that SWMM is right. Identical to EPA means EPA\'s answers, good or bad. No observed flow '
        'enters anywhere.',
        'It shows one platform: x86-64 Linux, glibc 2.39, gcc 13.3 (`gate/results/toolchain.txt`). On Windows or macOS the math library differs, and '
        'a port matches EPA built there only if its math library matches too.',
        'It shows one kind of processor. EPA itself changes %d models when glibc picks its generic math routines, as '
        'it would on a processor without FMA and AVX2. Fortran, C#, Python, C++ and Rust should follow EPA there, because they '
        'call the same library (this was not tested); TypeScript and Java carry the FMA versions and would not.' % (LM.get('generic_n', 0) - LM.get('generic_same', 0)),
        corpus_note(D),
        '%s of the %s stop on an input error. For %d of those EPA writes no results file and the report is the '
        'whole comparison; the other %d write a short one, which is compared.'
        % (n(cens['error_decks']), n(D['n_models']), cens['error_decks'] - cens['error_decks_with_out'],
           cens['error_decks_with_out']),
        'Some paths are thin or missing. Counting only models that ran, none exercises these: %s. (Street and '
        'inlet hydraulics appear in one deck, which stops on input errors before simulating.) Snow packs appear '
        'in %d models that ran, and only %d of them supply the temperatures snowmelt needs.'
        % ('; '.join(cens['not_exercised']), cens['snow'], cens['snow_temp']),
        'Python ran the %s fast models and %s of the %s slow ones, not all %s.' % (n(py['fast_n']), n(py['slow_run']), n(py['slow_n']), n(D['n_models'])),
        ('swmm5-cplus and swmm5-rust were gated as built from their repositories; how they were made is their own '
         'repositories\' story, and this essay does not re-examine it.' if rust_ran else
         'The Rust engine was not run here: its repository was not reachable from this session.'),
        'Only the command-line path was exercised. The API used for stepping a model from another program '
        '(swmm_step and friends) is translated but was not gated.',
        'The TypeScript and Java math routines were checked against the system libm on the arguments described above, '
        'not proved equal to it; a disagreement on an argument no test reached is possible, though none was found.',
        'No person has read the %s generated lines. The evidence is the gate and the controls, not review.'
        % n(L['f90_gen'] + L['cs_gen'] + L['py_gen'] + L['ts_gen'] + L['java_gen'] + L['libm_ts'] + L['libm_java'])]))

    # ------------------------------------------------------------------ 14
    A(('h2', 'howto', 'How to use the app and the repositories'))
    A(('ul', [
        '**Scoreboard** shows the summary: one row per engine, its gate result and its cost.',
        '**Models** lists every gate model. Filter by folder or name, and open a row to see its report statistics '
        'and each engine\'s output fingerprint.',
        '**Graphs** plots results from the reference .out for a chosen model and object, and under it the difference '
        'of each engine\'s own .out from the reference, period by period.',
        '**Speed** has the benchmark with its noise floor. **Verify** has the parity contract, controls, census and '
        'defect register.',
        'To rebuild an engine, regenerate it with `tools/c2x/emit_f90.py` (or `emit_cs.py`, `emit_py.py`, '
        '`emit_ts.py`, `emit_java.py`), build with `f90/build.sh`, `cs/build.sh`, `npm run build` in `ts/` or '
        '`java/build.sh`, then run `gate/gate.py NAME "ENGINE"` against the stored reference outputs. '
        '`tools/libm/make_libm.sh` regenerates the math routines from glibc\'s source, and '
        '`tools/libm/test/run_tests.sh` checks them against the system libm.']))

    # ------------------------------------------------------------------ 15
    A(('h2', 'ai', 'Use of AI'))
    A(('p', D['ai_use']))
    return out
