# Quantum Claim Court — UQCC-R1 cloning smoke test

**What runs:** one bare 3-qubit `QuantumCircuit` (the Bužek–Braunstein–Hillery–Bruß universal 1→2 cloner, PRA 56, 3446, 1997). It is submitted once, with 2000 shots, to the backend Qollab injects. There is no local fallback and no retry. Any backend other than BasicSimulator is refused before any job is sent.

**Input state (fixed):** |ψ⟩ = Rz(0.7) Ry(1.1) |0⟩. Each clone then gets the inverse rotation and is measured, so:
- P(clone reads 0) is that clone's fidelity;
- P(both 0) is the joint fidelity ⟨ψψ|ρ_AB|ψψ⟩.

**Exact values for this circuit:** clone A 5/6, clone B 5/6, joint 2/3, for every input state. The run reports measured estimates with 99% family-wise Wilson intervals (Bonferroni over 3). About 1.4% of runs of this correct circuit still show DISPUTED by chance (measured locally over 2000 seeds; 95% intervals gave 5.1%).

**What this does NOT show:**
- The **no-cloning theorem** is a mathematical result (Wootters & Zurek, Nature 299, 802, 1982). It does not come from this experiment, and a finite run cannot prove it.
- **5/6** is the optimal single-copy fidelity only for deterministic, symmetric, universal 1→2 qubit cloning (Bruß et al., PRA 57, 2368, 1998). It does not apply to asymmetric, probabilistic or state-dependent cloning. One interval containing 5/6 does not prove this circuit is optimal.
- Simulator results say nothing about hardware.

**Evidence levels (frozen offline manifest, no network at runtime):**
- SOURCE METADATA VERIFIED (Crossref)
- SOURCE ABSTRACT CHECKED (arXiv abstract; Bužek & Hillery 1996 and Bruß et al. 1998 yes, Wootters & Zurek 1982 title only)
- SOURCE TEXT VERIFIED: **no** for every source
- MATHEMATICAL RESULT ESTABLISHED
- SIMULATOR MEASUREMENT OBSERVED

These levels are kept separate and are never treated as equivalent.

**Claim court:**
- 4 scoped claims.
- 10 red-team claims: perfect cloning; "CNOT copies everything"; "experiment proves the theorem"; "optimum 0.9"; an irrelevant genuine DOI; a forged DOI; a relevant source without supporting text; an interval presented as an optimality proof; 5/6 over-generalised; a wrong DOI mapping.

**Verification:** the console prints `UQCC_R1_EVIDENCE_SHA256=…` and one exact evidence line. Save the whole console output to a file and run:
`python3 -I verifier/verify_uqcc_r1.py console.txt .`
The verifier uses the standard library only.

Code and text were prepared with AI assistance (Claude, Anthropic) under the team's direction. MIT licensed.
This effort is supported by Qollab & IonQ.
