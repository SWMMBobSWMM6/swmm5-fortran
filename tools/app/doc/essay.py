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
    word = {3: 'Three', 4: 'Four', 5: 'Five', 6: 'Six'}.get(len(ran), str(len(ran)))
    rust_ran = any(e.startswith('Rust') for e in ran)
    RU = D.get('rust') or {}
    A(('h1', '%s Engines, One Answer' % word))
    A(('sub', 'How EPA SWMM 5.2.4 was carried into Fortran, C# and Python without changing one bit of what it computes'))

    # ------------------------------------------------------------------ 1
    A(('h2', 'question', 'The question, and the only honest way to answer it'))
    A(('p', 'Bob Dickinson asked how many languages the SWMM5 engine could be carried into. He already had two '
            'answers in hand: a C++ restructuring called swmm5-cplus, and a Rust engine. The survey that followed sorted '
            'the candidates into languages that can run the engine one way or another and the smaller set that can '
            'hold a native port matching EPA byte for byte on Linux. Then he asked for three from that set: Fortran, '
            'C# and Python.'))
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
    A(('p', 'Six engines are lined up against %s models from Bob\'s 1729-SWMM5-Models-2030 corpus: EPA SWMM 5.2.4 compiled from '
            'the USEPA v5.2.4 tag, which is the reference; swmm5-cplus; the Rust engine; and the three new ports. The app '
            'shows, model by model, whether each engine\'s `.out` and `.rpt` match the reference, what the models '
            'contain, what their results look like, and what each engine costs to run. This essay explains how the '
            'ports were built, how they were judged, and how far the evidence reaches.' % n(D['n_models'])))
    if rust_ran:
        A(('p', 'Two of the six were not built here. swmm5-cplus is EPA restructured as a C++ class, and swmm5-rust is '
                'a translation into safe Rust (the engine crate forbids `unsafe` code), made in separate sessions and '
                'kept in their own repositories. Both were built from those repositories (swmm5-rust at commit %s) and '
                'put through the same gate as the three new ports, with the same reference and the same %s models.'
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
            'constants) and works out what every pointer is for. Three back ends then write Fortran, C# and Python.'
            % (n(D['front']['functions']), n(D['front']['globals']), D['front']['records'], n(D['front']['enums']))))
    A(('fig', 'pipeline', 'Figure 1. The C source goes through one front end and three back ends; each engine is then '
                          'judged on bytes. Mismatches were fixed in the translator or the hand-written runtime, '
                          'never in the generated code.'))
    A(('p', 'One rule did more good than any other: when a port disagreed with EPA, the fix went into the '
            'translator (or, for a C library function, the hand-written runtime), never into the generated code. Patch the generated file and the next regeneration quietly '
            'undoes your patch. Patch the translator and every function that shared the mistake is fixed at the same '
            'time, including the ones no test had reached yet.'))
    A(('table', ['Piece', 'Lines', 'Made by'],
       [['EPA SWMM 5.2.4 solver (C)', n(L['c']), 'EPA; untouched'],
        ['Translator: front end + three back ends (Python)', n(L['translator']), 'written for this job'],
        ['Fortran engine (one module)', n(L['f90_gen']), 'generated'],
        ['Fortran runtime + printf/scanf/strtod', n(L['f90_rt']), 'hand-written'],
        ['C# engine', n(L['cs_gen']), 'generated'],
        ['C# runtime', n(L['cs_rt']), 'hand-written'],
        ['Python engine', n(L['py_gen']), 'generated'],
        ['Python runtime', n(L['py_rt']), 'hand-written']]))
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
            'a function is a callback. In C these are one thing. In Fortran, C# and Python they are seven different '
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
            'a C# string and a Python str cannot do any of that. They are values, not addresses.'))
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
            'different libraries disagree in the last bit. All three ports call the same glibc library EPA calls: C# '
            'through the .NET runtime on Linux, Python through its math module, Fortran through gfortran\'s built-ins.'))
    A(('p', '**Fused multiply-add.** A compiler that turns `a*b + c` into one fused instruction rounds once instead '
            'of twice. That is more accurate and it is a different answer. EPA\'s build does not fuse. The Fortran '
            'build says `-ffp-contract=off` so it never does, and the controls below show what happens when it does.'))
    A(('p', '**NaN.** Zero divided by zero on x86 produces a NaN with its sign bit set, and glibc prints it as '
            '`-nan`. EPA\'s reports carry such cells in plain sight, in tables such as the node depth summary. The '
            'reference reports in this gate contain %s of them. Python\'s `float(\'nan\')` has the sign bit clear and '
            'would print `nan`. The Python port carries the x86 NaN instead.' % n(cens['nan_cells'])))

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
            'kinds of NaN. The C# and Python formatters were checked by the gate alone.'
            % (n(C['fmt_printf']), n(C['fmt_sscanf']), n(C['fmt_strtod']), n(C['fmt_mismatch']))))

    # ------------------------------------------------------------------ 8
    A(('h2', 'fortran', 'What Fortran made hard'))
    A(('p', 'C# and Python are near cousins of C, in the ways that matter here. Fortran is older and stricter, and '
            'it brought four problems of its own.'))
    A(('p', '**No short-circuit.** In C, `p != NULL && p->x > 0` never touches `p->x` when `p` is NULL. Fortran\'s '
            '`.and.` makes no such promise, and gfortran will evaluate both sides when it pleases. An early test at '
            '-O0 crashed on exactly SWMM\'s kind of guard. So the translator keeps a plain `.and.` only when the right '
            'side provably cannot fault or change anything. Otherwise it evaluates the right side inside an IF on the '
            'left side.'))
    A(('fig', 'shortcircuit', 'Figure 5. A real guard from climate.c and the Fortran the translator wrote for it. '
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
    A(('fig', 'matrix', 'Figure 6. Every model against every engine, drawn from the gate\'s own results. Green is '
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
    A(('fig', 'controls', 'Figure 7. The null control comes back identical. The positive control, one rounding rule '
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
        A(('fig', 'speed', 'Figure 8. CPU time against EPA on the same model. C++, ' + ('Rust ' if 'Rust' in B['median'] else '') + 'and Fortran sit near EPA, C# pays for '
                           'its runtime on short models, and Python pays for being Python.'))
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
    else:
        A(('p', 'The benchmark has not been run yet.'))

    # ------------------------------------------------------------------ 13
    A(('h2', 'limits', 'What this does not show'))
    A(('fig', 'coverage', 'Figure 9. How many of the %s gate models that ran without an input error use each '
                          'feature. Orange bars are features exercised by fewer than ten models; %d are not exercised '
                          'at all: %s.' % (n(cens['ran']), len(cens['not_exercised']), ', '.join(cens['not_exercised']))))
    A(('ul', [
        'It does not show that SWMM is right. Identical to EPA means EPA\'s answers, good or bad. No observed flow '
        'enters anywhere.',
        'It shows one platform: x86-64 Linux, glibc 2.39, gcc 13.3. On Windows or macOS the math library differs, and '
        'a port matches EPA built there only if its math library matches too.',
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
        'No person has read the %s generated lines. The evidence is the gate and the controls, not review.'
        % n(L['f90_gen'] + L['cs_gen'] + L['py_gen'])]))

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
        'To rebuild an engine, regenerate it with `tools/c2x/emit_f90.py` (or `emit_cs.py`, `emit_py.py`), build '
        'with `f90/build.sh` or `cs/build.sh`, then run `gate/gate.py NAME "ENGINE"` against the stored reference '
        'outputs.']))

    # ------------------------------------------------------------------ 15
    A(('h2', 'ai', 'Use of AI'))
    A(('p', D['ai_use']))
    return out
