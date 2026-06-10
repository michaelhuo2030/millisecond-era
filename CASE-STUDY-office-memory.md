# Case study — `office-memory`: what this chip is *for*

> **▶ Live demo (open it):** https://michaelhuo2030.github.io/office-memory/ &nbsp;·&nbsp; **Repo:** https://github.com/michaelhuo2030/office-memory

A ~120-line, **in-browser** demonstration of the one capability this chip exists to make **µW-always-on**: a **private, reversible, mergeable episodic memory.** Talk for a while (or load a sample work-day); the session is compressed into **one ~10 KB hypervector** — the raw audio is thrown away — then you query it three ways:

- **① by time** — *"what was I doing at 11:15?"* → `unbind(M, timeKey)` → the content
- **② by content / mood** — *"when did I get angry / mention architecture?"* → `unbind(M, contentKey)` → the times
- **③ by similarity** — *"what past moment is this like?"* → cosine

It runs today, with no server and nothing uploaded; the chip is what makes the same algebra run **all day, at microwatts, on a wearable.**

## Why this is the case study — and not a recognizer

Recognition (gestures, speech, images) is exactly where neural nets **tie or beat** HDC, and faster. So the demo deliberately showcases the *other* thing — the one capability a neural net **cannot do cleanly**:

| Property | HDC here | A neural net |
|---|---|---|
| **private** | memory is one local vector; raw recording discarded | typically needs the data (or its activations) |
| **mergeable** | two people's memories combine by **vector addition** (share a *sum*, not raw data) | must centralize or retrain to merge |
| **reversible / auditable** | `unbind` exactly recovers what was bound; **deterministic** every run | learned, approximate, black-box |
| **append-forever** | O(1) to add a moment; no retrain, no forgetting (to a capacity bound) | retraining / catastrophic forgetting |

A cloud assistant answering *"when did I mention that client?"* has to **store and replay your whole day.** This memory answers it from **one private vector** that never left the device.

## What runs today vs what the chip adds

- **Today (this demo, any browser):** the full HDC memory algebra — bind / bundle / `unbind`, deterministic, private, O(1) append. Verified end-to-end.
- **What the chip (`millisecond-era`) adds:** µW always-on at large D, on-device, non-volatile compute-in-memory — so it runs **continuously, all day, on glasses / a pendant**, which a phone CPU burning watts cannot. *That gap is the chip thesis.*

## Honest bounds (no-vaporware)

- Turning speech/text into vectors is a **neural net's** job (HDC operates on those vectors); plain similarity search **≈ a vector DB**. HDC's edge is **compression into one vector + a time-structure you can `unbind` + bit-level determinism + µW on CIM** — not "smarter" or "faster on a laptop" (on commodity hardware a small net is faster).
- Memory is **bounded (~D/20 items — a theorem)**: a *silicon hippocampus*, not infinite recall.
- The chip is a **thesis in progress** (Stage 0 FPGA today; first silicon est. 12–24 months).

→ Design principles behind it: [PHILOSOPHY.md](PHILOSOPHY.md) (withered technology + an enabling layer). Fast HDC kernel: [`hdc-neon`](https://github.com/michaelhuo2030/hdc-neon).
