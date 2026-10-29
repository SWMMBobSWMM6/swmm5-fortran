"""build_aux_data.py - regenerate the two small data files build_app.py reads besides models.json:

  data/front_stats.json  translator front-end tables (files, functions, globals, records, enum constants)
                         and the pointer classification counts, from tools/c2x/front.py over ref/epa524/solver
  data/files_use.json    which gate models use each [FILES] directive (USE/SAVE HOTSTART, RUNOFF, RDII,
                         INFLOWS, OUTFLOWS) and which read a climate file ([TEMPERATURE] FILE), from the
                         .inp files listed in gate/models_all.tsv

Run from anywhere: python3 tools/app/build_aux_data.py   (needs libclang, like the translator)
Written by Claude (Anthropic); see AI-USE.md.
"""
import collections, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'tools', 'c2x'))


def front_stats():
    import front
    F = front.Front()
    P = front.PtrInfo(F)
    arrays = sum(1 for k in P.mode if k in P.decl and
                 front.canon(P.decl[k].type).kind in (front.T.CONSTANTARRAY, front.T.INCOMPLETEARRAY))
    return dict(modes=dict(collections.Counter(P.mode.values())), files=len(F.tus), functions=len(F.funcs),
                globals=len(F.globals), records=len(F.records), enums=len(F.enum_consts),
                declared_arrays=arrays, decls=len(P.mode))


def files_use():
    corpus = os.environ.get('SWMM_CORPUS', os.path.join(ROOT, '..', '1729-SWMM5-Models-2030'))
    use = collections.defaultdict(list)
    for line in open(os.path.join(ROOT, 'gate', 'models_all.tsv')):
        mid, path = line.rstrip('\n').split('\t')
        if not os.path.isabs(path):
            path = os.path.join(corpus, path)
        sec = None
        for raw in open(path, encoding='latin-1'):
            s = raw.split(';')[0].strip()
            if not s:
                continue
            if s.startswith('['):
                sec = s.upper()
                continue
            if sec == '[FILES]':
                t = s.split()
                if len(t) >= 2:
                    use[t[0].upper() + ' ' + t[1].upper()].append(mid)
            elif sec == '[TEMPERATURE]' and s.split()[0].upper() == 'FILE' and mid not in use['CLIMATE FILE']:
                use['CLIMATE FILE'].append(mid)
    return dict(use)


if __name__ == '__main__':
    out = os.path.join(HERE, 'data')
    os.makedirs(out, exist_ok=True)
    fu = files_use()
    json.dump(fu, open(os.path.join(out, 'files_use.json'), 'w'), indent=1)
    print('files_use', {k: len(v) for k, v in fu.items()})
    if '--files-only' not in sys.argv:
        fs = front_stats()
        json.dump(fs, open(os.path.join(out, 'front_stats.json'), 'w'), indent=1)
        print('front_stats', fs)
