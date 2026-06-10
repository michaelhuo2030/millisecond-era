# Philosophy — withered technology, given away

*Why this chip is deliberately "boring," and why the methodology is open. Two design principles, stated plainly.*

---

## 1. Lateral thinking with withered technology — 枯れた技術の水平思考

Gunpei Yokoi, who led design at Nintendo, had a principle: **「枯れた技術の水平思考」— lateral thinking with seasoned (withered) technology.** Don't reach for the newest, most advanced part. Take a mature, cheap, well-understood technology and apply it sideways, brilliantly. The Game Boy beat the technically-superior Atari Lynx and Sega Game Gear — worse screen, no backlight — because it won on **battery life, price, durability, and games.** Mature tech + great design + ecosystem + cost control is the combination that actually *ships and wins* — not the best spec sheet.

**This chip takes that path at every fork:**

| Fork | The flashy option | What we chose | Why |
|---|---|---|---|
| ReRAM cell | analog multi-level (more bits/cell) | **2-state binary** | the easiest to read, most robust, *already mass-produced* eNVM ReRAM |
| Numeric format | high precision | **ternary {−1, 0, +1}** | the fault-tolerant, noise-tolerant regime — large margin |
| Readout | analog sensing + ADC | **digital counter, no ADC** | bit-exact, and it removes the ADC energy/area tax that the analog-CIM path is known for |
| Process node | bleeding edge | **mature 28nm** | proven, available, affordable |

**We carry technical redundancy on purpose.** We *could* chase analog MLC, more bits per cell, fancier readout, an advanced node — for a flashier spec sheet. We deliberately trade peak spec for four things: **control** (a small team can actually build it), **manufacturability** (existing process + vendor ReRAM), **robustness** (fault-tolerant ternary, a large noise margin), and **margin to spare** — not living on the knife-edge of every unverified knob.

The two failure modes that haunt this field are well known: **analog-precision / the ADC tax**, and **SRAM density**. We engineered *around both, by construction.* The redundancy isn't a limitation — **it's the reason this gets built.**

> We're not the team chasing the most advanced silicon and dying on yield. The aim is to be the **Nintendo of edge-AI memory chips** — seasoned technology, better design, bigger margin — so it actually ships, and wins on design and ecosystem, not spec-sheet bravado.

---

## 2. An enabling layer, given away

The intent is to **empower others (助力他人)** — and it's architecture, not a slogan.

**The evidence is already in this account:** the methodology, the laws registry, the corrections-published-in-public, the FPGA RTL, and the HDC software stack ([`hdc-neon`](https://github.com/michaelhuo2030/hdc-neon), [`hdc-wgsl`](https://michaelhuo2030.github.io/hdc-neon/)) are all open. The direction is a **chip-design path open enough that other small teams can *build*, not only *buy*.** And the business model is the same shape — **SoC-IP / design-partner**: make other hardware teams' dreams physically possible instead of competing with them.

**Why this is a moat, not charity.** Open methodology compounds credibility and pulls contributors. Partners who *own* the tools pull for you. The distribution channel *is* the community — wholehearted partners over passive capital. Empowerment is the moat; community is the distribution. *(This is a roadmap, not a finished toolchain — stated honestly.)*

> We don't build a walled garden. We build the layer that lets others build, and we give the method away.

---

## On honesty (the discipline both principles rest on)

This chip is a **thesis in progress** — Stage 0 FPGA today, first silicon an estimated 12–24 months out. Throughout this work, **measured** numbers (e.g. `hdc-neon` 89× over a numpy baseline; FPGA synthesis results) are labeled measured, and **projected** targets (on-chip 1–4k tok/s; the further ~100×) are labeled projected — never blurred. When an earlier version of the pitch was killed by its own benchmarks, the grave was published. Reputation compounds; honesty compounds faster.

<sub>合抱之木，生于毫末；九层之台，起于累土。 — 老子</sub>
