# How this project is built

millisecond-era is built by one person — a non-EE by training — teaching himself chip design **in public**, with AI as the team. The method matters more than any single result. This is the operating system.

## Operating principles

1. **First principles, no borrowed numbers.** Every load-bearing number is derived from physics or measured in code — not lifted from a slide. Where a value comes from a paper, it's labeled `[literature]`.

2. **MEASURED vs PROJECTED — always labeled.** A claim is `MEASURED` (a saved artifact — CSV/JSON/synth report — backs it), `PROJECTED` (a model/target), or held. The FPGA synthesis (194 MHz, 0 DSP, II=1.0, 99.5% datapath util) is *measured*; 1–4k tok/s is an *ASIC projection*. They never blur.

3. **Correction in public.** When a number is wrong it gets walked back in the open, with the reason. "25 GB/die pure-CIM" was physically infeasible (~1500× SOTA) → corrected to hybrid. A claimed "4-path convergence" was really 3 variants of one method → retracted. The corrections *are* the credibility, not the embarrassment. (See `hdc/HDC-LAWS-REGISTRY.md` L17 — anti-fabrication.)

4. **Frugality + staged de-risking.** ¥0 gates before any spend: FPGA twin (¥0) → open-PDK digital shuttle (¥0) → only then the ~¥50万 ReRAM test-tile. Each rung buys exactly one missing number before the next 10× of spend. Secondhand boards (¥150), borrowed PDKs, real device chips for a few dollars.

5. **Spec-driven, not run-everything.** Name the hypothesis → design the *minimal* experiment that de-risks it → measure only that → gate before the next spend. (See `specs/`.)

6. **AI as the team, in a visible protocol.** One person orchestrates a main reviewer + a compute worker + tool agents, coordinated by written specs, with a hard rule: nothing is "verified" until it's been audited. (See `specs/` + `hdc/HDC-EXPERIMENT-OPS-METHOD.md`.)

7. **Honest boundaries.** Every result states what it does **not** show. FPGA proves the *design*, not product speed. HDC's algebra wins when structure is *given*, ties learned embeddings when structure must be *discovered* (`hdc/HDC-LAWS-REGISTRY.md`, L1).

8. **The method is the moat.** Anyone can copy a number; far fewer can copy the discipline of deciding what's true. That discipline is what's published here.

## Where to look
- `hdc/` — the research laws, the arsenal, the ops-method (how truth is decided).
- `specs/` — how a hard physics question gets de-risked with a $0 experiment.
- `experiments/` — small runnable artifacts that test the thesis directly.
- `article-1.md` / `article-2.md` — the thesis + the validation report (with corrections kept visible).

*合抱之木，生于毫末。 — a tree that fills both arms grows from a tiny shoot.*
