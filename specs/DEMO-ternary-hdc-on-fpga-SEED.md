# FPGA Demo — ternary + toy-LLM + HDC on TALOS-V2 / EBAZ (Michael, 2026-05-30) · SEED

> Origin: Michael — "let's do FPGA simulations (like TALOS-V2) on ternary, using toy LLMs + HDC to
> demonstrate the power." The touchable hardware proof of the chip thesis — on a real ¥150 board,
> *before* the ASIC. Parallel to our software demo: this is the *silicon-side* feel-it demo.

## Why this is a strong demo (and cheap to do)
Both pillars of the thesis are **extremely FPGA-friendly** — no multipliers, no floating point:
- **Ternary {−1,0,+1} matmul = signed accumulation only** (add / subtract / skip-on-zero). A ternary MAC is a few LUTs, not a DSP multiplier → a tiny FPGA (EBAZ Zynq-7010) runs real layers.
- **HDC = bitwise XOR (bind) + popcount/majority (bundle) + Hamming/popcount (cleanup)** → the most FPGA-native compute there is (1-bit ops, massively parallel).
So a small board can genuinely show *both* — making the "1-bit / ternary energy" story **touchable**, not a slide.

## What to demonstrate (3 pieces, build incrementally)
1. **Ternary toy-LLM layer on FPGA** — a tiny ternary MLP / single transformer block (BitNet-nano scale)
   with {−1,0,+1} weights in RTL → correct outputs using *adders only*. Shows the energy/simplicity win
   (ternary MAC = no multiplier). Compare LUT/power vs an INT8 version on the same board.
2. **Ternary noise-tolerance, live (the E7 story on real hardware)** — inject bit/level perturbation and
   show ternary output stays correct where INT8 corrupts. The device-stability finding (`t1_reram_tolerance.py`:
   ternary 0% flips vs INT8 96.5% @σ=0.05) made *touchable* on real logic.
3. **HDC engine on FPGA** — bind/bundle/cleanup in RTL; run a tiny deterministic deterministic trace or
   item-memory recall (recall 1.0, bit-identical every run). Shows HDC's hardware-nativeness + determinism.
4. **(Stretch) the hybrid on hardware** — toy ternary-LLM extracts structure → HDC holds/traces it → the
   full "LLM discovers, HDC reasons" thesis running end-to-end on the board.

## Why it matters
- **Touchable de-risk** of the ASIC path: ternary + HDC proven on real reconfigurable silicon.
- **Founder-content credibility** (cf. the EBAZ Linux-boot post, but deeper): *"ternary LLM + HDC running on a ¥150 FPGA board."*
- Directly exercises the two de-risking decisions: **ternary cells** (E7 stability + gate-1 quality) and **HDC** (the reasoning substrate).

## Status & honest next steps
SEED. Builds on: **TALOS-V2** RTL (testbenches pass, but never synthesized to bitstream end-to-end —
elephant #1), the **EBAZ4205** board (boots Linux, `02-fpga-rtl/ebaz/`), the **vivado-vm** build server
(aux-mac headless Vivado), and the HDC ops (`hdc_ops`, bind/bundle/cleanup). To pick up: (1) get TALOS-V2
→ bitstream working (the open elephant); (2) write/borrow a ternary MAC + tiny-LLM-layer RTL; (3) HDC
bind/cleanup RTL; (4) the noise-injection demo; (5) capture as a post + a board video.

## ⚠️ CORRECTION (2026-05-30) — TALOS vs TALOS-V2 (I got this wrong, Michael was right)
The local `02-fpga-rtl/TALOS/` is the **old CNN** (MNIST digit classifier, INT8, 10 MHz) — no tokens.
I wrongly concluded "TALOS is just a CNN." **TALOS-V2 is a DIFFERENT thing: an RTL implementation of
Karpathy's microGPT (a real transformer/LLM), and it DOES measure ~53,000 tok/s on the DE1-SoC**
(github.com/Luthiraa/TALOS-V2, "running microgpt at 50k+ tkps"; custom 56.25 MHz PLL).
- **The catch that makes it consistent:** microGPT = **4,192 parameters** — tiny enough to fit *entirely
  on-chip* → no weight streaming → flies. (Confirms "fits on-chip → fast"; doesn't break it.) A benchmark
  even shows a single M4-Max CPU core runs the *same* model ~71× faster than the FPGA (AlexCheema/talos-vs-macbook)
  — i.e. for a 4k-param toy, even a CPU crushes the FPGA; the model's just trivially small.
- **Use it:** TALOS-V2 is a **forkable transformer-in-RTL base** for our demo — swap weights to ternary,
  bolt on HDC. Far better starting point than the CNN. **Lesson (mine): check the right version before concluding.**

## On-chip ternary capacity per FPGA tier (the "TALOS-V2 fast regime" = fully on-chip, no streaming)
Rule: **1 MB on-chip RAM (BRAM+URAM) ≈ 5M ternary params** (1 MB = 8 Mbit ÷ 1.6 bit). Reserve ~30% for HDC +
activations → usable ≈ **3.5M params/MB**. Speed stays *fast* (compute-bound, thousands–tens-of-thousands tok/s)
as long as the model fits on-chip, because the parallel ternary-MAC engine scales with the chip. *(estimates.)*

| board | FPGA | on-chip RAM (≈) | ternary params on-chip (fast) | vs microGPT (4,192) | anchor |
|---|---|---|---|---|---|
| DE1-SoC (TALOS-V2's board) | Cyclone V | ~0.5 MB | ~1.7M | ~400× | bigger microGPT |
| Ultra96-V2 | ZU3EG | ~0.95 MB | ~3M | ~700× | tiny char-LM |
| **Kria KV260** | ZU5EV | ~2.8 MB | **~10M** | ~2,400× | small char/word LM |
| ZCU104/106 | ZU7EV | ~4.75 MB | ~16M | ~3,800× | — |
| ZCU102 | ZU9EG | ~4 MB | ~14M | — | — |
| **Alveo U200/U250** | VU9P/13P | ~43–80 MB | **~150–280M** | ~36,000× | **GPT-2-small (124M) fully on-chip!** |
| Alveo U280 | VU37P | ~43 MB on-chip + 8GB HBM | ~150M on-chip; bigger in HBM (streams) | — | — |

HDC footprint is cheap (D=10k vector = 1.25 KB → 1,000-concept item-memory = ~1.25 MB) — on small boards it
shares the BRAM with the model; on Alveo there's plenty for both. **Headline: a ~¥5000 Alveo card, in ternary,
can hold a GPT-2-small-class (~124M) model ENTIRELY on-chip → fast (~10k–50k tok/s), with room for HDC.**

## Board shopping list (for 闲鱼 — ¥ = rough used 2026 price; verify on-site)
**够用首选 (demo + ≤8B 三值 in DDR / ≤10M on-chip):** Kria **KV260** (ZU5EV, 4GB, ¥1500–3000, ⭐), **Ultra96-V2**
(ZU3EG, 2GB, ¥800–1500), KR260. **更大逻辑:** **ZCU104** (ZU7EV, ¥3000–5000), **ZCU102** (ZU9EG, 4GB, ¥4000–8000).
**跑 30–70B 三值 (大内存 PCIe 卡, 需主机+Vitis):** Alveo **U50** (8GB HBM, ¥3000–6000), **U200/U250** (64GB DDR, ¥4000–12000),
**U280** (8GB HBM+32GB DDR, ¥6000–15000). 避坑: 认准 ZU…EG/EV 或 VU…P (别买成老 Zynq-7000); 电源/SD/风扇要齐.

Connections: ternary cell decision + E7 ([[project_reram_kb_base_and_dream_2026_05_30]]), HDC theory
([[project_hdc_fundamental_theory_2026_05_30]] — 1-bit ops, capacity=D), TALOS-V2 RTL (forkable base), EBAZ boot. → the
hardware twin of the our software demo.
