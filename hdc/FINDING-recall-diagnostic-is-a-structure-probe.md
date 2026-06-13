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
