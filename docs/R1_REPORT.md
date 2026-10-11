# UQCC-R1 — Qollab cloning smoke package (2026-10-10)

Base: UQCC-R0 `9e71e4d` (tag `uqcc-r0`). The R0 code under `uqcc/`, `verifier/` and `tests/test_uqcc.py` is unchanged.

## Package
`dist/uqcc_r1_qollab_smoke.zip`: 10 files, deterministic build (`scripts/build_r1_zip.py`). Sources are in `qollab_r1/`.
- `main.py` uses only the injected global `backend`. It refuses (zero jobs) if there is no backend, if the backend is not BasicSimulator, or if the backend target lacks a gate. It then calls `backend.run(circuit, shots=2000)` exactly once. There is no seed, no transpile, no fallback and no retry.
- The circuit is identical to R0 `bh_cloner(1.1, 0.7)`: 3 qubits, 5 ry, 3 rz, 1 cry, 4 cx, 2 measure, depth 9, size 15.
- Evidence is one canonical JSON line (sorted keys, compact separators, ASCII, no floats) with its SHA-256 printed above it.
- `verifier/verify_uqcc_r1.py` (stdlib only) hashes that exact line and never re-serialises it.

## Statistics
- 99% family-wise Wilson intervals, Bonferroni over 3 observables (z = 2.935).
- Measured locally with the 95% setting: 102 of 2000 correct runs showed DISPUTED by chance (5.1%). That was too high for a live demo, so R1 uses 99%.
- With 99%: 27 of 2000 (1.35%) false DISPUTED; largest half-width 0.032.
- An unseeded R1 test run hit exactly this case once and showed 2 failing tests (0.95 setting). The harness now seeds the *mock* backend only; the app call is unchanged.

## Evidence levels (frozen manifest r1.0, sha256 9de87809…, derived from R0 r0.1)
| Source | METADATA VERIFIED | ABSTRACT CHECKED | TEXT VERIFIED |
|---|---|---|---|
| Wootters & Zurek 1982 | yes (Crossref) | no (title only) | no |
| Bužek & Hillery 1996 | yes | yes (arXiv quant-ph/9607018) | no |
| Bruß et al. 1998 | yes | yes (arXiv quant-ph/9705038) | no |
| Bužek–Braunstein–Hillery–Bruß 1997 | yes | yes | no |

Bužek & Hillery 1996 is **not** credited with 5/6 or with optimality: its abstract states neither. Claim RT7 therefore comes out INSUFFICIENT.

## Open risks
- Not run in the real Qollab yet.
- The evidence line is ~10.8 KB on a single line. If the Qollab console wraps or truncates it, the verifier fails explicitly; it does not fall back to anything.
- The console SHA-256 shows only that the pasted text is intact, not where it came from.
