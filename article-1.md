# The Millisecond Era: One Person's Falsifiable Bet on the Next AI-Chip Substrate

*One person. 1.5 months. $1.4K out of pocket. 50+ reproducible datapoints. A thesis about why 28nm ReRAM compute-in-memory could be the substrate flip China can lead — and a set of my own corrections, published in the body, because a thesis that can't survive its own audit isn't worth shipping.*

---

## The reference frame matters more than the claim

Almost all "AI chip" coverage assumes a *static* world: "NVIDIA owns CUDA, China can't catch up, the game is over." Read from that frame, this work looks audacious or naive.

I write from a different frame: **the world is changing.**

- 2005–2025: the AI compute substrate flipped three times — CPU → GPU → ASIC.
- 2025–2045: it will flip again. We don't know exactly to what — but we know the static frame is wrong that "the game is over." In a changing world, standing still is shrinking. Today's CUDA moat is tomorrow's COBOL.

This article documents one bet on what the next flip looks like — empirically grounded, transparently scoped, falsifiable. I don't claim certainty. I claim the static frame produces blindness and the changing frame produces options. This chip is one option.

## TL;DR

I ran DeepSeek V4-Flash on a 128 GB MacBook (thanks to [@antirez](https://github.com/antirez)'s `ds4-server`), measured the indexer's memory growth empirically (25 datapoints, 10K → 250K context), and found it grows **~66× slower** than a linear reading of the README suggests — because the indexer pre-allocates a pool and reuses it.

That fact, plus ten framework-level reframes in 48 hours of multi-AI cross-validation (Kimi + Claude + DeepSeek + MiniMax + me), lets me argue — falsifiably — that a single 28nm hybrid ReRAM-CIM die can serve long-context, on-device LLM inference at **sub-5W (Mini tier)**, at **$850–$5K** product prices.

**What this article actually is:** not a chip pitch. A documentation of the *research methodology* that produces this chip. The chip is the artifact. The methodology is the moat.

## Corrigenda — what I corrected, and why it strengthens the thesis

This is the part most "chip theses" hide. I'm putting it up front. Since the first internal draft, four claims were corrected — three of them *downward*:

- **Speed (down ~5–50× from the original overclaim).** An earlier draft said "5–15K / 10K+ tok/s" — a hopeful extrapolation, not a measured envelope. The realistic envelope: **Mini ~500–2,000 · Mid ~1,000–2,500 · Pro ~220–2,000 tok/s.** Pro's number hinges on **ternary {−1, 0, +1} weights**, which shrink a 27–70B model to ~6–14 GB — small enough to mostly fit *on-compute*, so it's compute-bound (~500–2,000, Mini-tier) rather than weight-streaming-bound (~220–1,000); speculative decoding (a Mini puck drafting for the Pro) reaches several-thousand. **These are pre-silicon estimates — envelopes, not measured silicon.** Exact figures wait for Stage-1.
- **"Runs DeepSeek V4-Flash natively" — retracted for first silicon.** DeepSeek-class (81 GB, *already* INT2–8-compressed from ~170 GB FP16) is not physics-possible to hold natively on one 28nm die — fitting it would need ~270× compression, near the Shannon floor. So **first silicon targets a 27–70B-class model that comfortably fits**; frontier-class is a *later* SKU, once the process is de-risked. 合抱之木，生于毫末.
- **On-die capacity is an extrapolation, not a demo.** Every *published* 28nm ReRAM-CIM macro is small (≤4 Mb). There is no GB-scale demonstration yet, so the capacity figures need fab-partner validation. The honest Pro ceiling is **~48 GB @ 28nm 8-layer** (yield cliff), not 80.
- **Cells are ternary, not 4-bit MLC.** Published 4-bit-MLC RRAM has only ~2-hour retention at 125 °C plus conductance drift that corrupts analog inference. I lean **ternary {−1, 0, +1}**, which tolerates ~10–20× more analog noise — the single largest device-risk reduction available, and externally validated by OpenBMB's near-lossless ternary BitCPM LLM.

**Net:** the claim is no longer "fastest." It's **lowest-energy, on-device, honestly scoped** — the claim I can actually defend with silicon.

## The thesis: the missing hardware layer of DeepSeek's full stack

DeepSeek shipped a full stack — the V4-Flash model, `ds4-server` inference, transparent training. What's missing? **The hardware substrate co-designed for that model architecture.** H100 runs it; M4 runs it; MI300 will. All are general-purpose accelerators retrofitted for an architecture they weren't designed for. None is the substrate DeepSeek would design if they made silicon.

The bet: a 28nm hybrid ReRAM-CIM chip co-designed with V4-Flash's compressed-sparse-attention + hierarchical-compressed-activation, delivering:

- long-context inference on a single die (exact KV-SRAM sizing still being verified);
- **~500–2,000 tok/s (Mini) · ~1,000–2,500 (Mid) · ~220–2,000 (Pro)** — pre-silicon envelopes (see Corrigenda);
- **sub-5W for the Mini tier** vs 200W+ for an H100 — energy, not peak throughput, is the differentiator;
- **ternary {−1, 0, +1} cells**;
- $850 (Mini) / $1.4K (Mid) / $5K (Pro) product tiers.

**We're not the first — hybrid already shipped.** The skeptic asks: "Pure analog ReRAM-CIM died with Mythic. Why does hybrid work?" Because HYDAR (ISSCC 2026) is a hybrid analog/digital RRAM CIM that *just shipped silicon*. The market already decided: not pure analog, not pure digital — **hybrid**. (My own first draft mislabeled HYDAR "pure digital" from a secondhand summary; the official program corrected me to "hybrid." The correction *strengthens* the bet.) Pure analog is dead; pure digital is NVIDIA's expensive domain; hybrid is the 2026 reality, and that's where this chip lives.

**Why 28nm, not 7nm?** China can't manufacture 7nm at scale (the EUV embargo). But ReRAM-CIM doesn't need 7nm — compute-in-memory eliminates 60–80% of the data movement that dominates power and area at advanced nodes, so 28nm × multi-layer hybrid ReRAM-CIM approaches what 14nm pure-digital would deliver for this workload. The constraint shaped a different design space — and that space happens to be near the optimum for LLM edge inference. The substrate advantage isn't *despite* the embargo; it's *because* of it.

## What I've verified (50+ datapoints, reproducible on any M4 Max 128 GB)

The harness is ~280 lines of Python; reproduction takes ~6 hours on an M4 Max; all raw JSONL is public.

**The hidden elegance — pool allocation, not linear growth.** A linear reading of the `ds4-server` README suggests the indexer costs ~22 KB/token. The *code* tells a different story: it pre-allocates a pool at startup, then reuses it. My 25-datapoint measurement shows **~98.5% suppression** of the linear extrapolation — effective ~0.33 KB/token, not 22. This isn't a bug in the README; it's hidden engineering elegance in the code. The implication for hardware is foundational: ReRAM arrays similarly pre-allocate sense-voltage ranges at setup and reuse them. The 22-month thesis I'd been holding became *empirically falsifiable* the night that code ran on my laptop — because his code told a truth his README under-sold.

**The epistemic ladder.** Single-tool bias is what killed Mythic. Before publishing I ran seven layers: (1) hypothesis (deep-research spec); (2) one-pass consistency audit; (3) audit-of-the-audit; (4) independent parallel review (two more models); (5) empirical falsification (25 datapoints on one Mac, 8 on a second); (6) precedent triangulation (PagedAttention, llama.cpp KV benchmarks, 28 chip precedents); (7) the framework reframe — "what if the whole problem statement is wrong?" Layer 7 is the one Mythic lacked.

## What I have NOT verified (the honest matrix)

- The chip itself — no silicon yet. Stage 0+ is an FPGA proof-of-concept (EBAZ4205) running this month; first MPW targets 2027–2028.
- GB-scale ReRAM-CIM density at 28nm — no published demonstration; the capacity figures are extrapolations pending a fab partner.
- The tok/s envelopes — pre-silicon NeuroSim/bandwidth estimates, not measured.
- Ternary-cell yield and retention at production scale — promising in the literature, unproven at our target.

If any of these falls, I'll publish *that* too.

## What this is really about

In 48 hours starting 2026-05-14 I executed **ten framework reframes** — each questioning an assumption I'd treated as solid: KCM mask-ROM economics don't work for LLM-class models; an SRAM-density constant corrected by a parallel audit; the compressed indexer is a separate memory tier I'd missed; a 4-bit→2-bit quant baseline corrected by reading the source; pure-analog→hybrid corrected by ISSCC; and a founder-OS pivot from "raise a Seed round" to "build a 100-person partner network," triggered in meditation.

Each reframe came from a specific source — a README sentence, a calculation, a parallel audit, a harness run, a quiet hour. Not one engineer working harder: seven epistemic layers cross-validating, with the seventh being a person sitting still long enough to ask the framework-questioning question.

**This is not a startup pitch. It's the documentation of a methodology** that happens to produce chip designs as one output. If you leave with "interesting chip thesis," I under-communicated. If you leave with "I want to understand how ten reframes in 48 hours happens," you heard the signal.

## FAQ

**Engineer (China) — when can I plug this in?** Stage 0+ (FPGA PoC) is running this month; production targets 2028–2030. USB-C, no driver hassle. Mini runs Qwen3.5-9B Q4 (a tight fit); Pro targets a 27–70B-class model. (Frontier DeepSeek-V4-class is a later SKU — see Corrigenda.)

**Investor — TAM and exit?** Substrate flips every ~10 years; this one is 2027–2030. Winners of a substrate flip historically see $100B+ TAM. *However: I'm not raising.* Year-1 budget is $4K–$7K out of pocket; the goal is a 100-partner network, not a Seed round. If you want in, terms are equal — not a pitch, not a plea.

**Academic — reproducibility?** 50+ datapoints, a ~280-line Python harness, public on GitHub; an M4 Max 128 GB is the only requirement; raw JSONL attached for every measurement. Replicate before you cite.

**Policy / state capital — fit with China's chip strategy?** 28nm is the highest node China makes at scale (SMIC); the 7nm dependence is the bottleneck. For LLM edge inference, 28nm hybrid ReRAM-CIM can beat 14nm pure-digital by killing the data-movement penalty. It leverages existing 28nm capacity + domestic ReRAM IP, with no 7nm dependence. First MPW 2027–2028; capital intensity for the substrate-layer thesis is $110K–$210K for first silicon — orders of magnitude below a mainstream chip Series A.

**Developer / end user — cost and timing?** $850 / $1.4K / $5K tiers, USB-C plug-and-play, long-context. Mini runs Qwen3.5-9B Q4; Pro a 27–70B-class model. Production 2028–2030; the GitHub repo updates weekly as Stage 0+ data ships.

**Technical reader — is the data trustworthy?** 25 datapoints, M4 Max 128 GB, RSS via PID-anchored psutil, independently reproduced on a second M4 (±3%), methodology cross-audited by two other models. The harness is ~280 lines, on GitHub. (The reason RSS at 250K is *lower* than at 200K is pool reclaim, not measurement error; I hold three hypotheses and don't claim certainty on which.)

## An invitation — not a raise

I'm not raising. I'm inviting. If you have RTL / FPGA-bring-up experience, 28nm floorplanning / DFM background, ReRAM characterization access, DeepSeek-deployment war stories, or capital instincts *without* needing control ($110K–$210K for first MPW, equity-light, 10-year horizon) — reach me through the public channel first:

- **GitHub:** `michaelhuo2030/millisecond-era` (a public issue or PR is the first filter).

The first chip prototype is already spoken for — it goes to @antirez. Beyond that, there are 99 partner slots, not Seed slots.

## Acknowledgment

This project would not exist without **Salvatore Sanfilippo ([@antirez](https://github.com/antirez))**. His [`ds4-server`](https://github.com/antirez/ds4) made it possible to run DeepSeek V4-Flash on a 128 GB MacBook. Without it, a thesis I'd held for 22 months would never have become empirically falsifiable. The night his code ran on my laptop was the first night anyone else could reproduce what I believed. **When the first chip prototype ships, the very first unit goes to him.**

*— Written in the changing-world frame. Corrections welcome; I publish my own.*
