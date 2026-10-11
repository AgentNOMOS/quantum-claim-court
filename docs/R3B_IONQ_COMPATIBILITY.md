# UQCC-R3b: IonQ free-simulator compatibility

**Status: release candidate, not owner-accepted.** No IonQ run has been performed by the build process. Everything IonQ-related below was checked with synthetic test doubles and offline interface checks only.

## Why

The hackathon rules require projects to run "on Qollab's free simulators, including IonQ's quantum simulator". The R2 app (`dist/uqcc_r2_claim_court_app.zip`) refused every backend except Qiskit's BasicSimulator. R3b allows the free IonQ remote simulator as well, and nothing else.

## What changed relative to R3 (`uqcc-r3-submission-rc1`)

- **`app_r3b/` is a patched copy of `app/`.**
  - `app/` is unchanged, so the R2 ZIP still rebuilds byte-identically (`8edd6166…9cf16ea0`).
  - The frozen R1 science files (`qollab_r1/uqcc_r1/*`, `verify_uqcc_r1.py`) are unchanged. Their pins are in `scripts/frozen_pins.json`.
- **`app_r3b/uqcc_app/backend_policy.py` (new):** positive identification of the backend, failing closed (see below).
- **`app_r3b/uqcc_app/runner.py` (new):**
  - It mirrors the frozen `uqcc_r1.app.run` line for line, using only frozen functions. The single difference is that `backend_policy.classify` replaces the R1 allow-list.
  - Tests prove that for BasicSimulator it gives evidence byte-identical to the frozen runner.
- **`app_r3b/uqcc_app/court.py`:**
  - The court record (schema `uqcc-r3b-court/1`) gains `backend_context`: kind, free_simulator, noise_model, ideal_reference_applies, class MRO, and interpretation text.
  - When a noise model was simulated, the reason text of a DISPUTED value claim says so instead of quoting the 1.4% chance figure.
  - **No verdict rule changed.** The same measurement gives the same verdicts as R2.
- **`app_r3b/verifier/verify_uqcc_r3b.py` (replaces `verify_uqcc_r2.py` in the R3b ZIP; stdlib only):**
  - It verifies the measurement block with a verbatim copy of the frozen R1 `verify()`. Only the backend check is replaced by the R3b policy, and a test asserts that the copy differs in exactly that line.
  - It re-checks the backend context and the dispute-reason wording.
  - It re-decides V1–V4 and all 84 challenge cells.
- **UI (`index.html`, `main.js`, `ui/render.js`, `ui/logic.js`, `main.css`):**
  - Scene C shows the backend type, the noise model and an ideal/noise-model notice.
  - The status line shows the noise model.
  - The browser cross-check adds "authorised free simulator (no QPU)".
  - Static texts no longer say "ideal simulator" unconditionally.
- **Circuit, input state, measurement meaning, statistics (99% family-wise Wilson, Bonferroni-3), claims, sources and the challenge matrix are unchanged.**

## Backend authorization (`backend_policy.classify`)

| Kind | Accepted only if |
|---|---|
| `builtin_basic_simulator` | The frozen R1 rule: name `basic_simulator` or class name `BasicSimulator`. Refused if anything about it says QPU. |
| `ionq_remote_simulator` | **All** of the following: the class MRO contains `qiskit_ionq.*.IonQSimulatorBackend`; the MRO contains no `IonQQPUBackend`; the backend's `_simulator` flag is exactly `True`; the name matches `^ionq_simulator(\.[a-z0-9-]{1,32})?$` (anchored; never a substring test); `options.noise_model` is a short plain string. |

- **Everything else is refused before any job is sent**, with "Zero jobs submitted" in the message. That covers:
  - IonQ QPUs (they consume credits);
  - any class carrying both simulator and QPU identity;
  - duck-typed objects;
  - look-alike class names from other modules;
  - unknown providers;
  - a missing or empty name;
  - a missing, false or merely truthy simulator flag;
  - a missing or malformed noise model.
- **Source of the identities:** qiskit-ionq 1.1.1, inspected offline:
  - `IonQSimulatorBackend`, name `ionq_simulator`, `_simulator=True`, `options.noise_model` (default `ideal`);
  - `IonQQPUBackend`, names `ionq_qpu`, `ionq_qpu.forte-1` and so on, `_simulator=False`.
- **Not documented by Qollab:** which Python class it injects for the IonQ simulator. If Qollab uses a different class, the Run is refused. The refusal records the observed name and class, so nothing is sent and nothing is guessed.

## IonQ noise and scientific interpretation

- **The noise:** Qollab's IonQ remote simulators apply a noise model of an IonQ system (for example Forte 1 or Aria). They are free, but they are not ideal.
- **The exact values** 5/6, 5/6 and 2/3 are properties of the **ideal** circuit and remain valid. A noisy Run may measure lower fidelities. Its intervals may then exclude the ideal values, and C1, V1 and V3 may be DISPUTED.
- **What the court shows in that case:**
  - the actual counts;
  - the backend and its noise model;
  - a notice that the ideal reference is being compared with a noisy simulation;
  - a reason text stating that the deviation is expected and is **not** evidence against the mathematics or the no-cloning theorem.
- **Unaffected by noise:**
  - theorem, literature and scope claims (C2–C4, RT1–RT10);
  - the 84-cell challenge matrix.

  These are not decided by the measurement, and tests assert they are identical on noisy and ideal Runs.
- **Exit codes:** the verifier returns exit 2, VERIFIED_INCONSISTENT, for valid evidence that disagrees with an ideal value. On a noise-model simulator that is an expected outcome, not a failure of the evidence.
- **Hardware:** a noise-model simulation is still a simulation. It establishes nothing definitive about IonQ hardware.

## One-job contract

- **Per Run:**
  - exactly one bare `QuantumCircuit`;
  - exactly one `backend.run(qc, shots=2000)`;
  - no transpile, retry or fallback.
- **A second `run_court` call in the same Run** is refused without a job.
- **A provider failure** is shown as "failed", with "NOT retried".
- **All court interactions are local.** The browser tests click through every scene and assert that the bridge was called exactly once.
- **Gate compatibility:**
  - IonQ accepts the standard gate set without transpilation (Qollab "Transpilation" doc).
  - Offline, qiskit-ionq serialises the frozen circuit as **one `ionq.circuit.v1` payload** with 13 gates: ry, rz, ry, ry, controlled-ry, 4 × controlled-x, rz, ry, rz, ry.
  - No gate conversion is needed, so none is performed.

## Tests (all local; no IonQ or Qollab contact)

| Suite | Result |
|---|---|
| Python, all (Python 3.13.5 and 3.14.3) | 185 / 185: 118 R0–R3, 46 `tests/test_r3b.py`, 21 `tests/test_r3b_browser.py` (headless Chromium) |
| JavaScript (Node) | 27 / 27: 11 R2 plus 16 R3b (`dev/js_tests/logic_r3b.test.mjs`) |
| `scripts/ionq_offline_check.py` (real qiskit-ionq 1.1.1, sockets disabled) | PASS: 4 QPU names refused; simulator accepted under ideal, aria-1 and forte-1; 1 run call; verifier accepts the record |
| Unseeded local BasicSimulator Run → `verify_uqcc_r3b.py` | VERIFIED_CONSISTENT, 256 checks, 84 cells |

- **Synthetic stand-ins:** the IonQ objects in the test suites are synthetic (`dev/ionq_mocks.py`) and carry qiskit-ionq's identity surface.
- **What none of this shows:** none of it is a real IonQ Run, and none of it shows Qollab's live IonQ behaviour.

## Package

`dist/uqcc_r3b_ionq_compatible_rc.zip`. It is deterministic, rebuilt by `scripts/build_r3b_zip.py`, and its SHA-256 is pinned in `scripts/r3b_pins.json`.
