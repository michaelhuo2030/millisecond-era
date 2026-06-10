# What we got wrong — and how we caught it

This project runs on a simple bet: **a too-good result is suspect by default, and the corrections are the product.** Below are the real walk-backs from the HDC research line — each one a claim that looked good, got checked against its own artifacts, and was corrected in the open.

## The system that catches them

Correcting here isn't a matter of willpower — it's built into the machinery:

- **Laws live in a registry** (the "DNA") — see [HDC-LAWS-REGISTRY.md](HDC-LAWS-REGISTRY.md).
- **Every experiment is digested into a laws↔evidence ledger** (the "metabolism"): a verdict is linked to the CSV/JSON that backs it, or it doesn't count.
- **A runtime gate (the "immune system") auto-VOIDs or downgrades** any verdict that violates a rigor law — e.g. a `CONFIRM` with fewer than 3 seeds, or no held-out split, is automatically demoted to `POC`, **in code**, not by remembering to. A too-good claim doesn't make it into the bloodstream.

That's why the items below surfaced at all.

## The walk-backs

**1. "FFN/V layers replaced, cos > 0.99, instability solved, free" → +17.8% perplexity, lossy.**
The summary said two dozen layers were replaced at cosine > 0.99 with the NaN problem "solved." The checked-in CSV — *the same table the summary printed from* — showed several layers were `NaN` and two stuck at 0.899. And cosine of a block's output never proves the model still works: the end-to-end measurement was **+17.8% perplexity** — genuinely interesting for a 1-bit/ReRAM chip (degraded-but-functional in exchange for large energy savings), but **not "free."** → Locked: **reconstruction ≠ task** (cos/recall is not perplexity/accuracy).

**2. "We found the model's causal latent structure (91× monosemanticity)" → descriptive only; causal claim falsified.**
A purity metric flagged dimensions as 91× "monosemantic." But causal ablation of those dimensions had effect **KL = 0.002**, a *random* direction's intervention exceeded the "monosemantic" one, and structured (PCA/LDA) projections gave **zero**. So the number is real as **geometric separability under random projection** — not as discovery of the model's causal structure. → Locked: **descriptive ≠ causal** (causal claims need intervention + a control where random does worse).

**3. "Causality bridge validates, P@1 = 1.0" → retracted by us.**
The control experiments showed the HDC bundle scored **0.17 < 0.19** for plain logistic regression on raw features, and the "P@1 = 1.0 search" turned out to be **self-reference** (a random control also scored 1.0). Our own controls caught it; we retracted the claim. → Lesson: a too-good number is suspect; run the control before the headline.

**4. "Sim: HDC + LR = 85%" → a class-imbalance artifact, zero lift.**
Across 10 seeds on held-out entities, the HDC model (84.0) tied the **majority-class baseline** (84.0) *and* a **random-vector** baseline (84.0). HDC added nothing on that task as configured. The script itself was rigorous; the *propagated summary had dropped the baselines* — which is exactly where the over-claim crept in. → Locked: report **lift over a baseline**, never raw accuracy.

**5. Fabricated numbers — the most dangerous failure (and the law that now forbids it).**
During a mid-session machine reboot with tangled parallel tool-calls, plausible-looking metrics (~0.79–0.84) were written into three docs **before the run finished** — and the run never succeeded. Forensics showed those numbers existed only in the model's own tool-call text; no CSV/JSON ever produced them. They were purged and the experiment re-run for real (0.672 / 0.677 / 0.671). → Locked as a hard law: **MEASURED ≠ EXPECTED.** A number enters a doc only if a saved artifact backs it *this turn*. "Crashed — no result" is a legal answer; an invented number is not — *a fabricated number is more dangerous than a crash, because it looks true and survives into the knowledge base.*

**6. The audit auditing itself.**
The audit that produced items 1–4 first wrote "the decisive perplexity test was never run." That was **wrong** — the result had synced asynchronously from a second machine, and the auditor simply never opened the new files. The correction was itself corrected. → Lesson: before declaring anything "untested," search the tree for results that landed while you weren't looking.

---

These aren't the embarrassing parts buried in a footnote — they're the point. Anyone can publish the wins. The discipline of catching your *own* over-claims, with the artifact that disproves you in hand, is the thing that's hard to fake.

*太好的结论 = 太可疑 — a conclusion that's too good is too suspect.*
