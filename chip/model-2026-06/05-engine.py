#!/usr/bin/env python3
"""
05-engine.py — parametric density-ARCHITECTURE model for the ternary ReRAM-CIM chip.
Reads ONLY the cleanroom-grounded numbers (04-LEDGER) as baseline; every factor is a knob.
Cascade: cell-area(Icc) -> bare density -> array(xeff) -> CORE(operating, measured-anchored)
         -> /2 differential -> per-die params(xCIM-frac, area) -> fab-yield -> dies-for-target
         -> package(assembly-yield, N+k redundancy) -> system; + effective-density (two senses).
All arithmetic explicit so it can be codex-verified line by line. No heavy compute.
"""
import math
from math import comb, exp, ceil, log2

# ---------- BASELINE knobs (from 04-LEDGER, graded) ----------
BASE = dict(
    # cell device (Block 1)
    Icc_uA=(12.0, 25.0),         # binary low-Icc target band (uA); drives FET width
    Ion_per_um=700.0,            # 28nm NMOS on-current uA/um (mid of 500-900)
    CPP_nm=117.0, MP_nm=90.0,    # 28nm contacted-poly / metal pitch
    cell_floor_um2=0.04,         # layout-grid floor (~k>=50 F2 @28nm)
    # density cascade (Block 3 / ledger)
    array_eff=(0.60, 0.70),      # row/col driver amortization
    core_op_Mb_mm2=(0.5, 1.6),   # OPERATING CIM-core (measured-anchored: SPIKA-low .. HYDAR-high)
    cells_per_weight=2,          # 2-cell differential
    # die / package
    CIM_frac=(0.55, 0.70),       # fraction of die that is CIM array (rest = control/IO/PDN/SFU)
    die_mm2=200.0,
    D0_per_cm2=0.10,             # 28nm defect density (SMIC-ish 0.10-0.15; TSMC 0.03-0.05)
    assembly_yield_per_die=0.985,# per-die place/bond yield
    interposer_overhead=0.25,    # packaged footprint = sum(die area) x (1+overhead) for organic 2.5D
    wafer_mm2=70685.0,           # 300mm wafer area (pi*150^2)
)

def cell_area_um2(Icc_uA, p=BASE):
    """First-principles selector-current-floored cell area (um2). Returns band over Icc band."""
    out=[]
    for icc in (Icc_uA if isinstance(Icc_uA,(tuple,list)) else (Icc_uA,)):
        W_fet_nm = icc / p["Ion_per_um"] * 1000.0      # um->nm: (uA / (uA/um)) = um, *1000 = nm
        length_nm = 3*p["CPP_nm"]
        width_nm  = W_fet_nm + 2*p["MP_nm"]
        a = max(length_nm*width_nm/1e6, p["cell_floor_um2"])  # nm^2 -> um^2
        out.append(a)
    return (min(out), max(out))

def ternary_wt_per_mm2(core_op):
    """core (Mb/mm2 = 1e6 cells/mm2) /2 cells-per-weight -> ternary weights/mm2."""
    return tuple(c*1e6/BASE["cells_per_weight"] for c in core_op)  # wt/mm2

def per_die_params(core_op, CIM_frac, die_mm2):
    wt = ternary_wt_per_mm2(core_op)  # wt/mm2 band
    lo = wt[0]*die_mm2*CIM_frac[0]
    hi = wt[1]*die_mm2*CIM_frac[1]
    return (lo, hi)

def fab_yield(die_mm2, D0):
    return exp(-D0 * die_mm2/100.0)     # Poisson; A in cm2

def good_dies_per_wafer(die_mm2, D0, p=BASE):
    gross = p["wafer_mm2"]/die_mm2 * 0.85   # 0.85 edge/packing util
    return gross * fab_yield(die_mm2, D0)

def package_func_yield(N_need, k_spare, assembly_y, fab_y):
    """Fab N_need+k dies, each must be fab-good AND assembled-good; need >=N_need functional.
       per-die functional prob = fab_y*assembly_y; spares remap k failures."""
    Ntot=N_need+k_spare; pf=fab_y*assembly_y; tot=0.0
    for i in range(N_need, Ntot+1):
        tot += comb(Ntot,i)*pf**i*(1-pf)**(Ntot-i)
    return tot

def report():
    p=BASE
    print("="*78); print("BASELINE self-AUDIT (must reproduce 04-LEDGER)"); print("="*78)
    cell=cell_area_um2(p["Icc_uA"]); print(f"cell area @Icc {p['Icc_uA']}uA = {cell[0]:.3f}-{cell[1]:.3f} um2  (FET width {p['Icc_uA'][0]/p['Ion_per_um']*1000:.0f}-{p['Icc_uA'][1]/p['Ion_per_um']*1000:.0f} nm)")
    print(f"  bare storage ceiling 1/cell = {1/cell[1]:.1f}-{1/cell[0]:.1f} Mb/mm2")
    wt=ternary_wt_per_mm2(p["core_op_Mb_mm2"]); print(f"core(op) {p['core_op_Mb_mm2']} Mb/mm2 -> ternary {wt[0]/1e6:.2f}-{wt[1]/1e6:.2f} M wt/mm2")
    pd=per_die_params(p["core_op_Mb_mm2"],p["CIM_frac"],p["die_mm2"]); print(f"per GOOD die (200mm2, CIM {p['CIM_frac']}): {pd[0]/1e6:.0f}-{pd[1]/1e6:.0f} M params   [LEDGER: 27-112M]")
    n_lo=1000e6/pd[1]; n_hi=1000e6/pd[0]; print(f"1B dense dies = {n_lo:.1f}-{n_hi:.1f}   [LEDGER: 9-37]")
    print(f"AUDIT: {'PASS' if 26<pd[0]/1e6<29 and 110<pd[1]/1e6<114 else 'FAIL'}")

    print("\n"+"="*78); print("L4 DIE-SIZE 50/100/200 mm2 (correct arithmetic; redundancy sized to 92% target)"); print("="*78)
    core_pt=(1.0,1.0); cim=(0.65,0.65)  # mid operating point for clean comparison
    dens_pt = ternary_wt_per_mm2(core_pt)[0]*cim[0]/1e6   # M wt/mm2 of CIM die (=0.325M)
    print(f"{'die':>5} {'fabY':>6} {'perdie':>7} {'Nneed':>6} {'spares_k':>8} {'totdies':>8} {'waferEff':>9} {'pkgDens':>8} {'finalY':>7}")
    for A in (50,100,200):
        Y=fab_yield(A,p["D0_per_cm2"]); pdp=per_die_params(core_pt,cim,A)[0]; N=ceil(1000e6/pdp)
        pf=Y*p["assembly_yield_per_die"]
        k=0  # min spares for P(>=N of N+k) >= 0.92
        while package_func_yield(N,k,p["assembly_yield_per_die"],Y) < 0.92 and k<N+20: k+=1
        tot=N+k
        wafer_eff = Y*dens_pt                                  # M good-params / mm2 FABBED silicon
        pkg_area = tot*A*(1+p["interposer_overhead"]); pkg_dens=1000e6/pkg_area/1e6  # M params / mm2 PACKAGED
        finalY = package_func_yield(N,k,p["assembly_yield_per_die"],Y)*0.904         # +KGD/test discount
        print(f"{A:>5} {Y*100:>5.1f}% {pdp/1e6:>6.1f}M {N:>6} {k:>8} {tot:>8} {wafer_eff:>8.3f}M {pkg_dens:>7.3f}M {finalY*100:>6.1f}%")
    print("waferEff = good params / mm2 FABBED Si (=fabY x density) -> FAVORS small dies (less waste): 50mm2 ~+16% vs 200.")
    print("pkgDens  = 1B / packaged area incl interposer -> ~CONSTANT (overhead is a fixed fraction): cutting != denser package.")
    print("spares_k = extra dies to hit 92% functional yield -> small dies need MORE spares (more assembly), the real cost.")
    print(f"SANITY: 0.985^50={0.985**50*100:.1f}% (NOT 7.8%); 0.985^20={0.985**20*100:.1f}%; 0.985^9={0.985**9*100:.1f}%")

    print("\n"+"="*78); print("L1 ARRAY-EFF & L2 CIM-FRAC (disaggregation) levers @200mm2"); print("="*78)
    print("L1 array-eff 0.60->0.75: bare-density gain only; core(op) is measured-anchored so unchanged unless a domestic ReRAM fab confirms product amortization.")
    for cf in (0.55,0.65,0.75,0.90):
        pdp=per_die_params((1.0,1.0),(cf,cf),200)[0]; N=ceil(1000e6/pdp)
        print(f"  CIM-frac {cf:.2f} (disaggregation: move SFU/KV/control off array die) -> per-die {pdp/1e6:.0f}M, 1B={N} dies")
    print("  CIM-frac 0.60->0.90 is the BIGGEST density lever (1.5x params/die); it's REAL (already partly in ADR).")

    print("\n"+"="*78); print("L6 — NODE LADDER 28->7nm for 0.1B (TWO-COMPONENT: array~node^1 + periphery~node^2)"); print("="*78)
    TGT=0.1e9                          # the credible EDGE target (0.1B ternary weights)
    CIMf=0.90                          # max disaggregation (control off-die)
    core28=(2.0,2.5)                   # realistic 28nm PRODUCT core band (panel rs-1782377887)
    # --- CORRECTED MODEL (panel rs-1782379474, codex+kimi+minimax+glm 4/4): my earlier flat node^1 was TOO PESSIMISTIC.
    #   macro = ARRAY + PERIPHERY. ARRAY (1T1R, MV access-FET length voltage-floored) scales ~node^1 -> 28->7 ~2.75x.
    #   PERIPHERY (per-2-col counters+comparators = core LOGIC) scales ~node^2, REALISTICALLY ~5.75x 28->7 (= real TSMC
    #   28->N7 logic density, NOT ideal 16x: pitch-matched BL/PDN/MV-spacing lag). Our macro is READOUT-LIMITED so the
    #   periphery fraction f@28nm is HIGH (~0.6-0.85, prior panel: counter+comparator many-x the array) -> node shrink
    #   RELIEVES the dominant bottleneck -> blended uplift 28->7 ~= 4-5x (NOT node^1 ~3x).
    A_exp=0.73                         # array area ∝ r^0.73 (28->7 -> 2.75x);  P_exp -> periphery area ∝ r^1.26 (28->7 -> 5.75x)
    P_exp=1.26
    F28=(0.60,0.85)                    # periphery area fraction @28nm (readout-limited macro), band
    def uplift(node, f):
        r=node/28.0
        return 1.0/((1-f)*r**A_exp + f*r**P_exp)
    wafer_k={28:(3.0,3.5), 22:(4.3,5.6), 16:(6.0,9.0), 14:(7.0,10.0), 12:(9.0,13.0), 10:(11.0,15.0), 7:(14.0,19.0)}
    eReRAM={28:"mature/multi-fdy", 22:"available", 16:"rare(FinFET)", 14:"rare(FinFET)", 12:"bleeding-edge", 10:"~none-comm", 7:"~none-comm"}
    def die_band(node):
        # smallest die: high density end (core_hi, f_hi -> max uplift); largest: low end
        d_lo=TGT/(core28[1]*uplift(node,F28[1])*1e6/BASE["cells_per_weight"]*CIMf)
        d_hi=TGT/(core28[0]*uplift(node,F28[0])*1e6/BASE["cells_per_weight"]*CIMf)
        return (d_lo,d_hi)
    def klass1(A):
        if A<5: return "wearable(<5)"
        if A<25: return "phone-cmpn(5-25)"
        if A<100: return "edge MOD(25-100)"
        return "CARD(>100)"
    def klass(b):
        lo,hi=klass1(b[0]),klass1(b[1]); return lo if lo==hi else f"{lo}..{hi}(STRADDLE)"
    print(f"{'node':>5} {'uplift/28':>10} {'0.1B die mm2':>13} {'good/wfr':>9} {'$/good die':>11} {'eReRAM':>16}  class")
    for node in (28,22,16,14,12,10,7):
        ub=(uplift(node,F28[0]),uplift(node,F28[1])); A=die_band(node); Amid=(A[0]+A[1])/2
        Y=fab_yield(Amid,BASE["D0_per_cm2"]); good=BASE["wafer_mm2"]/Amid*0.80*Y
        wc=wafer_k[node]; cpd=(wc[0]*1000/good, wc[1]*1000/good)
        print(f"{node:>4}n {ub[0]:>4.1f}-{ub[1]:<4.1f}x {A[0]:>6.0f}-{A[1]:<5.0f} {good:>8.0f} ${cpd[0]:>4.1f}-{cpd[1]:<5.1f} {eReRAM[node]:>16}  {klass(A)}")
    print("READING (0.1B, CIM-frac 0.90, f@28nm=periphery fraction 0.60-0.85):")
    print(" - CORRECTION: node shrink helps MORE than node^1, because it RELIEVES the readout periphery (logic, ~node^2) that")
    print("   dominates our macro. Blended 28->7 ~= 4-5x (panel 4/4), not ~3x. (My earlier flat-node^1 ladder was too pessimistic.)")
    print(" - 22nm (realistic frontier): 0.1B ~67-86mm2, edge-MODULE. 14nm (stretch): ~40-55mm2, MODULE but notably smaller.")
    print(" - GEOMETRICALLY a smaller class IS reachable: ~10nm -> ~27-39mm2 (module edge); 7nm -> ~18-28mm2 (phone-companion).")
    print("   So 'node never unlocks a smaller class' was WRONG. BUT it's gated by eReRAM ACCESS, not geometry:")
    print(" - eReRAM access: mature 28/22, rare 16/14 (FinFET), ~none commercial <=10nm. => PRACTICALLY capped at 22nm / 14nm-stretch;")
    print("   the geometric <=10nm path to phone-companion is NOT buildable for us today. $/die also RISES at advanced nodes.")
    print(" - DEEPER LEVER: since the readout DOMINATES, shrinking/sharing the readout at a FIXED node is the SAME knob as node")
    print("   shrink (reduce periphery fraction) -> a readout redesign is an independent density lever, possibly > a node step.")
    print(" - The other sub-25mm2 unlock independent of node/readout: a smaller/task model, or 1S1R (removes the access-FET floor).")

# =====================================================================================
# L7 — THROUGHPUT & RESPONSE CYCLE, 0.1B..3B  (ledger §3; paradigm-native weight-stationary)
# Core: per-token latency = Σ_layers[ Σ weight-matmuls + attention + glue ]  (sequential depth).
#   timing-ceiling tok/s = 1/per_token_latency  (optimistic = parallel rowtile + all-cols-parallel readout)
#   energy/token         = N_params · E/MAC      (each resident weight used once per token)
#   power-bound tok/s    = W / energy_per_token
#   OPERATING rate(W)    = min(timing-ceiling, power-bound)  <- BOTH prefill & decode (single-stream) run here
#   响应周期 cycle = TTFT(prefill @rate + attn O(ctx^2)) + n_gen/rate ;  响应频率 Hz = 1/cycle
# All knobs explicit so codex/panel can audit line-by-line. The rowtile/col readout-parallelism is the
# named #1 ~10x GAP: here the ceiling uses the PARALLEL (optimistic) end; the power gate then caps it.
# =====================================================================================
MODELS = {  # real public configs [LOCKED]; N = ternary weights (≈ params)
  "0.1B": dict(L=12, d=768,  dff=3072, nh=12, nkv=12, hd=64,  N=1.0e8),  # GPT2-small-ish
  "0.3B": dict(L=24, d=1024, dff=4096, nh=16, nkv=16, hd=64,  N=3.0e8),  # GPT2-medium-ish
  "0.5B": dict(L=24, d=896,  dff=4864, nh=14, nkv=2,  hd=64,  N=5.0e8),  # Qwen2-0.5B
  "1B":   dict(L=16, d=2048, dff=8192, nh=32, nkv=8,  hd=64,  N=1.0e9),  # Llama-3.2-1B
  "1.5B": dict(L=28, d=1536, dff=8960, nh=12, nkv=2,  hd=128, N=1.5e9),  # Qwen2-1.5B
  "3B":   dict(L=28, d=3072, dff=8192, nh=24, nkv=8,  hd=128, N=3.0e9),  # Llama-3.2-3B
}
ROWS, COLS = 256, 512          # ledger §3: IR-drop row limit / outputs per array
E_MAC = 100e-15                # ledger §4: J/MAC nominal (lever 44-100 fJ via V², 1/R)
# t = (t_vmm, t_glue_per_layer, t_add)  — ledger §3 cohort 5-18 ns; glue per-LAYER not per-VMM
TSCN = {"ideal":(5e-9,5e-9,0.5e-9), "realistic":(10e-9,15e-9,1.0e-9), "conservative":(18e-9,30e-9,2.0e-9)}

def _matmuls(m):
    d,dff,nh,nkv,hd = m["d"],m["dff"],m["nh"],m["nkv"],m["hd"]
    return [("Q",d,nh*hd),("K",d,nkv*hd),("V",d,nkv*hd),("O",nh*hd,d),
            ("gate",d,dff),("up",d,dff),("down",dff,d)]
def _matmul_lat(c, o, t_vmm, t_add):
    """PARALLEL rowtile (resident macros fire together)+add-tree; cols all-parallel (optimistic readout)."""
    rt = ceil(c/ROWS)
    addtree = ceil(log2(rt)) if rt>1 else 0
    return t_vmm + addtree*t_add          # 1 VMM wave (cols parallel) + log2(row_tiles) adds
def _attn_lat(m, ctx, t_vmm, t_add):      # decode-step attention over ctx KV (KV-dependent, not weight)
    qk = _matmul_lat(ctx, m["nh"]*m["hd"], t_vmm, t_add)
    av = _matmul_lat(ctx, m["nh"]*m["hd"], t_vmm, t_add)
    return qk + av + t_vmm                 # +softmax/glue ~1 VMM
def per_token_latency(m, ctx, scn):
    t_vmm,t_glue,t_add = TSCN[scn]
    per_layer = sum(_matmul_lat(c,o,t_vmm,t_add) for _,c,o in _matmuls(m))
    per_layer += _attn_lat(m, ctx, t_vmm, t_add) + t_glue
    return per_layer * m["L"]
def timing_ceiling(m, ctx, scn):  return 1.0/per_token_latency(m, ctx, scn)
def energy_per_token(m):          return m["N"]*E_MAC
def power_bound(m, watts):        return watts/energy_per_token(m)
def operating(m, ctx, scn, watts):
    tc=timing_ceiling(m,ctx,scn); pb=power_bound(m,watts)
    return (min(tc,pb), "power" if pb<tc else "timing")
def ttft(m, ctx, scn, watts):
    """Prefill: ctx tokens at the operating rate + causal attention O(ctx^2)."""
    rate,_ = operating(m, ctx, scn, watts); t_vmm = TSCN[scn][0]
    t_attn = (ctx*ctx/(2*ROWS))*m["L"]*t_vmm
    return ctx/rate + t_attn
def response_cycle(m, ctx, gen, scn, watts):
    rate,_ = operating(m, ctx+gen//2, scn, watts)
    return ttft(m,ctx,scn,watts) + (gen/rate if gen else 0.0)
def response_hz(m, ctx, gen, scn, watts):
    c=response_cycle(m,ctx,gen,scn,watts); return 1.0/c if c>0 else float("inf")

def _f(x):
    if x>=1e6: return f"{x/1e6:.2f}M"
    if x>=1e3: return f"{x/1e3:.1f}k"
    if x>=1:   return f"{x:.0f}"
    return f"{x:.2f}"
def _ft(s):
    if s>=1:    return f"{s:.2f}s"
    if s>=1e-3: return f"{s*1e3:.1f}ms"
    return f"{s*1e6:.0f}us"

def throughput_report():
    print("\n"+"="*86); print("L7 — THROUGHPUT & RESPONSE CYCLE 0.1B..3B (single-stream/edge; ledger §3)"); print("="*86)
    print("paradigm-native weight-stationary: speed=1/(seq-depth·t_vmm) capped by power; cycle=TTFT+gen/rate.")
    print("ceiling = realistic t_vmm 10ns, PARALLEL rowtile (optimistic readout, the #1 ~10x GAP). ctx_avg=512.")

    print("\n[A] DECODE tok/s = min(timing-ceiling, power-bound) — single user")
    print(f"  {'model':>6} {'energy/tok':>11} {'timing-ceil':>12} {'@0.5W':>11} {'@3W':>11} {'@15W':>11} {'@50W(box)':>12}")
    for nm,m in MODELS.items():
        tc=timing_ceiling(m,512,"realistic"); row=f"  {nm:>6} {_f(energy_per_token(m)*1e6)+'uJ':>11} {_f(tc):>12}"
        for w in (0.5,3,15,50):
            op,b=operating(m,512,"realistic",w); row+=f"{_f(op)+'('+b[0]+')':>11}" if w<50 else f"{_f(op)+'('+b[0]+')':>12}"
        print(row)
    print("  edge sub-W..few-W = POWER-bound(p). Flip to TIMING(t) only above W*=ceiling x E/tok (glm panel catch):")
    print("    0.1B ~6W, 0.3B ~9W, 0.5B ~16W, 1.5B ~38W, 1B ~45W, 3B ~74W -> SMALL models reach timing in a box;")
    print("    >=1B stay POWER-bound through tens of W. human read ~10-50 tok/s (every cell >> that).")
    print("  NOTE (codex): energy/tok = N x E_MAC is the WEIGHT-MAC term (dominant) = optimistic FLOOR; full token")
    print("  energy adds attention-KV/softmax/LN/control -> real edge tok/s ~1.3-2x LOWER (ledger §4 system overhead).")
    print("  band: ideal t_vmm 5ns ~2x ceiling, conservative 18ns ~0.5x; SERIAL rowtile ~10x slower (readout GAP).")

    print("\n[B] RESPONSE CYCLE 响应周期 + 频率 Hz (思考心跳) — edge @3W vs box(timing-ceiling)")
    print(f"  {'model':>6} {'scenario':>10} {'ctx':>5} {'gen':>4} | {'TTFT@3W':>8} {'cycle@3W':>9} {'Hz@3W':>7} | {'cyc-ceil':>8} {'Hz-ceil':>8}")
    SCN=[("short-qa",256,64),("mid-chat",1024,256),("long-scan",4096,0)]
    for nm in ("0.1B","1B","3B"):
        m=MODELS[nm]
        for s,ctx,gen in SCN:
            c3=response_cycle(m,ctx,gen,"realistic",3.0); h3=response_hz(m,ctx,gen,"realistic",3.0)
            cc=response_cycle(m,ctx,gen,"realistic",1e6); hc=response_hz(m,ctx,gen,"realistic",1e6)  # 1MW => timing ceiling
            print(f"  {nm:>6} {s:>10} {ctx:>5} {gen:>4} | {_ft(ttft(m,ctx,'realistic',3.0)):>8} {_ft(c3):>9} {h3:>6.0f} | {_ft(cc):>8} {hc:>7.0f}")
    print("  @3W = honest edge heartbeat (power-bound, big models slow); ceil = box/datacenter (timing-bound).")

    print("\n[C] SELF-AUDIT")
    chk=[]
    chk.append(("smaller faster (0.1B>3B timing)", timing_ceiling(MODELS['0.1B'],512,'realistic')>timing_ceiling(MODELS['3B'],512,'realistic')))
    chk.append(("1B@3W matches ledger ~30k", 25e3<operating(MODELS['1B'],512,'realistic',3.0)[0]<35e3))
    chk.append(("1B@0.5W matches ledger ~5k", 4e3<operating(MODELS['1B'],512,'realistic',0.5)[0]<6e3))
    chk.append(("small model few-W = timing-bound", operating(MODELS['0.1B'],512,'realistic',15)[1]=="timing"))
    chk.append(("big model few-W = power-bound", operating(MODELS['3B'],512,'realistic',3.0)[1]=="power"))
    chk.append(("TTFT grows with ctx (O(ctx^2))", ttft(MODELS['1B'],4096,'realistic',3.0)>ttft(MODELS['1B'],256,'realistic',3.0)))
    chk.append(("edge cycle slower than box ceiling", response_cycle(MODELS['3B'],1024,256,'realistic',3.0)>response_cycle(MODELS['3B'],1024,256,'realistic',1e6)))
    for nm,ok in chk: print(f"  [{'OK' if ok else 'FLAG'}] {nm}")
    print("  conservatism noted: ceiling SUMS all 7 matmuls sequentially though QKV & gate/up are physically")
    print("  parallel (true seq-depth ~4/layer) -> ceiling ~1.5-2x pessimistic; but EDGE point is power-bound so")
    print("  the product number is unaffected. GAPs: t_vmm(SPICE), rowtile readout-parallelism(#1 ~10x), prefill attn impl.")

if __name__=="__main__":
    report()
    throughput_report()
