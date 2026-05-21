"""
HDC Code Archaeology — Semantic Git Search
Encodes git commits as hypervectors, enables semantic search across history.

No embeddings, no training. Just text n-grams → HDC → cosine search.

Run: python3 code_archaeology.py [--repo /tmp/millisecond-era]
"""
import sys, os, time, subprocess, argparse
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from reram_hdc_sdk import encode_level

D        = 10_000
N_LEVELS = 100
N_GRAM   = 3


class Backend:
    def __init__(self, d):
        self.d = d; self.rng = np.random.default_rng(42)
    def random_hv(self): return (self.rng.integers(0, 2, self.d) * 2 - 1).astype(np.int8)
    def bind(self, a, b): return (a * b).astype(np.int8)
    def bundle(self, hvs):
        arr = np.stack(hvs) if not isinstance(hvs, np.ndarray) else hvs
        s = arr.astype(np.int32).sum(axis=0)
        r = np.where(s >= 0, 1, -1).astype(np.int8)
        ties = (s == 0); r[ties] = (self.rng.integers(0, 2, int(ties.sum())) * 2 - 1).astype(np.int8)
        return r
    def permute(self, hv, n): return np.roll(hv, n)
    def cos(self, a, b):
        af, bf = a.astype(np.float32), b.astype(np.float32)
        return float(np.dot(af, bf) / (np.linalg.norm(af) * np.linalg.norm(bf) + 1e-9))


def make_level_hvs(n, d, seed=99):
    rng = np.random.default_rng(seed)
    base = (rng.integers(0, 2, d) * 2 - 1).astype(np.int8)
    lvls = [base.copy()]; nf = d // n
    for _ in range(1, n):
        hv = lvls[-1].copy(); idx = rng.choice(d, nf, replace=False)
        hv[idx] *= -1; lvls.append(hv)
    return np.array(lvls, dtype=np.int8)


be      = Backend(D)
lv_hvs  = make_level_hvs(N_LEVELS, D)
# One HV per ASCII character (128 chars)
char_hvs = {i: be.random_hv() for i in range(128)}


def encode_text(text: str, n: int = N_GRAM) -> np.ndarray:
    """Text → HV via character n-gram encoding."""
    text = text.lower()[:300]   # cap length
    if len(text) < n:
        text = text.ljust(n, ' ')
    ngrams = []
    for i in range(len(text) - n + 1):
        hv = char_hvs[ord(text[i]) % 128].copy()
        for j in range(1, n):
            hv = be.bind(hv, be.permute(char_hvs[ord(text[i + j]) % 128], j))
        ngrams.append(hv)
    return be.bundle(ngrams) if ngrams else be.random_hv()


def get_commits(repo_path: str) -> list:
    """Get commits from git log with message + changed files."""
    try:
        log = subprocess.check_output(
            ['git', 'log', '--oneline', '--no-merges'],
            cwd=repo_path, text=True, stderr=subprocess.DEVNULL
        ).strip().split('\n')
    except Exception as e:
        print(f"git log failed: {e}"); return []

    commits = []
    for line in log:
        if not line.strip(): continue
        parts = line.split(' ', 1)
        if len(parts) < 2: continue
        h, msg = parts[0], parts[1]
        # Get changed files
        try:
            stat = subprocess.check_output(
                ['git', 'show', '--stat', '--format=', h],
                cwd=repo_path, text=True, stderr=subprocess.DEVNULL
            ).strip()
            # Extract just file names from stat
            file_lines = [l.split('|')[0].strip() for l in stat.split('\n')
                          if '|' in l]
            files_text = ' '.join(file_lines)
        except Exception:
            files_text = ''
        commits.append({'hash': h, 'msg': msg, 'files': files_text,
                        'full': msg + ' ' + files_text})
    return commits


def semantic_search(query: str, commit_hvs: dict, top_k: int = 4) -> list:
    q_hv = encode_text(query)
    sims = {h: be.cos(q_hv, hv) for h, hv in commit_hvs.items()}
    return sorted(sims.items(), key=lambda x: -x[1])[:top_k]


def run(repo_path: str):
    print("=" * 65)
    print("HDC Code Archaeology — Semantic Git Search")
    print(f"D={D:,}  n-gram={N_GRAM}  repo={repo_path}")
    print("=" * 65)

    commits = get_commits(repo_path)
    if not commits:
        print("No commits found."); return

    print(f"\nEncoding {len(commits)} commits...")
    t0 = time.perf_counter()
    commit_hvs   = {}   # hash → hv
    commit_index = {}   # hash → info dict
    for c in commits:
        commit_hvs[c['hash']] = encode_text(c['full'])
        commit_index[c['hash']] = c
    t_enc = (time.perf_counter() - t0) * 1000
    print(f"Encoded in {t_enc:.0f}ms  ({t_enc/len(commits):.1f}ms/commit)")

    print(f"\nAll commits:")
    for c in commits:
        print(f"  [{c['hash']}] {c['msg'][:70]}")

    # ── Semantic search queries ─────────────────────────────────────────────
    QUERIES = [
        "sign language deaf recognition",
        "real data MSL mexican",
        "avatar gesture blend weights",
        "multimodal binding episode",
        "bug fix error correction",
        "audio voice speaker",
        "silicon hippocampus article",
        "dataset download registry",
    ]

    print(f"\n{'='*65}")
    print("SEMANTIC SEARCH RESULTS")
    print(f"{'='*65}")
    t_start = time.perf_counter()
    for query in QUERIES:
        results = semantic_search(query, commit_hvs, top_k=3)
        print(f"\nQuery: \"{query}\"")
        for i, (h, sim) in enumerate(results, 1):
            msg = commit_index[h]['msg'][:60]
            print(f"  {i}. [{h}] {msg:<60}  sim={sim:+.3f}")
    t_search = (time.perf_counter() - t_start) * 1000
    n_queries = len(QUERIES)
    print(f"\n{n_queries} queries in {t_search:.1f}ms  →  {t_search/n_queries:.2f} ms/query")

    # ── Cluster analysis ────────────────────────────────────────────────────
    print(f"\n{'='*65}")
    print("COMMIT CLUSTERING — Most Related Pairs")
    print(f"{'='*65}")
    hashes = list(commit_hvs.keys())
    n = len(hashes)
    pairs = []
    for i in range(n):
        for j in range(i + 1, n):
            sim = be.cos(commit_hvs[hashes[i]], commit_hvs[hashes[j]])
            pairs.append((sim, hashes[i], hashes[j]))
    pairs.sort(reverse=True)

    print("\nTop 5 most related commit pairs:")
    for sim, h1, h2 in pairs[:5]:
        m1 = commit_index[h1]['msg'][:35]
        m2 = commit_index[h2]['msg'][:35]
        print(f"  sim={sim:+.3f}  [{h1}] {m1}")
        print(f"           ↔  [{h2}] {m2}")

    # Most unique commit
    avg_sims = {}
    for h in hashes:
        others = [be.cos(commit_hvs[h], commit_hvs[h2]) for h2 in hashes if h2 != h]
        avg_sims[h] = np.mean(others) if others else 0.0
    most_unique = min(avg_sims, key=avg_sims.get)
    print(f"\nMost unique commit (lowest avg similarity):")
    print(f"  [{most_unique}] {commit_index[most_unique]['msg']}")
    print(f"  avg_sim={avg_sims[most_unique]:+.3f}")

    # ── Save ────────────────────────────────────────────────────────────────
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "code-archaeology-results-2026-05-21.txt")
    with open(out, 'w') as f:
        f.write(f"HDC Code Archaeology  D={D}  n-gram={N_GRAM}\n")
        f.write(f"{len(commits)} commits encoded, {n_queries} queries run\n\n")
        for query in QUERIES:
            results = semantic_search(query, commit_hvs, top_k=2)
            f.write(f"Query: '{query}'\n")
            for h, sim in results:
                f.write(f"  [{h}] {commit_index[h]['msg'][:70]}  sim={sim:+.3f}\n")
            f.write("\n")
    print(f"\nResults saved: {out}")

    print(f"\n{'='*65}")
    print("HDC Code Archaeology — key insight:")
    print("Semantic similarity across commits WITHOUT training or embeddings.")
    print("Same 200-line HDC math — swap audio→text, same pipeline.")
    print(f"{'='*65}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--repo', default='/tmp/millisecond-era')
    args = parser.parse_args()
    run(args.repo)
