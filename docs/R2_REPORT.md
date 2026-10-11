# UQCC-R2 — Interactive Quantum Claim Court (2026-10-10)

Base: UQCC-R1 `7e7e340` (tag `uqcc-r1`), owner-verified in real Qollab:
- basic_simulator, Python 3.14.2, Qiskit 2.5.2
- counts 00:1331 / 01:329 / 10:340
- evidence sha256 8df0de20…

## Scientific freeze
- `uqcc_r1/*` and `verifier/verify_uqcc_r1.py` ship byte-identical to tag `uqcc-r1`. `scripts/build_r2_zip.py` aborts if any of them differ.
- Unchanged: circuit, input, inverse rotations, bit order, claim rules, manifest, and 99% Bonferroni-3 intervals.
- New code only adds to this:
  - `uqcc_app/court.py`: 4 value claims (V1–V4), a challenge matrix of 6 statements × 7 citations × 2 framings = 84 cells each decided by the frozen `claims.decide`, witness codes, and rewrites.
  - `uqcc_app/js_api.py`: the bridge.

## Qollab contract (as used by the team's earlier JS apps that ran in real Qollab)
- `index.html` is a body fragment: no html/head/body/script tags, and no `<header>` either (defensive). `main.css` is auto-loaded.
- `main.js` does `import * as api from 'uqcc_app.js_api'`, then calls `api.run_court.callPromising(backend)` **once**, guarded.
- All later interaction is local: no Python call, no quantum job.
- Python returns one JSON string. The export text is built in Python and shown verbatim in a textarea.
- Copy: Clipboard API, then execCommand fallback, then a "text selected, press Ctrl+C" message. There is no download button (Blob download did nothing in the earlier app).

## Evidence
- The export contains two blocks:
  - UQCC_R1_EVIDENCE: the frozen schema; it also verifies with the R1 verifier.
  - UQCC_R2_COURT: canonical, float-free, and bound to the R1 evidence sha256.
- `verifier/verify_uqcc_r2.py` (stdlib only):
  - runs the frozen R1 verifier;
  - re-decides V1–V4 and all 84 cells independently (using the R1 verifier's re-decision rules, not app code);
  - checks 12 pre-registered cells.
- The browser cross-check (pure-JS SHA-256, re-decoded counts) is consistency only, not provenance.

## Tests
- Python: 116 passed on 3.13.5 and 3.14.3:
  - 65 R1-era tests, unchanged
  - 35 R2
  - 16 headless Chromium with a mocked bridge (fixtures produced by the real Python bridge)
- Node: 11 passed (logic + SHA-256).
- The browser tests cover:
  - widths 1280/820/375/320: no horizontal overflow, no hidden or clipped controls;
  - a null-origin sandboxed iframe: clipboard fallback, and pure-JS SHA-256 works without `crypto.subtle`;
  - one bridge call only;
  - exact clipboard copy, then the verifier passes on it;
  - failure states show no data.

## Not yet verified
The real Qollab browser run of the R2 ZIP.
