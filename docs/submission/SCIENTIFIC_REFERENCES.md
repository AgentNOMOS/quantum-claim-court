# Scientific references: what each source supports, and how it was checked

Bibliographic metadata was retrieved from the **Crossref REST API** on 2026-10-10 between 12:04:44 and 12:08:23 UTC. Abstracts were retrieved from the **arXiv API** at 12:06:18 UTC. The raw responses are in `evidence/raw/`, and the frozen manifests (`uqcc/sources.json`, `qollab_r1/uqcc_r1/sources_manifest.py`) are generated from them.

**No full text was reviewed for any source.**

## Evidence levels (never treated as equivalent)

| Level | Meaning in this project |
|---|---|
| SOURCE_METADATA_VERIFIED | The DOI resolves in Crossref to this title, authors, year and venue (HTTP 200). |
| SOURCE_ABSTRACT_CHECKED | The quoted sentence appears verbatim in the arXiv abstract we retrieved. |
| SOURCE_TEXT_VERIFIED | Someone reviewed the full text. **False for every source here.** |
| MATHEMATICAL_RESULT_ESTABLISHED | A theorem established in the literature, or an exact calculation for this specific circuit. Which one is always stated. |
| SIMULATOR_MEASUREMENT_OBSERVED | Counts from a real run on a simulator (Qollab's built-in simulator, or a local one). Never hardware, and never a proof of a theorem. |

## The three primary publications

### 1. Wootters & Zurek (1982)
- W. K. Wootters, W. H. Zurek, **"A single quantum cannot be cloned"**, *Nature* **299**, 802–803 (1982). doi:[10.1038/299802a0](https://doi.org/10.1038/299802a0)
- **Levels:** metadata verified (Crossref, 12:04:44Z). Abstract check: **no**, no arXiv abstract retrieved. Full text: **no**.
- **Supports (title level):** perfect cloning of an unknown quantum state is impossible. This is the no-cloning theorem.
- **Does not support:** that approximate copying is impossible. The R0 research docket (claim C06) attributes that to this paper and is ruled DISPUTED.

### 2. Bužek & Hillery (1996)
- V. Bužek, M. Hillery, **"Quantum copying: Beyond the no-cloning theorem"**, *Physical Review A* **54**, 1844–1852 (1996). doi:[10.1103/PhysRevA.54.1844](https://doi.org/10.1103/PhysRevA.54.1844). arXiv:quant-ph/9607018.
- **Levels:** metadata verified (12:04:44Z). Abstract checked: **yes** (arXiv, 12:06:18Z). Full text: **no**.
- **Supports (abstract quote):** "there exists a "universal quantum copying machine", which approximately copies quantum mechanical states in such a way that the quality of its output does not depend on the input".
- **Not credited with:** the value 5/6, or the claim that 5/6 is optimal. The checked abstract states neither. A claim attributing the 5/6 optimum to this paper is ruled **INSUFFICIENT** (claim RT7).

### 3. Bruß, DiVincenzo, Ekert, Fuchs, Macchiavello & Smolin (1998)
- D. Bruß, D. P. DiVincenzo, A. Ekert, C. A. Fuchs, C. Macchiavello, J. A. Smolin, **"Optimal universal and state-dependent quantum cloning"**, *Physical Review A* **57**, 2368–2378 (1998). doi:[10.1103/PhysRevA.57.2368](https://doi.org/10.1103/PhysRevA.57.2368). arXiv:quant-ph/9705038.
- **Levels:** metadata verified (12:04:44Z). Abstract checked: **yes** (12:06:18Z). Full text: **no**.
- **Supports (abstract quote):** "The maximal fidelity of cloning is shown to be 5/6 for universal cloners". The abstract also says the work concerns cloners that produce "two clones out of a single input".
- **Scope used by the court:** deterministic, symmetric, universal, 1→2, qubits. Two caveats:
  - The words "deterministic" and "symmetric" are our statement of the standard setting. They were not checked against the full text.
  - The court refuses to carry 5/6 over to asymmetric, probabilistic, state-dependent or N→M cloning (claim RT9).

## Supporting and control sources

| Source | Role | Levels |
|---|---|---|
| V. Bužek, S. L. Braunstein, M. Hillery, D. Bruß, "Quantum copying: A network", PRA 56, 3446 (1997), doi:10.1103/PhysRevA.56.3446, arXiv:quant-ph/9703046 | Origin of the gate network we run. Abstract: "a network consisting of quantum gates which produces two imperfect copies of an arbitrary qubit". | metadata ✔, abstract ✔, full text ✘ |
| N. Gisin, S. Massar, "Optimal Quantum Cloning Machines", PRL 79, 2153 (1997), doi:10.1103/PhysRevLett.79.2153 | Optimality of N→M cloners (abstract: "we prove that the fidelity ... is optimal"). | metadata ✔, abstract ✔, full text ✘ |
| D. Deutsch, R. Jozsa, "Rapid solution of problems by quantum computation", Proc. R. Soc. A 439, 553 (1992), doi:10.1098/rspa.1992.0167 | **Control:** genuine but irrelevant to cloning. | metadata ✔ |
| D. G. Cory et al., "Experimental Quantum Error Correction", PRL 81, 2152 (1998), doi:10.1103/PhysRevLett.81.2152 | **Control:** a real DOI paired with the wrong (Bužek–Hillery) title in RT10. | metadata ✔ |
| doi:10.1103/PhysRevLett.130.999999 | **Control:** fabricated. Crossref returned HTTP 404 (2026-10-10T12:08:23Z). The authors "Fictitious & Placeholder" are invented and labelled as such. | — |

The R0 manifest also lists D. Dieks (1982), S. Massar & S. Popescu (1995) and Scarani et al. (2005) with metadata only. The app does not use them to support any claim.

## Mathematical results, and where they come from

| Result | Origin | Status |
|---|---|---|
| No-cloning theorem | Literature (Wootters & Zurek 1982, title-level) | Established in the literature. **Not** derived from or proved by any run. |
| 5/6 optimum for deterministic, symmetric, universal 1→2 qubit cloning | Literature (Bruß et al. 1998, abstract-level; Gisin & Massar 1997) | Established in the literature. Not re-derived here. |
| This circuit gives F_A = F_B = 5/6 and F_AB = 2/3 for every input | Exact calculation (Qiskit Statevector; stdlib verifiers; `scripts/exact_reference.py`) | Exact computation for this circuit. Says nothing about optimality. |

## Redistribution notes

- **arXiv metadata, abstracts included,** is available under CC0 1.0 (arXiv API Terms of Use). `evidence/raw/arxiv.xml` is redistributed on that basis.
- **Crossref bibliographic metadata** (titles, authors, identifiers) is factual and freely reusable.
  - The Crossref record for Deutsch & Jozsa (1992) contained a publisher-deposited abstract. In the public snapshot that one field is removed (see `evidence/README.md`).
- **Short quotations** from abstracts are reproduced with full attribution for scholarly comment.
- **No publisher full text or PDF** is included.
