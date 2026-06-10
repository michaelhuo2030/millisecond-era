#!/usr/bin/env python3
"""
tok_s.py — implied decode tok/s from MEASURED FPGA bounds.

Formula (bit-verified in Method-2 RTL, see digital-speed-estimate/method2-rtl.md):
    tok/s = Fmax * P * util / (2 * N_params)

We plug in the EBAZ4205 (xc7z010) MEASURED Fmax + the max P that fits the
fabric. This is an FPGA-fabric FLOOR, not the product number: a real 28nm
ASIC has far more area (=> much larger P) and a higher clock (~600 MHz-1 GHz
vs ~200-270 MHz here). Reported as a conservative anchor.
"""

# --- MEASURED on xc7z010 (EBAZ4205), filled from synth reports ---
# (P, LUTs, FFs, fits?, Fmax_MHz)  -- Fmax from routed top-wrapper WNS
MEASURED = [
    # filled by the sweep; see reports/sweep_P*.log
]

def tok_s(fmax_hz, P, util, n_params):
    return fmax_hz * P * util / (2.0 * n_params)

def report(fmax_mhz, P, label):
    fmax = fmax_mhz * 1e6
    print(f"\n=== {label}: Fmax={fmax_mhz:.0f} MHz, P={P} ===")
    print(f"{'N_params':>10} | {'util=0.25':>12} | {'util=0.40':>12}")
    print("-" * 40)
    for n, nlab in [(1e9, "1B"), (4e9, "4B")]:
        t25 = tok_s(fmax, P, 0.25, n)
        t40 = tok_s(fmax, P, 0.40, n)
        print(f"{nlab:>10} | {t25:>12.1f} | {t40:>12.1f}")

if __name__ == "__main__":
    import sys
    # usage: tok_s.py <Fmax_MHz> <P>
    if len(sys.argv) == 3:
        report(float(sys.argv[1]), int(sys.argv[2]),
               f"EBAZ measured")
    else:
        print("usage: tok_s.py <Fmax_MHz> <P_max_that_fits>")
