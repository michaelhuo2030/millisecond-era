# GROUNDING — energy/MAC and TOPS/W (the efficiency story, system-level not peak)

**Target:** energy per MAC (fJ) and system-level TOPS/W. **Why load-bearing:** sets the power-bound decode (the honest
operating tok/s) and the efficiency claim (CORE ~12–15 TOPS/W; SYSTEM ~6–11 ≈ **~2–4× H100** — the old "~5–10×" was
the core number mislabeled as system).

---

## R3 boundary guard
Report **system-level** TOPS/W, NOT the analog-macro **PEAK** (28–195 TOPS/W bit-normalized = ⚫ SUPERSEDED for the
system claim). Peak is a circuit datum; the system carries periphery, glue, KV-SRAM, I/O.

## Leg A — first principles (per-VMM energy → energy/MAC)
```
e_read     = (n_lrs·I_LRS + n_hrs·I_HRS) · vdd_int · t_int     # analog MAC current
e_capclick = n_click · 0.5 · C_int · V_ref²                    # integration-cap reset
e_digital  = n_click · (E_comp + E_cnt)                        # comparator + counter
energy_per_mac = (e_read + (N_cols/2)·e_capclick + (N_cols/2)·e_digital) / (N_rows · N_cols)
```
> **⚠️ codex catch (engine fix):** e_capclick/e_digital are PER-COLUMN (one cap/comparator/counter per 2 columns), so
> they must be multiplied by the column count (N_cols/2) before dividing by MACs/VMM (= N_rows·N_cols). The earlier
> "÷ MACs per VMM" with single-column periphery under-counted readout energy → made energy_per_mac too low. Fixed above;
> instantiate in `05-engine.py`.

Constants: I_LRS 5 µA / I_HRS 0.067 µA, V_ref 1.2 V (SPIKA §3.2.5 scheme), vdd_int 0.8–1.2 V, t_int 10–30 ns,
C_int 30–300 fF, n_click 5–15, E_comp 20 fJ, E_cnt 5 fJ, ACTIVE ~1/3 (ternary ~2/3 zeros).
→ **15–80 fJ/MAC** (low–high) → macro-only **25–133 TOPS/W** (Path-A CEILING, NOT a floor — codex). **Conversion
(make it explicit):** TOPS/W = 2 ops/MAC ÷ E_MAC, so **100 fJ/MAC ↔ 20 TOPS/W**, 15 fJ ↔ 133, 80 fJ ↔ 25.
**Lever: E = f(V_periph², 1/R_LRS)** — PERIPH_SHARE ~0.83, V_periph 0.9→0.6 V roughly halves energy (V²); higher R_LRS
(TaOx) cuts read current.

## Leg B — ≥2 anchors (one MEASURED-ours, one published)

| anchor | what | value | role |
|---|---|---|---|
| **OUR FPGA report_power** (`POWER-REPORT-RESULTS-2026-06-15`) | digital-ternary datapath, P=512@100MHz | **0.35 TOPS/W measured** → ×(7–14× ASIC gain) = **2.4–4.9 TOPS/W floor** | 🟢 Path-B (conservative, structurally independent of CIM lit) |
| **NTHU ISSCC'21** (full-precision honest end, not 195 peak) | 28nm ReRAM-CIM | **11.9–15 TOPS/W** | 🟢 Path-C published |

## Reconciliation — the three paths bound it (CORRECTED after panel #4 + codex re-review)
- Path A (per-MAC, macro-only) = **CEILING**: 25–133 TOPS/W (= 15–80 fJ; our optimistic "100 fJ nominal" sits at the
  low-efficiency end of this, **≈ 20 TOPS/W**).
- Path B (FPGA digital controller × assumed 7–14× ASIC gain) = floor: 2.4–4.9 TOPS/W (the gain factor is assumed).
- Path C (published 28nm, MACRO-level): 11.9–15 TOPS/W — this is the realistic CORE point (published macros carry real
  periphery, ≈130–170 fJ/MAC effective, so LOWER than our optimistic 100 fJ → 20). **Note (codex): the 15–80 fJ Leg-A
  and the 100 fJ "nominal" must be reconciled — 100 fJ → 20 TOPS/W, NOT 12–15; the 12–15 comes from Path C, not from
  100 fJ. The energy↔TOPS/W chain here is still loose and gets a clean rebuild in `05-engine.py`.**

> **⚠️ Panel #4 catch (codex + minimax + glm ALL converged) — I was optimistic-drifting (R0).** 12–15 TOPS/W is a
> **CORE/MACRO number, not system-level.** All three paths measure macro-or-partial energy, then silently promote
> macro→system. Bare 100 fJ/MAC excludes control, clocking, SFU/nonlinear, KV-SRAM, I/O, inter-die activation
> movement, weight-load (amortized OK). **BUT** the panel's "3–5× worse" assumes a standard **8-bit DAC (200–500 fJ)
> + SAR-ADC (100–300 fJ)** — the *exact* overheads our **ADC-free counting + DPC time-domain input** scheme avoids.
> So the penalty is real but smaller than a conventional analog-CIM design.
>
> **Honest split:**
> - **CORE/macro-level ≈ 12–15 TOPS/W** — 🟡 MODELED (Path C anchored). Our Leg-A 100 fJ already includes
>   comparator+counter+cap (the no-ADC readout), so it's core+readout, NOT bare array.
> - **TRUE SYSTEM-level ≈ 6–11 TOPS/W** (core × ~1.3–2.5 residual overhead: control/SFU/KV-SRAM/IO/inter-die; less
>   than the standard 3–5× because we skip the big ADC/DAC) **= ~2–4× H100** (INT8 ~2.8 TOPS/W) — 🟡/🔴 (the exact
>   factor is an end-to-end-measurement **GAP**).
> - **Headline correction: "~5–10× H100" was the CORE number mislabeled. System-level is "~2–4× H100", pending an
>   end-to-end measurement.** The efficiency edge is real, just smaller than the old headline.

## R2a correlation + R2c variance
Path B (our FPGA, digital) and Path C (CIM lit, analog) are **structurally independent legs** (different paradigm,
different measurement) — they bracket the answer rather than pseudo-replicate, which is exactly the independence R2a
wants. Path A vs Path C spread (~133 vs ~15) is **explained**: Path A is macro-only PEAK (no periphery/glue/KV/IO);
Path C is a published **MACRO** number (codex: NOT "system-honest" — it still excludes SFU/KV-SRAM/IO/inter-die).
Mechanism + magnitude given → not 🔴 contested; the load-bearing CORE claim uses Path C, and SYSTEM is core minus
further overhead (below).

## Result
- **energy/MAC ≈ 100 fJ nominal** (core+no-ADC readout; lever 44–100 fJ via V²/R) — 🟡 MODELED.
- **CORE/macro TOPS/W ≈ 12–15** — 🟡 MODELED, Path-C-anchored.
- **SYSTEM-level TOPS/W ≈ 6–11 (~2–4× H100)** — 🟡/🔴 (residual overhead factor = end-to-end-measurement GAP).
- Power-bound decode (feeds t_vmm.md): 1B ≈ 5k@0.5W · 30k@3W · 150k@15W (this is the AGGREGATE energy ceiling).
- ⚫ SUPERSEDED: 28–195 TOPS/W analog peak as system; **"~5–10× H100" as the system claim (that was the core number)**.
- 🔴 GAP: per-block periphery POWER split + the core→system overhead factor — needs primary Table-5 + SPICE + end-to-end.

## Fleet verdict (panel #4 rs-1782357202 3/3 + codex re-review rs-1782362173)
Panel #4: 12–15 is core-not-system (folded — H100 multiple ~5–10× core → ~2–4× system). **codex re-review then caught
the residual looseness:** (a) Path A is a CEILING not a "floor"; (b) Path C is a MACRO number, not "system-honest";
(c) the 15–80 fJ Leg-A and 100 fJ nominal aren't reconciled (100 fJ → 20 TOPS/W, not 12–15); (d) **the ~1.3–2.5×
core→system factor is an ESTIMATE with no bottom-up residual-power split — so the "6–11 / ~2–4× H100" system number
inherits that unsupported step (mark 🟡-soft / 🔴 GAP, not a derived value)**; (e) per-VMM energy needs the column
multiplicity. Net: the *direction* (real but modest efficiency edge, core>system) holds; the **energy↔TOPS/W chain
is rebuilt cleanly in `05-engine.py`**, and until then the system TOPS/W is a soft estimate, not grounded.
