# millisecond-era · site cheatsheet

Public repo → GitHub Pages (Jekyll, NO `.nojekyll`). Live: https://michaelhuo2030.github.io/millisecond-era/
Local preview: `python3 -m http.server 8792` from repo root → http://localhost:8792/

## Site architecture (rebuilt 2026-06-19 — "make every HTML playable + navigable")
- **`index.html`** (root) = the visual home/hub. **Jekyll serves `index.html` OVER `README.md`**, so:
  - Students/Pages visitors land on the playable hub (`index.html`).
  - `README.md` stays as the repo's research doc (still shown on github.com).
- **`site-nav.js`** (root) = ONE shared nav bar + the global EN/中 language toggle, included by every page. Reusable LEGO block.

## i18n — site-wide EN/中 toggle (added 2026-06-19, default English)
- **One global control lives in `site-nav.js`.** State in `localStorage('msEraLang')` ('en'|'zh', default 'en'),
  the SAME key the civ demos' own i18n uses → choice persists across all pages.
- On change it does BOTH, so two pre-existing mechanisms stay in sync under one switch:
  1. sets `<html data-lang>` → CSS (injected by nav): `html[data-lang=en] .lang-zh{display:none}` /
     `html[data-lang=zh] .lang-en{display:none}` / `html:not([data-lang]) .lang-zh{display:none}` (default EN).
  2. calls the page's own `setLang(l)` if defined (the civ demos' JS-dictionary i18n).
  Also dispatches `window` event **`mse:lang`** (detail = 'en'|'zh').
- **To make a page bilingual (static text):** wrap each run as
  `<span class="lang-en">English</span><span class="lang-zh">中文</span>` (English first). No per-page JS.
- **For JS-generated on-screen text:** pick by `document.documentElement.dataset.lang` (==='zh'?…:…) and
  re-render on `window.addEventListener('mse:lang', renderFn)`. Canvas/SVG labels too. Don't translate `<title>` via
  spans (can't) — put `English | 中文` plain. `<option>`/`<title>` need JS (data-en/data-zh) or plain dual text.
- Coverage: home + 18 explainers/demos bilingual; voice-xray + 5 long-tail civ demos already English; original
  5 civ demos use their own dict i18n (bridged). `<html lang>` set by nav to match.
- ⚠ A regex `<div>` open/close count is an unreliable validity check here — JS `innerHTML` templates contain
  `<div>`/`</div>` in string literals and skew the count. Validate by browser render + Python html.parser, not grep.
- Demos live under `learn/demos/` (8 speed demos + gallery), `learn/civilization/` (5 app demos + gallery),
  `learn/*.html` (reram/hdc/speed-trial explainers), `hdc/applications/sign-language/demo.html`.

## site-nav.js — the reusable block (works on BOTH localhost root AND Pages /millisecond-era/)
- Auto base-path detection: `location.pathname.match(/^(.*?\/millisecond-era\/)/)` → BASE, else `/`.
- Injects a slim sticky top bar + a **spacer div** at top of `<body>` so it never overlaps page CSS
  (don't use `padding-top` — pages override it; insert a real spacer element instead).
- Idempotent (`window.__mseNavLoaded` guard).
- **Include per page with a RELATIVE src** (not root-absolute — `/site-nav.js` 404s on Pages):
  - root page: `<script src="site-nav.js"></script>`
  - `learn/x.html`: `../site-nav.js` · `learn/demos/x.html`: `../../site-nav.js` · `hdc/applications/sign-language/`: `../../../site-nav.js`
- To re-inject after adding a new page: re-run the injector (counts depth, inserts before `</body>`, skips if `site-nav.js` already present).

## Link rules on Jekyll Pages (what 404s / "看不到东西")
- **Dir renders IF it has `README.md` OR `index.html`** (Jekyll auto-index). README-less dir → 404.
- **Raw `.py/.csv/.json`** → served as download / blank, NOT viewable. Link these to the **GitHub blob URL** instead:
  `https://github.com/michaelhuo2030/millisecond-era/blob/main/<path>` (renders identically on localhost + Pages).
- **Pure `.md` docs** in cards: link to GitHub blob too (localhost http.server serves raw .md; only Jekyll renders it).
- Verify with the link-checker one-liner (resolve every href/`](...)`, flag missing file / README-less dir / raw source).

## Deploy (only on Michael's explicit OK — public repo)
- Allow-list `git add` file-by-file (NEVER `git add .`). New: `index.html`, `site-nav.js`. Modified: 27 demo HTML (nav) + README/sub-READMEs (link repoints).
- Note: `fpga/SILICON-MEASURED-2026-06-13.md` carries PRIOR uncommitted work (抗噪 demo section) — include intentionally or stage separately.

## Public chip positioning update (2026-07-07)
- Current public boundary is `chip/C1-FIRST-SKU-PUBLIC-BRIEF-2026-07.md`, not the old fixed USB-C/PCIe tier table.
- C1 ladder: `0.1B / 0.3B / 1B / bounded 3B`; `>3B` stays C2/C3 future learning.
- Whole-picture framing: C1 is the bridgehead, not the ceiling. Keep 8B / 32B / 100B as C2/C3 frontier coordinates,
  not first-SKU promises.
- Buyer-facing order: same-task `tok/s`, latency, fixed-workload short-turn `Hz` + `ms/turn`, task success, then local/private/power. Bind model + ctx/gen + single-stream/batch + prefix-cache + operating point + status. C1-A headline: 0.1B resident weights, single-stream, prefix-cache hit 0%, `ctx256/gen64` ~1.87kHz/~0.534ms at plugged-in timing-bound point; same workload @3W ~924Hz/~1.08ms. TOPS/TFLOPS belong in footnotes.
- Rewritable wording: "provisionable resident model slots"; do not imply per-request hot-swap or online learning in ReRAM.
- Public-safe red lines: no cell programming recipes, circuit/floorplan/package/process private detail, partner names, unsupported AI4S 100x claims, or "replace GPU/DRIVE/Jetson safety stack" claims.
- `chip/model-2026-06/` is now an archived public physics snapshot. It is still useful, but current product/outreach copy starts from the C1 brief.
- Run `python3 scripts/public_c1_consistency_audit.py` before publishing public chip updates. It checks README, chip docs,
  public articles, FPGA/data archives, RWKV notes, and key `learn/` explainers for C1 anchors and stale Mini/Pro/USB-C/9B
  language.

## GitHub push release gate (living-impact guard)
- When Michael says "push to GitHub", treat it as a whole-repository release gate, not a narrow Git operation.
- Run `python3 scripts/living_impact_selftest.py` and `python3 scripts/public_c1_consistency_audit.py` before any public push.
- `living-impact-map.json` is the manifest: every live text surface must be either a `required_update` with anchors or an
  explicitly classified unaffected/archive surface with a reason.
- The C1 audit now calls the living-impact audit too. A file cannot pass only because it has one C1 label at the top while
  stale product claims remain elsewhere.
- Do not use `git add .`; inspect `git status -sb` and stage allow-listed files only.
