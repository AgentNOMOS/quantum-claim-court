import copy
import json
import math
import pathlib
import shutil
import subprocess
import sys

import pytest
from qiskit import QuantumCircuit

from uqcc import circuits, docket, experiment, gate

ROOT = pathlib.Path(__file__).resolve().parent.parent


@pytest.fixture(scope="module")
def run():
    return docket.run_all()


@pytest.fixture(scope="module")
def manifest():
    return gate.load_manifest()


# --- circuits / mathematics -------------------------------------------------

@pytest.mark.parametrize("label", list(circuits.STATES))
def test_bh_exact_fidelities_are_input_independent(label):
    th, ph = circuits.STATES[label]
    f = experiment.exact_fidelities(circuits.bh_cloner, th, ph)
    assert math.isclose(f["A"], 5 / 6, abs_tol=1e-12)
    assert math.isclose(f["B"], 5 / 6, abs_tol=1e-12)
    assert math.isclose(f["AB"], 2 / 3, abs_tol=1e-12)


def test_cnot_copier_is_state_dependent():
    f0 = experiment.exact_fidelities(circuits.cnot_copier, 0.0, 0.0)
    fp = experiment.exact_fidelities(circuits.cnot_copier, math.pi / 2, 0.0)
    assert f0["A"] == pytest.approx(1.0) and fp["A"] == pytest.approx(0.5)


def test_cnot_copier_average_fidelity_is_two_thirds():
    # Bloch-sphere average of (1+z^2)/2 = 2/3; numeric quadrature over theta.
    n = 2000
    tot = 0.0
    for i in range(n):
        th = (i + 0.5) * math.pi / n
        tot += experiment.exact_fidelities(circuits.cnot_copier, th, 0.3)["A"] * math.sin(th) * math.pi / n / 2
    assert tot == pytest.approx(2 / 3, abs=1e-6)


def test_flagship_is_one_bare_circuit_3q():
    qc = circuits.flagship_circuit()
    assert isinstance(qc, QuantumCircuit)
    s = experiment.circuit_stats(qc)
    assert s["qubits"] == 3 and s["clbits"] == 2
    assert s["ops"]["cx"] == 4 and s["ops"]["cry"] == 1


def test_measurement_is_real_shot_data(run):
    panels, _ = run
    for p in panels.values():
        for r in p["rows"]:
            assert sum(r["counts"].values()) == r["shots"]
    # finite-shot noise exists: not all BH estimates equal 5/6 exactly
    est = [r["measured"]["A"]["f_hat"] for r in panels["BH_FULL"]["rows"]]
    assert any(abs(e - 5 / 6) > 1e-6 for e in est)


def test_seeded_runs_reproducible():
    a = experiment.run(circuits.bh_cloner, 1.1, 0.7, 500, 42)
    b = experiment.run(circuits.bh_cloner, 1.1, 0.7, 500, 42)
    assert a == b


# --- gate ------------------------------------------------------------------

def test_docket_all_expected(run):
    _, decisions = run
    assert len(decisions) == 16
    assert {d["claim_id"]: d["verdict"] for d in decisions} == {c["id"]: c["expected"] for c in docket.CLAIMS}


def test_all_five_verdicts_exercised(run):
    assert {d["verdict"] for d in run[1]} == {"SUPPORTED", "DISPUTED", "INSUFFICIENT", "REWRITE", "BLOCK"}


def test_three_evidence_classes_reported_separately(run):
    for d in run[1]:
        assert set(d["evidence"]) == {"literature", "mathematics", "measurement"}


def _claim(cid):
    return copy.deepcopy(next(c for c in docket.CLAIMS if c["id"] == cid))


def test_reference_alone_cannot_support_new_experimental_result(manifest):
    c = _claim("C01")
    d = gate.decide(c, manifest, {"measurement": None, "math": None})
    assert d["verdict"] == "INSUFFICIENT" and d["evidence"]["literature"].startswith("SUPPORTED")


def test_finite_experiment_cannot_prove_universal_theorem(manifest):
    d = gate.decide(_claim("C05"), manifest, {})
    assert d["verdict"] == "REWRITE" and "cannot prove" in d["reason"]


def test_hash_is_not_authentication(manifest):
    d = gate.decide(_claim("C13"), manifest, {})
    assert d["verdict"] == "REWRITE" and "does not authenticate" in d["reason"]


def test_unknown_doi_is_insufficient_not_block(manifest):
    c = _claim("C02")
    c["citations"] = [{"doi": "10.9999/not-in-manifest", "title": "x"}]
    assert gate.decide(c, manifest, {})["verdict"] == "INSUFFICIENT"


def test_wrong_year_is_mismatch(manifest):
    c = _claim("C02")
    c["citations"][0]["year"] = 1997
    assert gate.decide(c, manifest, {})["verdict"] == "BLOCK"


def test_fabricated_citation_blocks_even_for_true_proposition(manifest):
    c = _claim("C02")
    c["citations"] = c["citations"] + [docket.FICTITIOUS]
    assert gate.decide(c, manifest, {})["verdict"] == "BLOCK"


def test_contradiction_beats_supporting_measurement(manifest, run):
    panels, _ = run
    c = _claim("C14")
    c.update(panel="BH_FULL", measurement_key=["A"], claimed_value=5 / 6, tolerance=0.01, citations=[docket.BRUSS])
    assert gate.decide(c, manifest, {"measurement": panels["BH_FULL"], "math": None})["verdict"] == "BLOCK"


def test_gate_is_deterministic(run, manifest):
    panels, decisions = run
    again = [gate.decide(c, manifest, {"measurement": panels.get(c.get("panel")),
                                       "math": docket.math_evidence(c, panels)}) for c in docket.CLAIMS]
    assert [d["verdict"] for d in again] == [d["verdict"] for d in decisions]


# --- manifest ----------------------------------------------------------------

def test_manifest_metadata_matches_raw_crossref(manifest):
    for s in manifest["sources"]:
        raw = json.loads((ROOT / s["raw_file"]).read_text())["message"]
        assert raw["DOI"].lower() == s["doi"]
        assert " ".join(raw["title"][0].split()) == s["title"]


def test_strong_propositions_have_quotes_in_primary_text(manifest):
    arxiv = (ROOT / "evidence/raw/arxiv.xml").read_text()
    arxiv = " ".join(arxiv.split())
    for s in manifest["sources"]:
        for p in s["propositions"]:
            if p["basis"] == "ABSTRACT_TEXT":
                assert p["quote"] in arxiv
            if p["basis"] == "TITLE_TEXT":
                assert p["quote"].lower() == s["title"].lower()


def test_manifest_declares_it_is_frozen(manifest):
    assert "Not a live academic search" in manifest["notice"]


def test_no_network_imports_in_runtime():
    for f in (ROOT / "uqcc").glob("*.py"):
        src = f.read_text()
        for bad in ("urllib", "requests", "http.client", "socket"):
            assert bad not in src, (f, bad)


# --- independent verifier ----------------------------------------------------

def _verify(root):
    return subprocess.run([sys.executable, "-I", str(ROOT / "verifier/verify_uqcc.py"), str(root)],
                          capture_output=True, text=True)


@pytest.fixture()
def results_copy(tmp_path):
    docket.main(out_dir=str(ROOT / "results"))
    for d in ("results", "uqcc", "evidence"):
        shutil.copytree(ROOT / d, tmp_path / d)
    return tmp_path


def test_verifier_passes(results_copy):
    r = _verify(results_copy)
    assert r.returncode == 0, r.stdout


def test_verifier_catches_tampered_counts(results_copy):
    p = results_copy / "results/panels.json"
    d = json.loads(p.read_text())
    row = d["BH_FULL"]["rows"][0]
    row["counts"]["00"] += 2000
    p.write_text(json.dumps(d))
    assert _verify(results_copy).returncode == 1


def test_verifier_catches_fabricated_precomputed_result(results_copy):
    p = results_copy / "results/panels.json"
    d = json.loads(p.read_text())
    row = d["BH_FULL"]["rows"][3]
    n = row["shots"]
    hit = round(n * 0.95)                          # "perfect-ish cloning", inconsistent with physics
    row["counts"] = {"00": hit, "11": n - hit}
    for k in ("A", "B", "AB"):
        row["measured"][k]["hits"] = hit
    p.write_text(json.dumps(d))
    assert _verify(results_copy).returncode == 1


def test_verifier_catches_edited_manifest(results_copy):
    p = results_copy / "uqcc/sources.json"
    p.write_text(p.read_text().replace("5/6", "9/10", 1))
    assert _verify(results_copy).returncode == 1


def test_verifier_catches_verdict_drift(results_copy):
    p = results_copy / "results/decisions.json"
    d = json.loads(p.read_text())
    d["decisions"][3]["verdict"] = "SUPPORTED"
    p.write_text(json.dumps(d))
    assert _verify(results_copy).returncode == 1
