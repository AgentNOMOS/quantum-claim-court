# UQCC-R0 — Quantum Claim Court: research spike report

Date: 2026-10-10 (UTC). Status: **R0 research spike, awaiting owner review.** Nothing published or submitted, and no IonQ calls were made.

## 1. Candidate comparison

| Criterion | A: No-cloning | B: BB84 intercept-resend | C: Algorithm (e.g. Deutsch–Jozsa) |
|---|---|---|---|
| Primary sources verified in R0 | 8 cloning papers on Crossref; 4 also have arXiv abstracts with quotable claims | BB84 (TCS 2014 reprint), Ekert91, Scarani 2009 RMP: metadata only | Deutsch–Jozsa 1992: metadata only |
| Exact, quotable number | **5/6** (Bruß et al. 1998 abstract), 2/3 joint | 25% QBER on sifted key for full intercept-resend (standard result, but no abstract quote retrieved) | Exact 1-query separation, deterministic |
| Circuit | 3 qubits, 4 CX + 1 CRY, depth 9 | 2–3 qubits per round, but many rounds | 3–5 qubits |
| Quantumness of the observable | High: a fidelity that is impossible to reach perfectly | Medium: classical simulation of the protocol is easy | Low: the oracle model hides the comparison |
| Separation of evidence classes | Clean: theorem (impossibility), positive result (5/6), measurement | QBER ≠ security is a strong lesson, but needs many runs | Speedup claims can't be tested on small runs, so the measurement side is weak |
| Distinct from projects 1–3 | Yes: not a game, an optimiser, or QEC | Yes | Overlaps the "query/oracle" tutorial genre |
| Tutorial risk | Medium (the BH cloner is a known circuit); the novelty is the court, not the circuit | High (BB84 demos are very common) | High |
| Fits 1 bare circuit per Run | Yes | Awkward (needs many rounds) | Yes |
| Build time | Low | Medium | Low |

**Selected: A — No-Cloning Claim Court.** It is the only candidate where the three evidence classes can each **disagree** with a claim in a measurable way:
- the impossibility theorem blocks claims,
- the 5/6 optimality result disputes or blocks overclaims,
- the measured shots dispute misstated values.

## 2. Scientific question

*Which claims about quantum copying survive checking against verified primary literature, exact mathematics, and real shot data, each kept separate?*

Experiment-level claim (C01): on an ideal noiseless simulator, the Bužek–Braunstein–Hillery–Bruß gate network produces two clones whose single-copy fidelity is consistent with 5/6 (±0.01) on all 8 tested input states.

## 3. Mathematics

- Input |ψ(θ,φ)⟩ = Rz(φ)Ry(θ)|0⟩.
- Machine state (2|00⟩+|01⟩+|11⟩)/√6 on (b,c), followed by CX(a→b), CX(a→c), CX(b→a), CX(c→a) [BBHB97 network].
- Exact results, recomputed independently by Qiskit `Statevector` and by the stdlib verifier:
  - F_A = F_B = **5/6** for every input.
  - Joint fidelity ⟨ψψ|ρ_AB|ψψ⟩ = **2/3**.
  - Machine qubit: input-dependent.
- Readout: undo U on each clone and measure. Then P(0) = F exactly and P(00) = joint fidelity. **One circuit gives three fidelity estimates.**
- Comparison circuit, the CNOT "copier":
  - F = (1+z²)/2, which is 1 on |0⟩ and |1⟩ and ½ on the equator.
  - Bloch-sphere average 2/3 (checked by quadrature in the tests).
- What the experiment does **not** do:
  - It does not prove no-cloning, which is a statement about all unitaries.
  - It does not prove that 5/6 is optimal (that is Bruß et al. / Gisin–Massar; R0 does not re-derive it).
  - It says nothing about hardware.

## 4. Measured results (BasicSimulator, seeded, 20 000 shots per state, 95% Wilson CIs with Bonferroni correction over 8 states, z = 2.734)

| Panel | Result |
|---|---|
| BH cloner, 8 states | F_A in 0.8307–0.8376; F_B in 0.8290–0.8345. All 16 CIs contain 0.8333, max half-width 0.0073. Joint fidelity in 0.6602–0.6707, all CIs contain 0.6667. |
| CNOT copier | Z±: 1.0000 (CI lower bound 0.9996). X±/Y±: 0.494–0.504. G1 0.603, G2 0.721–0.726, matching exact 0.6029 / 0.7220. |
| BH, 60 shots | Point estimates 0.77–0.93. CI half-widths up to ~0.15, so the ±0.01 claim gets **INSUFFICIENT**. |
| Flagship circuit, bare `BasicSimulator().run`, 2000 shots, seed 7 | P(A=0) = 1657/2000 = 0.829 |

## 5. Source verification (frozen manifest `uqcc/sources.json`, r0.1)

- **Metadata:** fetched from the Crossref REST API between 2026-10-10T12:04:44Z and 12:08:23Z. arXiv abstracts fetched at 12:06:18Z. The raw responses are kept in `evidence/raw/`, and the manifest metadata is generated from those files, not typed by hand.
- **Basis levels:**
  - `ABSTRACT_TEXT`: the quote is checked verbatim against the retrieved arXiv abstract.
  - `TITLE_TEXT`: the title states the proposition (WZ82).
  - `CURATED`: widely known, but primary text **not** retrieved (Dieks82, Massar–Popescu95, Scarani et al. 2005 review). The gate refuses to treat `CURATED` as sufficient.
- **Negative evidence:** Crossref returned 404 for 10.1103/PhysRevLett.130.999999 (the fictitious control) and 10.1103/PhysRevLett.79.2156 (a mistyped page for Gisin–Massar; the correct one is 79.2153).
- **Wrong-mapping control:** 10.1103/PhysRevLett.81.2152 is real, but it is Cory et al., "Experimental Quantum Error Correction", not Bužek–Hillery.
- **Limits:** the manifest is a frozen snapshot, not a live search. Its SHA-256 shows only that the file is unchanged. Full texts (paywalled APS/Nature) were **not** read.

## 6. Gate verdicts (16 claims, all match pre-registered expectations)

SUPPORTED: C01, C02, C03, C16 · DISPUTED: C06, C15 · INSUFFICIENT: C10, C11, C12 · REWRITE: C05, C09, C13 · BLOCK: C04, C07, C08, C14.

| Required case | Claim | Verdict |
|---|---|---|
| Genuine source, correctly limited claim | C02 (Bruß et al., 5/6 optimal) | SUPPORTED |
| Genuine source + new experiment | C01 | SUPPORTED |
| Real source, exaggerated | C06 (WZ82 "not even approximately") | DISPUTED, with rewrite |
| Fabricated citation | C07 (fictitious, Crossref 404) | BLOCK |
| Wrong DOI-to-title mapping | C08 | BLOCK |
| Genuine but irrelevant citation | C09 (Deutsch–Jozsa cited for 5/6) | REWRITE: cite BDEFMS98 |
| Contradicted by a theorem | C04 (CNOT clones anything), C14 (F = 0.9 universal) | BLOCK |
| Measurement disputes a value | C15 (2/3 per clone) | DISPUTED |
| Insufficient: too few shots / wrong platform / curated-only source | C10 / C11 / C12 | INSUFFICIENT |
| Finite experiment "proves" a theorem | C05 | REWRITE |
| Hash used as authenticity | C13 | REWRITE |

## 7. Difference from the Quantum Research Governor (project 3)

- **Different question.** QRG asks whether a quantum measurement supports an operational conclusion (decision over its own experiment). UQCC asks whether an **external scientific claim** holds: citation existence and metadata, whether a source actually states the claim, theorem scope, and contradiction with known results. Its own experiment is only one of three evidence classes.
- **Different physics.** No-cloning and optimal cloning, not QEC.
- **Shared idea.** Both are evidence gates. The owner should judge whether a jury sees them as the same "AI-governance-over-quantum" theme. Our assessment: they are distinct in substance (5 of 9 gate rules concern literature or theorem scope, which QRG does not have), but there is a real *positioning* overlap.

## 8. Hackathon / security notes

- **Official terms not re-fetched in R0.** A web search did not find the terms page. Facts below come from today's notes on earlier projects:
  - build window 2026-10-09 23:00Z → 2026-10-11 23:00Z
  - MIT public repo + public Qollab project + 2–3 min public video
  - attribution "This effort is supported by Qollab & IonQ"
- **Open question:** whether one team may submit several projects. The owner must check the terms or FAQ.
- **Clean-room.** No access to Quantum Impossible, Quantum Allocation Lab, QRG, UVO/ActionGate 2.0, or AgentNOMOS production. No secrets, endpoints, payments, or publication.

## 9. Known limitations

- Ideal simulator only, no noise model, no hardware.
- 8 input states is not "all states".
- Claims are hand-structured; there is no natural-language claim extraction.
- Proposition mapping is curated by the builder (the quote check makes it auditable but not automatic).
- The contradiction register is small and hand-written.
- Python 3.13/3.14 locally; Qollab in-browser execution is not tested.
