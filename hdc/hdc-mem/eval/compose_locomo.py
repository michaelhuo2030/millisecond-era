"""
compose_locomo.py — turn the LoCoMo compose-gap from MOTIVATION into a public-data WIN (trinity-lite).

Idea: LoCoMo gives real structure WITHOUT a heavy LLM — every turn has a SPEAKER, and most questions name
the person they ask about. The trinity: extract the speaker from the question (name-match), bind it.
  turn_HV  = norm(R_c ⊙ emb(turn))  + α · norm(R_s ⊙ A_spk[turn.speaker])
  query_HV = norm(R_c ⊙ emb(q))     + α · norm(R_s ⊙ A_spk[detected])         (content-only if no speaker)
With R²=1 and orthogonal speaker atoms, cosine(query_HV, turn_HV) ≈ semantic(q,t) + α²·[same-speaker bonus]
— a SOFT algebraic speaker-boost (compose), robust where a hard filter would over-commit on mis-detection.

PREMORTEM (so I can't manufacture a win):
  * Fair baselines, all 3 reported: (1) flat bge cosine; (2) flat + HARD speaker filter (the strong baseline
    that ALSO uses the speaker — does algebra beat explicit filtering?); (3) HDC soft-compose.
  * If compose ≈ flat+filter → value is "composable/soft, no enumerated filter", not recall. Honest.
  * If compose < flat → the speaker term adds noise; report it straight.
  * Speaker detection is dumb name-substring (no peeking at the answer). Undetected → content-only (no cheat).
  * 3 atom-seeds ±SE. recall@5 stratified single vs multi-evidence (the compose-relevant split).
  * Embedding (heavy) reuses aux-cached turn vectors; only questions are embedded fresh.
"""
import sys, os, json, ast, argparse
_thr = os.environ.get('LOCOMO_THREADS', '4')
for _v in ('OMP_NUM_THREADS','MKL_NUM_THREADS','OPENBLAS_NUM_THREADS','VECLIB_MAXIMUM_THREADS','NUMEXPR_NUM_THREADS'):
    os.environ.setdefault(_v, _thr)
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.environ.get('LOCOMO_DATA', '/tmp/locomo.json')
MODEL = os.environ.get('LOCOMO_MODEL', 'BAAI/bge-m3')
EMB = os.environ.get('LOCOMO_CACHE', '/tmp/locomo_emb_{i}.npy')

def flatten(conv):
    c = conv['conversation']; turns = []
    for s in range(1, 40):
        k = f'session_{s}'
        if k in c:
            for t in c[k]:
                turns.append({'speaker': t['speaker'], 'dia_id': t['dia_id'], 'text': t.get('text','')})
    return turns

def speakers(conv):
    c = conv['conversation']; return [c.get('speaker_a',''), c.get('speaker_b','')]

def detect(qtext, spk):
    hit = [s for s in spk if s and s.split()[0].lower() in qtext.lower()]
    return hit[0] if len(hit) == 1 else None        # exactly one named speaker -> usable; else content-only

def recall_at(order, gold, k):
    top = set(order[:k]); return len(set(gold) & top) / len(gold)

def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--poc', action='store_true')
    ap.add_argument('--alphas', type=float, nargs='+', default=[0.5, 1.0])
    ap.add_argument('--seeds', type=int, nargs='+', default=[0,1,2]); ap.add_argument('--k', type=int, default=5)
    a = ap.parse_args()
    import torch; torch.set_num_threads(int(_thr))
    from sentence_transformers import SentenceTransformer
    print(f'# compose_locomo model={MODEL} threads={_thr}', flush=True)
    model = SentenceTransformer(MODEL)
    d = json.load(open(DATA)); convs = [0] if a.poc else list(range(len(d)))

    # accumulators: method -> stratum -> list of recalls
    res = {m: {'1': [], 'M': []} for m in ['flat', 'flat+spkfilter'] + [f'compose@{al}' for al in a.alphas]}
    spk_detected = 0; spk_total = 0
    for i in convs:
        turns = flatten(d[i]); spk = speakers(d[i])
        cache = EMB.format(i=i)
        E = np.load(cache) if os.path.exists(cache) else model.encode([t['text'] for t in turns], normalize_embeddings=True, batch_size=128).astype(np.float32)
        if not os.path.exists(cache):
            np.save(cache, E)
        En = E / (np.linalg.norm(E, axis=1, keepdims=True) + 1e-9)
        dim = E.shape[1]
        sp_idx = {s: j for j, s in enumerate(spk)}
        turn_spk = np.array([sp_idx.get(t['speaker'], 0) for t in turns])
        did = {t['dia_id']: j for j, t in enumerate(turns)}
        # questions
        qs, gold, qspk = [], [], []
        for qa in d[i].get('qa', []):
            ev = qa.get('evidence')
            if isinstance(ev, str):
                try: ev = ast.literal_eval(ev)
                except Exception: ev = []
            ev = [did[e] for e in (ev or []) if e in did]
            if not ev or 'question' not in qa: continue
            qs.append(qa['question']); gold.append(ev); qspk.append(detect(qa['question'], spk))
        if not qs: continue
        Q = model.encode(qs, normalize_embeddings=True, batch_size=128).astype(np.float32)
        Qn = Q / (np.linalg.norm(Q, axis=1, keepdims=True) + 1e-9)
        Sflat = Qn @ En.T                                  # semantic cosine
        spk_total += len(qs); spk_detected += sum(x is not None for x in qspk)
        # per atom-seed (atoms only affect the speaker-bonus orthogonality; content cosine is seed-invariant)
        for seed in a.seeds:
            rng = np.random.default_rng(seed)
            A = np.where(rng.random((2, dim)) < 0.5, -1.0, 1.0)   # speaker atoms
            A = A / np.linalg.norm(A, axis=1, keepdims=True)
            # same-speaker bonus = A_qspk · A_tspk : =1 for same speaker (normalized self-overlap), ~0 for different
            same = np.zeros((len(qs), len(turns)), np.float32)
            for r, qsp in enumerate(qspk):
                if qsp is not None:
                    same[r] = (turn_spk == sp_idx[qsp]).astype(np.float32) * float(A[sp_idx[qsp]] @ A[sp_idx[qsp]])
            for al in a.alphas:
                Scomp = Sflat + (al*al) * same
                for r in range(len(qs)):
                    order = np.argsort(-Scomp[r])
                    res[f'compose@{al}']['M' if len(gold[r])>1 else '1'].append(recall_at(order, gold[r], a.k))
        # baselines (seed-invariant) — compute once
        for r in range(len(qs)):
            strat = 'M' if len(gold[r])>1 else '1'
            res['flat'][strat].append(recall_at(np.argsort(-Sflat[r]), gold[r], a.k))
            if qspk[r] is not None:                         # hard speaker filter
                mask = (turn_spk == sp_idx[qspk[r]])
                sc = np.where(mask, Sflat[r], -1e9)
                res['flat+spkfilter'][strat].append(recall_at(np.argsort(-sc), gold[r], a.k))
            else:
                res['flat+spkfilter'][strat].append(recall_at(np.argsort(-Sflat[r]), gold[r], a.k))

    def ms(v): return (float(np.mean(v)), float(np.std(v)/np.sqrt(max(len(v),1)))) if v else (0.0,0.0)
    print(f'#### compose_locomo recall@{a.k}  (single n={len(res["flat"]["1"])}, multi n={len(res["flat"]["M"])}, speaker-detected {spk_detected}/{spk_total})')
    print(f'# {"method":18s} {"single":>14s} {"multi(compose)":>16s}')
    out = {}
    for m in res:
        s1, e1 = ms(res[m]['1']); sM, eM = ms(res[m]['M'])
        out[m] = {'single': s1, 'single_se': e1, 'multi': sM, 'multi_se': eM}
        print(f'  {m:18s} {s1:.3f}±{e1:.3f}   {sM:.3f}±{eM:.3f}', flush=True)
    json.dump(out, open(HERE+'/RESULTS-locomo-compose.json','w'), indent=2)
    print('# DONE_COMPOSE_LOCOMO')

if __name__ == '__main__':
    main()
