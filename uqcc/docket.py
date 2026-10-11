"""The R0 docket: 16 structured claims, the circuits that produce their evidence, and the gate.

Claims are pre-structured (no NLP in R0). Each records the verdict the design intends, so the
tests and the independent verifier can check the gate did not drift.
C07 uses a deliberately FICTITIOUS citation (invented authors, Crossref 404) as a negative control.
"""
import json
import math

from . import circuits, experiment, gate

BH = {"doi": "10.1103/PhysRevA.56.3446", "title": "Quantum copying: A network", "year": 1997,
      "first_author": "Bužek"}
BRUSS = {"doi": "10.1103/PhysRevA.57.2368", "title": "Optimal universal and state-dependent quantum cloning",
         "year": 1998, "first_author": "Bruß"}
WZ = {"doi": "10.1038/299802a0", "title": "A single quantum cannot be cloned", "year": 1982,
      "first_author": "Wootters"}
MP = {"doi": "10.1103/PhysRevLett.74.1259", "title": "Optimal Extraction of Information from Finite Quantum Ensembles",
      "year": 1995, "first_author": "Massar"}
DJ = {"doi": "10.1098/rspa.1992.0167", "title": "Rapid solution of problems by quantum computation",
      "year": 1992, "first_author": "Deutsch"}
FICTITIOUS = {"doi": "10.1103/PhysRevLett.130.999999", "title": "Perfect quantum cloning on trapped ions",
              "year": 2023, "first_author": "Fictitious"}
BH96_TITLE_WRONG_DOI = {"doi": "10.1103/PhysRevLett.81.2152", "title": "Quantum copying: Beyond the no-cloning theorem",
                        "year": 1996, "first_author": "Bužek"}

ALL = list(circuits.STATES)
FIVE_SIXTHS = 5 / 6

CLAIMS = [
    dict(id="C01", expected="SUPPORTED", kind="quantitative", proposition="P_UQCM_GATE_NETWORK",
         text="On an ideal noiseless simulator, the Bužek–Braunstein–Hillery–Bruß gate network produced two clones "
              "whose single-copy fidelity is consistent with 5/6 (±0.01) on all 8 tested input states.",
         citations=[BH], panel="BH_FULL", measurement_key=["A", "B"], claimed_value=FIVE_SIXTHS, tolerance=0.01,
         platform="ideal_simulator"),
    dict(id="C02", expected="SUPPORTED", kind="attribution", proposition="P_UQCM_OPTIMAL_5_6",
         text="Bruß et al. (1998) showed that 5/6 is the maximal single-copy fidelity of a universal 1→2 qubit cloner.",
         citations=[BRUSS]),
    dict(id="C03", expected="SUPPORTED", kind="quantitative", proposition="P_CNOT_COPIES_BASIS_STATES",
         text="A CNOT copies the known computational basis states |0⟩ and |1⟩ with single-copy fidelity 1.",
         needs_literature=False, panel="CNOT_FULL", measurement_key=["A", "B"], claimed_value=1.0,
         tolerance=0.001, states=["Z+", "Z-"], platform="ideal_simulator"),
    dict(id="C04", expected="BLOCK", kind="theorem", proposition="P_PERFECT_UNIVERSAL_CLONING",
         text="A CNOT gate clones arbitrary unknown qubit states.",
         panel="CNOT_FULL", measurement_key=["A", "B"], claimed_value=1.0, tolerance=0.001,
         rewrite_hint="A CNOT copies |0⟩ and |1⟩; on |+⟩ each output has fidelity 1/2 (measured).",
         platform="ideal_simulator"),
    dict(id="C05", expected="REWRITE", kind="theorem", proposition="P_NOCLONE_UNIVERSAL", verb="proves",
         basis="own_experiment", needs_literature=False,
         text="Our simulator experiment proves the no-cloning theorem.",
         rewrite_hint="Our measurements are consistent with the no-cloning theorem (Wootters & Zurek 1982); "
                      "a finite experiment cannot prove it."),
    dict(id="C06", expected="DISPUTED", kind="attribution", proposition="P_NO_APPROXIMATE_CLONING",
         text="Wootters & Zurek (1982) showed that no device can copy an unknown quantum state, even approximately.",
         citations=[WZ],
         rewrite_hint="Wootters & Zurek (1982) rule out PERFECT cloning; approximate universal cloning exists "
                      "(Bužek & Hillery 1996) with optimal single-copy fidelity 5/6 (Bruß et al. 1998)."),
    dict(id="C07", expected="BLOCK", kind="attribution", proposition="P_UQCM_HARDWARE_5_6",
         text="[NEGATIVE CONTROL, fictitious citation] 'Fictitious & Placeholder (2023)' measured 5/6 cloning "
              "fidelity on trapped ions.",
         citations=[FICTITIOUS]),
    dict(id="C08", expected="BLOCK", kind="attribution", proposition="P_UQCM_EXISTS_INPUT_INDEPENDENT",
         text="A universal copier with input-independent quality exists (Bužek & Hillery, 'Quantum copying: "
              "Beyond the no-cloning theorem', doi:10.1103/PhysRevLett.81.2152).",
         citations=[BH96_TITLE_WRONG_DOI]),
    dict(id="C09", expected="REWRITE", kind="attribution", proposition="P_UQCM_OPTIMAL_5_6",
         text="The optimal universal 1→2 cloning fidelity is 5/6 (Deutsch & Jozsa 1992).",
         citations=[DJ]),
    dict(id="C10", expected="INSUFFICIENT", kind="quantitative", proposition="P_UQCM_GATE_NETWORK",
         text="Same as C01, but measured with only 60 shots per state.",
         citations=[BH], panel="BH_SMALL", measurement_key=["A", "B"], claimed_value=FIVE_SIXTHS,
         tolerance=0.01, platform="ideal_simulator"),
    dict(id="C11", expected="INSUFFICIENT", kind="quantitative", proposition="P_UQCM_GATE_NETWORK",
         text="The Bužek–Braunstein–Hillery–Bruß network achieves 5/6 single-copy fidelity on IonQ hardware.",
         citations=[BH], measurement_key=["A", "B"], claimed_value=FIVE_SIXTHS, tolerance=0.01,
         platform="ionq_hardware"),
    dict(id="C12", expected="INSUFFICIENT", kind="attribution", proposition="P_MEASURE_PREPARE_2_3",
         text="A 5/6 cloner beats the optimal measure-and-prepare fidelity of 2/3 (Massar & Popescu 1995).",
         citations=[MP]),
    dict(id="C13", expected="REWRITE", kind="provenance", proposition="P_MANIFEST_AUTHENTIC",
         authenticity_basis="sha256", needs_literature=False,
         text="Our source manifest is authentic because its SHA-256 hash matches."),
    dict(id="C14", expected="BLOCK", kind="quantitative", proposition="P_UQCM_FIDELITY_ABOVE_5_6",
         text="Our improved universal 1→2 cloner reaches single-copy fidelity 0.9 for every input."),
    dict(id="C15", expected="DISPUTED", kind="quantitative", proposition="P_UQCM_GATE_NETWORK",
         text="Each clone of the Bužek–Braunstein–Hillery–Bruß network has single-copy fidelity 2/3.",
         citations=[BH], panel="BH_FULL", measurement_key=["A", "B"], claimed_value=2 / 3, tolerance=0.01,
         platform="ideal_simulator",
         rewrite_hint="2/3 is the JOINT two-copy fidelity ⟨ψψ|ρ_AB|ψψ⟩; each single copy has 5/6."),
    dict(id="C16", expected="SUPPORTED", kind="quantitative", proposition="P_BH_JOINT_2_3",
         text="In our circuit the two clones jointly match |ψψ⟩ with probability 2/3 (±0.01) on all 8 tested inputs.",
         needs_literature=False, panel="BH_FULL", measurement_key="AB", claimed_value=2 / 3, tolerance=0.01,
         platform="ideal_simulator"),
]

PANELS = {
    "BH_FULL": (circuits.bh_cloner, 20000, 1000),
    "BH_SMALL": (circuits.bh_cloner, 60, 5000),
    "CNOT_FULL": (circuits.cnot_copier, 20000, 2000),
}
BUILDERS = {"BH_FULL": circuits.bh_cloner, "BH_SMALL": circuits.bh_cloner, "CNOT_FULL": circuits.cnot_copier}


def math_evidence(claim, panels):
    if "claimed_value" not in claim or "panel" not in claim:
        return None
    keys = claim["measurement_key"]
    keys = [keys] if isinstance(keys, str) else keys
    rows = [r for r in panels[claim["panel"]]["rows"] if r["state"] in claim.get("states", ALL)]
    exact = sorted({round(r["exact"][k], 12) for r in rows for k in keys})
    agrees = all(math.isclose(v, claim["claimed_value"], abs_tol=1e-9) for v in exact)
    return {"status": "AGREES" if agrees else "CONTRADICTS", "exact_values": exact}


def run_all():
    panels = {name: experiment.measure_panel(b, shots, seed) for name, (b, shots, seed) in PANELS.items()}
    manifest = gate.load_manifest()
    decisions = []
    for c in CLAIMS:
        ev = {"measurement": panels.get(c.get("panel")), "math": math_evidence(c, panels)}
        d = gate.decide(c, manifest, ev)
        d["text"] = c["text"]
        d["expected"] = c["expected"]
        decisions.append(d)
    return panels, decisions


def export_circuit(qc):
    """Gate list for the independent verifier (it never imports Qiskit)."""
    ops = []
    for inst in qc.data:
        ops.append({"name": inst.operation.name,
                    "qubits": [qc.find_bit(q).index for q in inst.qubits],
                    "clbits": [qc.find_bit(c).index for c in inst.clbits],
                    "params": [float(p) for p in inst.operation.params]})
    return {"num_qubits": qc.num_qubits, "ops": ops}


def main(out_dir="results"):
    import hashlib
    import pathlib
    out = pathlib.Path(out_dir)
    out.mkdir(exist_ok=True)
    panels, decisions = run_all()
    stats = {"flagship_bh_cloner": experiment.circuit_stats(circuits.flagship_circuit()),
             "cnot_copier": experiment.circuit_stats(circuits.cnot_copier(1.1, 0.7))}
    manifest_sha = hashlib.sha256(gate.MANIFEST_PATH.read_bytes()).hexdigest()
    for name, panel in panels.items():
        for r in panel["rows"]:
            r["circuit"] = export_circuit(BUILDERS[name](r["theta"], r["phi"]))
    (out / "panels.json").write_text(json.dumps(panels, indent=1, sort_keys=True))
    (out / "decisions.json").write_text(json.dumps(
        {"manifest_sha256": manifest_sha, "circuit_stats": stats, "decisions": decisions},
        indent=1, sort_keys=True, ensure_ascii=False))
    for d in decisions:
        flag = "ok" if d["verdict"] == d["expected"] else "MISMATCH"
        print(f"{d['claim_id']} {d['verdict']:<12} [{flag}] lit={d['evidence']['literature']} | "
              f"math={d['evidence']['mathematics']} | meas={d['evidence']['measurement']}")
    return decisions


if __name__ == "__main__":
    main()
