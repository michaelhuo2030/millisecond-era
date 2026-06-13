# A recall diagnostic that measures the *shape* of a knowledge graph
### (when "partial recall" is the system reporting structure, not failing)
*millisecond-era · HDC findings · 2026-06-13 · measured, ≥3 seeds, honest*

## The setup
We store verified knowledge as a single high-dimensional **memory algebra** (bind / bundle / reverse-search):
edges `antecedents → consequent` are superposed into one hypervector; a query reverse-searches to recover a
node's ancestors, and recurses to walk a chain. A real test on a biology+chemistry graph gave a recall of
**0.695** — which *looked* like a representation ceiling. It wasn't. The search's "branching" knob (how many
antecedents it recovers per step) was set to 2, but the real biology network had nodes with 3–4 parents.
Open the knob to match → recall **1.000**. The 0.695 was the system **reporting the network's true branching
structure**, not failing.

## The finding
That hints at something reusable: build a tiny **disambiguator** that sweeps the search's own knobs
(branching `max_set`, recursion `max_depth`, threshold, dimension) and names the dominant recall limiter. We
asked: does the *location of the knee* in each relief curve recover the graph's true topology?

**Yes — exactly.** On controlled graphs with a *known* max fan-in `f` and *known* chain depth `d`:

| controlled graph | knee of the branching curve | knee of the depth curve |
|---|---|---|
| fan-in f = 2,3,4,5,6,8 | recovers **f exactly** (2→2 … 8→8) | — |
| chain depth d = 2,3,4,6,8 | — | recovers **d exactly** (2→2 … 8→8) |

**Recovery accuracy = 1.000** across all structures × 3 seeds (33/33 runs). The recall curve is literally
`min(knob, true)/true`, so the saturation knee *is* the true value.

> **So the recall diagnostic doubles as a knowledge-graph *measurement instrument*** — it reads out how
> interconnected the knowledge is (fan-in) and how deep its causal chains run (depth). It doesn't just fix
> recall; it measures the topology of what you stored.

## Confirmed on a real knowledge graph (Hetionet)
We then took it to a real, open biomedical graph — Hetionet (~47k nodes / 2.25M edges, built from CTD + 28
public resources). A unified memory chaining `Disease → Gene → {Compound, Pathway, regulating Gene}` recalled
the full cross-domain set at only **0.65** — which again *looked* like a representation ceiling. It wasn't. The
relief curve:

| max_set | 4 | 6 | 8 | 10 | 12 | 14 | 16 | 20 |
|---|---|---|---|---|---|---|---|---|
| recall | 0.49 | 0.66 | 0.80 | 0.90 | 0.96 | 0.97 | 0.98 | **0.99** |

The knee sits at **max_set ≈ 14**. We had predicted ≈12 from first principles — a *gene* is pointed at by three
relation types at once (drugs, pathways, other genes), so its effective fan-in is ~3× the per-relation cap. **The
recall curve recovered that real-biology hub size on its own**, and opening the knob took recall **0.65 → 0.99**.
Two clean routes reach it: match `max_set` to the effective fan-in, or *type* the edges (one role key per
relation) — the latter reaches 0.96 at a quarter of the search effort and is the faithful model of a typed graph.
Robust across 4 encodings × 3 seeds at adequate dimension (0.95–0.97). A second, independent limiter — capacity
(dimension) — bites only when D is undersized. *(This also corrected one of our own earlier write-ups, which had
called the 0.65 gap a "residual representation" limit; it was the tool. Suspect-the-tool includes your own
theory.)*

## The companion discipline (the faith principle, quantified)
A small census across a battery of recall tasks: of the "apparent ceilings" (recall < 1.0 at the default
config), **~75% were tool artifacts** — a knob set wrong — not real ceilings. Only one was a genuine residual
limit. Operational rule: **before calling any number a ceiling, sweep the tool's knobs; most "walls" are your
own settings.**

## Honest scope
- The knee↔structure recovery is on controlled synthetic graphs (clean fan-in/depth); on messy real graphs
  the knee reports the *effective* fan-in/depth at the recovery threshold — re-measure per corpus.
- The census fraction depends on the battery; the point is qualitative ("most ceilings are tool artifacts"),
  and one bare-disambiguator mislabel (representational confusion read as branching) is itself a known
  boundary, fixed by a precision-at-relief check.

*Reproduce: `disambiguator.py`, `disambiguator_structure_probe.py` (in the universal-algebra kit). Every claim
above is emitted to the experiment ledger.*
