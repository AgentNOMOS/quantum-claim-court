"""UQCC-R1 tests: extracted-ZIP run with a mock injected backend, verifier, red team."""
import json
import pathlib
import re
import subprocess
import sys
import textwrap
import zipfile

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "qollab_r1"))

from uqcc_r1 import app, circuit, claims, interpret  # noqa: E402
from uqcc_r1.sources_manifest import MANIFEST_TEXT  # noqa: E402

sys.path.insert(0, str(ROOT / "scripts"))
import build_r1_zip  # noqa: E402

MANIFEST = json.loads(MANIFEST_TEXT)

HARNESS = textwrap.dedent('''
    import json, runpy, sys
    from qiskit import QuantumCircuit
    from qiskit.providers.basic_provider import BasicSimulator

    MODE = sys.argv[2]
    CALLS = []

    class _Res:
        def __init__(self, counts, shots):
            self._c, self.results = counts, [type("R", (), {"shots": shots})()]
        def get_counts(self):
            return self._c

    class _Job:
        def __init__(self, r): self._r = r
        def result(self): return self._r

    class MockInjectedBackend:
        """Stands in for Qollab's injected backend; delegates to a real BasicSimulator."""
        def __init__(self, name="basic_simulator"):
            self._real, self.name = BasicSimulator(), name
        @property
        def target(self):
            if MODE == "no_cry":
                from qiskit.transpiler import Target
                from qiskit.circuit.library import RYGate, RZGate, CXGate, Measure
                from qiskit.circuit import Parameter
                t = Target(num_qubits=3)
                t.add_instruction(RYGate(Parameter("a"))); t.add_instruction(RZGate(Parameter("b")))
                t.add_instruction(CXGate()); t.add_instruction(Measure())
                return t
            return self._real.target
        def run(self, run_input, **kw):
            CALLS.append({"type": type(run_input).__name__, "kw": sorted(kw), "shots": kw.get("shots")})
            if MODE == "raise":
                raise RuntimeError("simulated provider failure")
            if MODE == "fake_perfect":
                return _Job(_Res({"00": 2000}, 2000))
            if MODE == "short":
                return _Job(_Res({"00": 1999}, 1999))
            if MODE == "badkey":
                return _Job(_Res({"000": 2000}, 2000))
            return self._real.run(run_input, seed_simulator=1234, **kw)   # harness-only seed

    g = {}
    if MODE != "no_backend":
        g["backend"] = MockInjectedBackend("ionq_simulator" if MODE == "ionq" else "basic_simulator")
    sys.path.insert(0, sys.argv[1])
    code = 0
    try:
        runpy.run_path(sys.argv[1] + "/main.py", init_globals=g, run_name="__main__")
    except SystemExit as e:
        print(e, file=sys.stderr); code = 3
    except Exception as e:
        print("ERROR", type(e).__name__, e, file=sys.stderr); code = 4
    print("HARNESS_CALLS=" + json.dumps(CALLS), file=sys.stderr)
    sys.exit(code)
''')


@pytest.fixture(scope="module")
def pkg(tmp_path_factory):
    d = tmp_path_factory.mktemp("zip")
    zp, _ = build_r1_zip.build(d / "uqcc_r1.zip")
    out = d / "x"
    with zipfile.ZipFile(zp) as z:
        assert sorted(z.namelist()) == sorted(build_r1_zip.FILES)
        z.extractall(out)
    (d / "harness.py").write_text(HARNESS)
    return out


def run_pkg(pkg, mode):
    r = subprocess.run([sys.executable, str(pkg.parent / "harness.py"), str(pkg), mode],
                       capture_output=True, text=True, cwd=str(pkg))
    calls = json.loads(re.search(r"HARNESS_CALLS=(.*)", r.stderr).group(1))
    return r, calls


def verify(pkg, text, tmp_path):
    f = tmp_path / "console.txt"
    f.write_bytes(text.encode("utf-8") if isinstance(text, str) else text)
    return subprocess.run([sys.executable, "-I", str(pkg / "verifier/verify_uqcc_r1.py"), str(f), str(pkg)],
                          capture_output=True, text=True)


@pytest.fixture(scope="module")
def good(pkg):
    r, calls = run_pkg(pkg, "ok")
    assert r.returncode == 0, r.stderr
    return r.stdout, calls


# ---- R0 science preserved ----

def test_r1_circuit_identical_to_r0():
    sys.path.insert(0, str(ROOT))
    from uqcc import circuits as r0
    a, b = circuit.build(), r0.bh_cloner(1.1, 0.7)
    assert [(i.operation.name, [float(p) for p in i.operation.params], [a.find_bit(q).index for q in i.qubits])
            for i in a.data] == \
           [(i.operation.name, [float(p) for p in i.operation.params], [b.find_bit(q).index for q in i.qubits])
            for i in b.data]


def test_circuit_metrics():
    m = circuit.metrics(circuit.build())
    assert m == {"qubits": 3, "clbits": 2, "depth": 9, "size": 15,
                 "ops": {"cry": 1, "cx": 4, "measure": 2, "ry": 5, "rz": 3}}


# ---- extracted ZIP with mock injected backend ----

def test_zip_run_one_bare_circuit_one_job(good):
    _, calls = good
    assert calls == [{"type": "QuantumCircuit", "kw": ["shots"], "shots": 2000}]


def test_zip_run_verifies(good, pkg, tmp_path):
    v = verify(pkg, good[0], tmp_path)
    assert v.returncode == 0, v.stdout
    assert json.loads(v.stdout)["status"] == "VERIFIED_CONSISTENT"


def test_windows_crlf_paste_still_verifies(good, pkg, tmp_path):
    assert verify(pkg, good[0].replace("\n", "\r\n"), tmp_path).returncode == 0


@pytest.mark.parametrize("mode", ["ionq", "no_backend", "no_cry"])
def test_refusals_submit_zero_jobs(pkg, mode):
    r, calls = run_pkg(pkg, mode)
    assert r.returncode == 3 and calls == [] and "REFUSED" in r.stderr


def test_provider_failure_no_retry(pkg):
    r, calls = run_pkg(pkg, "raise")
    assert r.returncode == 4 and len(calls) == 1


def test_fabricated_perfect_counts_disputed(pkg, tmp_path):
    r, calls = run_pkg(pkg, "fake_perfect")
    assert len(calls) == 1 and re.search(r"C1\s+DISPUTED", r.stdout)
    v = verify(pkg, r.stdout, tmp_path)
    assert v.returncode == 2 and json.loads(v.stdout)["status"] == "VERIFIED_INCONSISTENT"


@pytest.mark.parametrize("mode", ["short", "badkey"])
def test_corrupt_measurement_insufficient_and_verifier_fails(pkg, tmp_path, mode):
    r, _ = run_pkg(pkg, mode)
    assert re.search(r"C1\s+INSUFFICIENT", r.stdout) and "MEASUREMENT INVALID" in r.stdout
    assert verify(pkg, r.stdout, tmp_path).returncode == 1


# ---- verifier integrity ----

def _evidence_line(stdout):
    return stdout.split("UQCC_R1_EVIDENCE_BEGIN\n")[1].split("\nUQCC_R1_EVIDENCE_END")[0]


def test_tampered_count_fails(good, pkg, tmp_path):
    line = _evidence_line(good[0])
    ev = json.loads(line)
    k = next(iter(ev["counts"]))
    bad = good[0].replace(f'"counts":{{"{k}":{ev["counts"][k]}', f'"counts":{{"{k}":{ev["counts"][k] + 1}', 1)
    assert bad != good[0] and verify(pkg, bad, tmp_path).returncode == 1


def test_reserialised_evidence_is_rejected_not_rehashed(good, pkg, tmp_path):
    line = _evidence_line(good[0])
    pretty = json.dumps(json.loads(line))          # default separators -> different bytes
    assert verify(pkg, good[0].replace(line, pretty), tmp_path).returncode == 1


def test_evidence_text_is_canonical_and_float_free(good):
    line = _evidence_line(good[0])
    obj = json.loads(line)
    assert app.canonical(obj) == line

    def walk(x):
        if isinstance(x, float):
            raise AssertionError(x)
        for v in (x.values() if isinstance(x, dict) else x if isinstance(x, list) else []):
            walk(v)
    walk(obj)


def test_missing_markers_fail(pkg, tmp_path):
    v = verify(pkg, "no evidence here", tmp_path)
    assert v.returncode == 1 and "INSUFFICIENT" in v.stdout


def test_wrapped_line_fails(good, pkg, tmp_path):
    line = _evidence_line(good[0])
    assert verify(pkg, good[0].replace(line, line[:500] + "\n" + line[500:]), tmp_path).returncode == 1


def test_forged_supported_verdict_fails(good, pkg, tmp_path):
    line = _evidence_line(good[0])
    ev = json.loads(line)
    for d in ev["decisions"]:
        if d["id"] == "RT1":
            d["verdict"] = "SUPPORTED"
    new = app.canonical(ev)
    import hashlib
    h = hashlib.sha256(new.encode()).hexdigest()
    forged = re.sub(r"UQCC_R1_EVIDENCE_SHA256=\w+", "UQCC_R1_EVIDENCE_SHA256=" + h, good[0].replace(line, new))
    v = verify(pkg, forged, tmp_path)
    assert v.returncode == 1 and "RT1" in v.stdout


def test_edited_manifest_fails(good, pkg, tmp_path):
    p = pkg / "uqcc_r1/sources_manifest.py"
    orig = p.read_text()
    try:
        p.write_text(orig.replace("5/6", "9/10", 1))
        assert verify(pkg, good[0], tmp_path).returncode == 1
    finally:
        p.write_text(orig)


# ---- red team (in-app decisions) ----

EXPECTED = {"C2": "SUPPORTED", "C3": "SUPPORTED", "C4": "SUPPORTED", "RT1": "BLOCK", "RT2": "BLOCK",
            "RT3": "REWRITE", "RT4": "BLOCK", "RT5": "REWRITE", "RT6": "BLOCK", "RT7": "INSUFFICIENT",
            "RT8": "REWRITE", "RT9": "REWRITE", "RT10": "BLOCK"}


def _meas(counts):
    return interpret.interpret(counts, 2000)


def test_red_team_verdicts():
    got = {d["id"]: d["verdict"] for d in claims.decide_all(MANIFEST, _meas({"00": 1333, "01": 334, "10": 333}))}
    for k, v in EXPECTED.items():
        assert got[k] == v, k
    assert got["C1"] == "SUPPORTED"


@pytest.mark.parametrize("meas", [None, {"valid": False, "errors": ["corrupted"]}])
def test_missing_or_corrupt_measurement_is_insufficient(meas):
    c1 = next(c for c in claims.CLAIMS if c["id"] == "C1")
    d = claims.decide(c1, MANIFEST, meas)
    assert d["verdict"] == "INSUFFICIENT" and d["evidence"]["measurement"].startswith("MISSING_OR_INVALID")


def test_evidence_classes_kept_separate():
    ds = {d["id"]: d for d in claims.decide_all(MANIFEST, _meas({"00": 1333, "01": 334, "10": 333}))}
    assert ds["C1"]["evidence"]["literature"] == "NOT_REQUIRED"
    assert ds["C1"]["evidence"]["measurement"].startswith("SIMULATOR_MEASUREMENT_OBSERVED")
    assert "exact_computation" in ds["C1"]["evidence"]["mathematics"]
    assert "literature" in ds["C2"]["evidence"]["mathematics"] and ds["C2"]["evidence"]["measurement"] == "NOT_USED"
    assert "TITLE_TEXT" in ds["C2"]["evidence"]["literature"]
    assert "ABSTRACT_QUOTE" in ds["C3"]["evidence"]["literature"]
    assert ds["RT1"]["evidence"]["measurement"].startswith("SIMULATOR_MEASUREMENT_OBSERVED: clone CIs exclude F=1")


def test_interval_with_5_6_does_not_prove_optimality():
    c = next(c for c in claims.CLAIMS if c["id"] == "RT8")
    assert claims.decide(c, MANIFEST, _meas({"00": 1333, "01": 334, "10": 333}))["verdict"] == "REWRITE"


# ---- manifest accuracy ----

@pytest.mark.parametrize("doi,title,year,abstract", [
    ("10.1038/299802a0", "A single quantum cannot be cloned", 1982, False),
    ("10.1103/physreva.54.1844", "Quantum copying: Beyond the no-cloning theorem", 1996, True),
    ("10.1103/physreva.57.2368", "Optimal universal and state-dependent quantum cloning", 1998, True),
])
def test_required_sources_accurate(doi, title, year, abstract):
    s = next(s for s in MANIFEST["sources"] if s["doi"] == doi)
    assert (s["title"], s["year"]) == (title, year)
    assert s["levels"]["SOURCE_METADATA_VERIFIED"]["value"] is True
    assert s["levels"]["SOURCE_ABSTRACT_CHECKED"]["value"] is abstract
    assert s["levels"]["SOURCE_TEXT_VERIFIED"]["value"] is False


def test_bh96_not_credited_with_5_6():
    s = next(s for s in MANIFEST["sources"] if s["id"] == "BH96")
    assert all("5_6" not in st["statement"] for st in s["statements"])


def test_scope_of_5_6_is_stated():
    m = next(m for m in MANIFEST["math_results"] if m["id"] == "M_OPT_5_6")
    for w in ("deterministic", "symmetric", "universal", "1->2"):
        assert w in m["statement"]
    assert "NOT" in m["note"] and "asymmetric" in m["note"] and "probabilistic" in m["note"]


# ---- static guarantees ----

def test_package_has_no_fallback_or_network():
    src = "".join(p.read_text() for p in (ROOT / "qollab_r1").rglob("*.py"))
    assert src.count("backend.run(") == 1
    assert "BasicSimulator(" not in src and "Aer" not in src
    for bad in ("urllib", "requests", "http.client", "socket"):
        assert bad not in src


def test_verifier_is_stdlib_only():
    src = (ROOT / "qollab_r1/verifier/verify_uqcc_r1.py").read_text()
    assert "qiskit" not in src.replace("never imports Qiskit", "") and "uqcc_r1 import" not in src


def test_false_dispute_rate_is_low():
    from qiskit.providers.basic_provider import BasicSimulator
    qc, b, n, bad = circuit.build(), BasicSimulator(), 400, 0
    for s in range(n):
        m = interpret.interpret(b.run(qc, shots=2000, seed_simulator=10_000 + s).result().get_counts(), 2000)
        bad += not all(o["contains_expected"] for o in m["observables"].values())
    assert bad / n < 0.04
