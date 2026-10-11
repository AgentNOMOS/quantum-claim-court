# Quantum Claim Court

*Can a quantum claim survive scientific verification?*

A scientific claim about copying quantum states is brought before the court. Three independent witnesses testify, and none of them may speak for the others:

1. **Literature:** what the original publications establish, at the level we actually checked. That means Crossref metadata, and arXiv abstract or title text. No full text was reviewed.
2. **Mathematics:** established theorems (no-cloning; the 5/6 optimum), and the exact state-vector values of this circuit.
3. **Quantum measurement:** what this Run's single 2000-shot execution observed, with 99% family-wise Wilson intervals.

## What runs

- Each Run executes **one bare 3-qubit `QuantumCircuit` once** on the backend Qollab injects. There is no retry and no fallback simulator. Two free simulators are accepted:
  - the Qollab **built-in simulator** (Qiskit BasicSimulator, ideal);
  - an **IonQ remote simulator** (free; it applies a noise model of an IonQ system), positively identified as qiskit-ionq's `IonQSimulatorBackend`.

  **IonQ quantum computers (hardware, credits) are always refused**, as are unknown or ambiguous backends. A refusal happens before any job is sent. IonQ allows one job per Run, and this app sends exactly one.
- The circuit is the Bužek–Braunstein–Hillery–Bruß universal 1→2 cloner. The fixed input is |ψ⟩ = Rz(0.7)·Ry(1.1)|0⟩.
- Each clone has the input rotation undone and is measured, so P(clone reads 0) is its fidelity and P(both 0) is the joint fidelity.
- Exact values: **clone A 5/6, clone B 5/6, joint 2/3**.

## Six scenes

| Scene | What it shows |
|---|---|
| A · Docket | 18 claims: 14 frozen R1 claims plus 4 R2 measurement-value claims. Claims that need measurement are marked. |
| B · Sources | Wootters & Zurek 1982, Bužek & Hillery 1996, Bruß et al. 1998, each with what was and was not verified, plus a five-case citation test bench. |
| C · Experiment | The circuit, the backend, this Run's raw counts, and measured vs exact fidelities. |
| D · Witnesses | Literature, mathematics and measurement for every claim, side by side. |
| E · Verdict | The case file for each claim, and a "challenge the court" builder (LOCAL EVALUATION, no new job). |
| F · Limits & evidence | Limitations, a browser cross-check (consistency only), and the exact evidence export. |

## Verify the evidence

Copy the export box into `evidence.txt`, then run:

    python3 -I verifier/verify_uqcc_r3b.py evidence.txt .

The verifier uses the Python standard library only.
- It checks the measurement block with the frozen R1 checks (only the backend check is widened to the two free simulators).
- It re-checks the backend classification and noise-model context.
- It re-decides the four value claims and all 84 challenge cells.

Exit codes: 0 = consistent, 2 = valid evidence but the measurement disagrees with an exact ideal value (expected on a noise-model simulator), 1 = fail. SHA-256 shows that the content is unchanged, not who produced it.

## What this does not show

- **The no-cloning theorem is a mathematical result** (Wootters & Zurek 1982). It does not come from this experiment.
- **5/6 is optimal only for deterministic, symmetric, universal 1→2 qubit cloning** (Bruß et al. 1998). It does not apply to asymmetric, probabilistic or state-dependent cloning.
- The measurement covers **one input state on a simulator**, not hardware.
- On the **built-in (ideal) simulator**, about **1.4%** of runs of this correct circuit show DISPUTED by chance.
- On an **IonQ noise-model simulator**, the measured fidelities may fall below the ideal 5/6, 5/6, 2/3, and measurement claims may be DISPUTED. That describes the noisy Run, **not** the mathematics: noise cannot disprove the no-cloning theorem. The exact values remain the ideal-circuit prediction.
- The claim register is frozen and was structured by hand. This is not a general-purpose fact checker.

## References

- W. K. Wootters & W. H. Zurek, "A single quantum cannot be cloned", Nature 299, 802–803 (1982), doi:10.1038/299802a0
- V. Bužek & M. Hillery, "Quantum copying: Beyond the no-cloning theorem", Phys. Rev. A 54, 1844 (1996), doi:10.1103/PhysRevA.54.1844
- V. Bužek, S. L. Braunstein, M. Hillery & D. Bruß, "Quantum copying: A network", Phys. Rev. A 56, 3446 (1997), doi:10.1103/PhysRevA.56.3446
- D. Bruß, D. P. DiVincenzo, A. Ekert, C. A. Fuchs, C. Macchiavello & J. A. Smolin, "Optimal universal and state-dependent quantum cloning", Phys. Rev. A 57, 2368 (1998), doi:10.1103/PhysRevA.57.2368

## Prior work and AI-assistance disclosure

- **Prior work:** the team has earlier concepts for verifying scientific claims (UVO / ActionGate 2.0). Those inspired the separation into evidence classes. **No code, data or private API** from those systems, or from the team's other hackathon projects, was used. This is a clean-room implementation built during the hackathon window.
- **AI assistance:** code and text were prepared with AI assistance (Claude, Anthropic) under the team's direction and review.

MIT licensed. **This effort is supported by Qollab & IonQ.**
