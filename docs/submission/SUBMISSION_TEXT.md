# Quantum Claim Court
### Where Scientific Claims Face Literature, Mathematics and Quantum Evidence

**Qollab × IonQ Quantum Hackathon 2026 · AgentNOMOS Quantum Lab**

> The project does not invent quantum cloning. It creates an auditable scientific claim-verification experience around established quantum physics.

---

## The idea in one minute

"Quantum computers can copy any quantum state." "This experiment proves the no-cloning theorem." "The best possible copy is 90% faithful."

Claims like these appear in talks, articles and AI-generated summaries. Some are true, some are almost true, and some are false but cite real papers. Quantum Claim Court puts eighteen such claims **on trial**.

Each claim is examined by three independent witnesses:

1. **Literature:** what the original publications actually say, at the level we checked.
2. **Mathematics:** established theorems, and the exact behaviour of our circuit.
3. **Quantum measurement:** what a real quantum circuit, run once in Qollab, actually observed.

The court then gives one of five verdicts: **Supported, Disputed, Insufficient, Rewrite** or **Blocked**. Every verdict is explained, and many come with a corrected claim the court would accept.

## Why scientific quantum claims need verification

Quantum physics is easy to overstate. A real citation can be attached to a claim it never made. A finite experiment can be presented as proof of a universal law. And a correct number can be quoted outside the conditions where it holds. Quantum Claim Court makes these failure modes visible and testable.

## The physics, without the jargon

- **No-cloning.** You cannot build a machine that makes a perfect copy of an *unknown* quantum state. This was shown mathematically by Wootters and Zurek in 1982. It is a theorem, not an experimental observation.
- **Approximate cloning is possible.** In 1996 Bužek and Hillery described a "universal quantum copying machine": imperfect copies whose quality does not depend on the input.
- **The best possible copy.** Bruß and colleagues (1998) showed that for this kind of copier the best achievable copy quality, called fidelity, is **5/6 ≈ 83.3%**. This bound has precise conditions: one input to two outputs, the same quality for every input, equal quality for both copies, and success every time.

## The real quantum circuit

- **The circuit:** a 3-qubit circuit, the Bužek–Braunstein–Hillery–Bruß network:
  - qubit 0 holds the state to be copied and becomes **clone A**;
  - qubit 1 becomes **clone B**;
  - qubit 2 is the **machine qubit**, which absorbs the unavoidable disturbance.
- **Gates:** 5 RY, 3 RZ, 1 controlled-RY, 4 CNOTs and 2 measurements (depth 9).
- **The input state:** fixed and documented, Rz(0.7)·Ry(1.1)|0⟩.
- **How fidelity is measured:** after copying, the input rotation is undone on each clone, so "measures 0" means "matches the original". That turns copy quality into a simple measured frequency.
- **One job:** each Run submits **exactly one bare circuit, once** (2000 shots). Everything you click afterwards is local and launches no new quantum job.
- **Backends:** Qollab's built-in simulator (ideal) or IonQ's free remote simulator (with a noise model of an IonQ system). IonQ quantum computers are refused, so no credits are ever used. On a noise-model simulator the app shows the noise model and explains that deviations from the ideal 5/6 are expected and do not challenge the mathematics.
- **IonQ status:** a Run attempted on IonQ's free remote simulator in Qollab failed with a backend connection error. No IonQ result is reported.

## What you can do in the app

- **A · Claim docket:** eighteen claims with their verdicts. Filter them, and see which ones need measurement evidence.
- **B · Original sources:** each paper shows its DOI, authors, what was verified (metadata, abstract) and what was **not** (full text). A citation test bench shows a valid reference, a fabricated DOI, a wrong DOI-to-title mapping, a genuine but irrelevant paper, and a genuine paper that does not say what is claimed.
- **C · Experiment:** the circuit, the backend, this Run's raw counts, and measured vs exact copy quality with 99% confidence intervals.
- **D · Three witnesses:** literature, mathematics and measurement for every claim, side by side.
- **E · Verdict and "Challenge the court":** open any case file. Then build your own claim from a statement, a citation and a framing (84 combinations), and see how the court rules. These rulings are clearly labelled **LOCAL EVALUATION**: they reuse the Run's single measurement and frozen rules, and launch no new job.
- **F · Limits and evidence:** the scientific limitations, a browser integrity cross-check, and the exact evidence text to copy.

## Independent verification

- The app exports its evidence as exact text with SHA-256 hashes.
- A standalone verifier that uses only the Python standard library re-derives everything from that text:
  - counts and copy fidelities;
  - confidence intervals;
  - the exact values, with its own simulator;
  - all claim verdicts and all 84 challenge rulings.
- A hash shows the text is unchanged. It does **not** prove who produced it.

## The successful Qollab run

- **The run:** on 2026-10-10 the team ran the app on Qollab's built-in simulator (`basic_simulator`, Qiskit `BasicSimulator`, 2000 shots), with one job. Raw counts: **00: 1347, 01: 327, 10: 326**.

| | Measured | Exact | 99% interval contains exact? |
|---|---|---|---|
| Clone A | 1673/2000 = 0.8365 | 5/6 | yes |
| Clone B | 1674/2000 = 0.8370 | 5/6 | yes |
| Both clones jointly | 1347/2000 = 0.6735 | 2/3 | yes |

- **Verification:** the evidence of that run verified independently.
  - Measurement evidence SHA-256: `57f0388c…77ac77c1`.
  - Court record SHA-256: `b9cf5cce…6321b495`, bound to that measurement.
- **Next runs:** every new Run produces new counts. These numbers are a record of one run, not values built into the app.

## Scientific limitations (stated in the app)

- A simulator, not quantum hardware. IonQ's remote simulators add a hardware noise model, so their results may fall below the ideal values. Noise cannot disprove the no-cloning theorem.
- One input state is measured live. The input-independence of the copies comes from the exact calculation, and the optimality of 5/6 from the literature.
- Finite-shot uncertainty: about ±0.03 at 2000 shots. About 1.4% of correct runs will show a "Disputed" by pure chance.
- Literature is checked at title or abstract level. No full texts were reviewed.
- The claim register is frozen and structured by hand. **This is not a general-purpose scientific fact checker.**

## What is new

Each ingredient is established science: the no-cloning theorem, the Bužek–Hillery copier, the 5/6 bound, the Qiskit circuit. What we add is the **integrated, auditable court**:
- three evidence classes that are never allowed to substitute for each other;
- explicit evidence levels, so metadata, abstract and full text are never conflated;
- measurement that can change only the claims that depend on it;
- interactive challenges without extra quantum jobs;
- byte-exact evidence that a reviewer can verify offline.

## Relationship to prior work, and AI assistance

- **Prior work:** the team has earlier concepts for verifying scientific claims (UVO / ActionGate 2.0). They inspired the separation into evidence classes. **No code, data or private API** from them, or from the team's other hackathon projects, was used. Quantum Claim Court was written from scratch during the build window.
- **Third-party code:** the physics follows the publications cited above. Qiskit is used under its own licence.
- **AI assistance:** code and text were prepared with AI assistance (Claude, Anthropic) under the team's direction and review.

## Reproducibility

The public repository contains:
- the full source;
- deterministic builds that reproduce the Qollab ZIPs byte for byte;
- a standard-library exact-value script and the independent verifiers;
- 185 Python tests (37 headless-browser), plus 27 JavaScript tests.

See `docs/REPRODUCIBILITY.md`.

## Links

- Qollab project: **https://qollab.xyz/u/agentnomos/quantum-claim-court**
- Public source: **https://github.com/AgentNOMOS/quantum-claim-court**
- Demo video (2–3 min): **[PUBLIC VIDEO URL — to be added by the team]**

MIT licensed. **This effort is supported by Qollab & IonQ.**
