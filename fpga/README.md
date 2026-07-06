# fpga — multiplier-free ternary MAC, measured on real fabric

This is the **measured FPGA proof** under millisecond-era's speed thesis: a SPIKA-style ternary {−1, 0, +1} multiply-accumulate array, synthesized on a real **Zynq-7010 (EBAZ4205, ~¥150 board)** in Vivado 2023.2 (`xc7z010clg400-1`).

> **2026-07 C1 framing:** FPGA evidence proves the multiplier-free ternary datapath and tiny C0 loops. It does **not**
> prove the ReRAM-CIM ASIC SKU. Current public C1 starts at 0.1B / 0.3B / 1B / bounded 3B; older 1B/4B ASIC
> projections here are historical anchors, not buyer promises.

## Measured (the honest floor)
- **0 DSPs** — multiplier-free by construction (ternary weights ⇒ add/subtract only).
- **Fmax 194–266 MHz** on the tiny 17.6k-LUT xc7z010 (−1 speed grade); ~84% of the critical path is *routing* delay → a 28nm ASIC clocks far higher (600 MHz–1 GHz assumption holds).
- **P = 512** lanes fit the fabric (75.5% LUT @ P=512); sweep reports for P=64…4096 in `reports/`.
- **II = 1.0, ~99.5% datapath utilization** (cycle-accurate throughput testbench).

## Honestly owed (not faked)
Sustained **batch-1 utilization on the physical board** and **absolute tok/s** need the board flashed with the full feed path — left **OWED, not faked**. Read these as the *smallest credible anchor* (an EBAZ-fabric floor), **not** the product number. The **1–4k tok/s is the ASIC projection** (see [`../chip/ADR-v1-architecture.md`](../chip/ADR-v1-architecture.md)); these reports are the *measured* end of the measured-vs-projected line.

## Layout
- `rtl/` — `ternary_mac_array.v` + `ternary_mac_top.v` (the array + top wrapper)
- `sim/` — functional + throughput testbenches
- `reports/` — **real Vivado timing + utilization reports** (P64…P4096) — the receipts
- `RESULTS.md` · `THROUGHPUT-UTIL-2026-06-09.md` · `COUNTER-WIDTH-VERIFICATION-CHECKLIST.md` — the measured writeups, boundaries stated
- `build_sweep.tcl` · `tok_s.py` — the build sweep + throughput calc

*This is what "MEASURED, not projected" looks like in hardware — the proof, with its own boundary stated.*
