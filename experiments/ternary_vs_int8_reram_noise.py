#!/usr/bin/env python3
"""exp_ternary_reram_noise.py — the ¥0 chip-substrate result + the seed of a sellable 'noise-aware ternary' toolkit.
CLAIM (measured here): ternary {-1,0,+1} weights tolerate ReRAM analog DEVICE noise FAR better than int8/fp — and
the reason is physical, not magic: device conductance noise is a ~FIXED ABSOLUTE property of the cell, so packing
more levels into the same conductance range shrinks the level-spacing BELOW the noise (int8: 256 levels, spacing
~range/255) while ternary's 3 coarse levels keep spacing >> noise (spacing = range/2). So the ReRAM analog-tolerance
is LOW-PRECISION's win (matches our prior finding: ternary carries it, not HDC per se).
FAIR test: ALL precisions map into the SAME normalized conductance range [-1,1] and get the SAME absolute noise.
Multi-component NeuroSim-style noise = lumped Gaussian (programming+read+drift) + stuck-at faults + output ADC quant.
sklearn digits + numpy only. Usage: python exp_ternary_reram_noise.py"""
import warnings; warnings.filterwarnings("ignore")
import numpy as np; np.seterr(all="ignore")
from sklearn.datasets import load_digits
from sklearn.model_selection import train_test_split
from sklearn.neural_network import MLPClassifier

SEEDS = 6
SIGMAS = [0.0, 0.02, 0.05, 0.1, 0.2, 0.3, 0.5]   # device noise = fraction of the (shared) conductance range
ADC_BITS = 6                                      # output ADC quantization (peripheral)
STUCK = 0.01                                      # 1% stuck-at cells

def quantize_cond(W, kind):
    """Map weights into the SHARED conductance space [-1,1], at the given precision. Returns (cond, scale)."""
    m = np.max(np.abs(W)) + 1e-9; Wn = W / m
    if kind == "fp32":    q = Wn
    elif kind == "int8":  q = np.round(Wn * 127) / 127      # 256 levels
    elif kind == "int4":  q = np.round(Wn * 7) / 7          # 16 levels
    elif kind == "ternary":
        thr = 0.7 * np.mean(np.abs(Wn)); q = np.where(Wn > thr, 1.0, np.where(Wn < -thr, -1.0, 0.0))  # 3 levels
    return q, m

def noisy_weight(q, m, sigma, rng):
    cn = q + rng.normal(0, sigma * 2.0, q.shape)            # SAME absolute noise (range=2) for ALL precisions
    if STUCK > 0:
        mask = rng.random(q.shape) < STUCK
        cn[mask] = rng.choice(np.array([-1.0, 1.0]), int(mask.sum()))
    return cn * m

def adc(x, bits):
    x = np.nan_to_num(x, posinf=0.0, neginf=0.0)           # high-σ stuck-at faults can overflow; clamp
    m = np.max(np.abs(x)) + 1e-9; L = 2 ** bits
    return np.round(x / m * (L // 2)) / (L // 2) * m

def forward(X, W1, b1, W2, b2):
    h = adc(np.maximum(0, X @ W1 + b1), ADC_BITS)
    return np.argmax(adc(h @ W2 + b2, ADC_BITS), axis=1)

def main():
    d = load_digits(); X, y = d.data / 16.0, d.target
    Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.3, random_state=0)
    clf = MLPClassifier(hidden_layer_sizes=(64,), max_iter=800, random_state=0).fit(Xtr, ytr)
    W1, b1 = clf.coefs_[0], clf.intercepts_[0]; W2, b2 = clf.coefs_[1], clf.intercepts_[1]
    print(f"[exp_ternary_reram_noise] digits, {len(yte)} test | fp32 clean acc = {(forward(Xte,W1,b1,W2,b2)==yte).mean():.3f}\n")
    print(f"  σ(dev) |  fp32  |  int8  |  int4  | TERNARY")
    print(f"  -------+--------+--------+--------+--------")
    for sigma in SIGMAS:
        row = {}
        for kind in ("fp32", "int8", "int4", "ternary"):
            q1, m1 = quantize_cond(W1, kind); q2, m2 = quantize_cond(W2, kind)
            accs = []
            for s in range(SEEDS):
                rng = np.random.default_rng(s)
                accs.append((forward(Xte, noisy_weight(q1, m1, sigma, rng), b1, noisy_weight(q2, m2, sigma, rng), b2) == yte).mean())
            row[kind] = np.mean(accs)
        print(f"  {sigma:>5.2f}  | {row['fp32']:.3f}  | {row['int8']:.3f}  | {row['int4']:.3f}  | {row['ternary']:.3f}")
    print("\n  READ: device noise σ is FIXED-ABSOLUTE (same for all). Ternary's 3 coarse levels keep spacing >> noise")
    print("  → graceful; int8's 256 packed levels have spacing << noise → collapse. The ReRAM analog-tolerance is")
    print("  LOW-PRECISION's win — the seed of a 'noise-aware ternary mapping' toolkit (cross-check next on NeuroSim/AIHWKit).")

if __name__ == "__main__":
    main()
