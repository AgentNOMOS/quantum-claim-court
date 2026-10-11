"""UQCC-R3b Python tests: backend policy (positive identification, fail closed), one-job contract,
BasicSimulator regression, frozen-science identity, ideal vs noise-model interpretation, R3b verifier, ZIP.

IonQ backends here are SYNTHETIC stand-ins (dev/ionq_mocks.py). Nothing in this file contacts IonQ or Qollab,
and nothing here is evidence of a real IonQ run.
"""
import contextlib
import difflib
import hashlib
import inspect
import io
import json
import pathlib
import subprocess
import sys
import types
import zipfile

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "dev"))
import build_r2_zip  # noqa: E402
import build_r3b_zip  # noqa: E402
import ionq_mocks  # noqa: E402

STAGE = build_r3b_zip.stage(ROOT / "dev" / "_stage_tests_r3b")
_saved = {m: sys.modules.pop(m) for m in [m for m in sys.modules if m.startswith(("uqcc_r1", "uqcc_app"))]}
sys.path.insert(0, str(STAGE))
from qiskit.providers.basic_provider import BasicSimulator  # noqa: E402

from uqcc_app import backend_policy, court, js_api, runner  # noqa: E402
from uqcc_r1 import app as r1_app, circuit  # noqa: E402
sys.path.remove(str(STAGE))
for m in [m for m in sys.modules if m.startswith(("uqcc_r1", "uqcc_app"))]:
    del sys.modules[m]
sys.modules.update(_saved)            # other test modules keep their own staged packages

PINS = json.loads((ROOT / "scripts/frozen_pins.json").read_text())
THEOREM_CLAIMS = ("C2", "C3", "C4", "RT1", "RT2", "RT3", "RT9")


class Counting(BasicSimulator):
    def __init__(self, counts=None, fail=None, seed=99):
        super().__init__()
        self.calls, self._counts, self._fail, self._seed = [], counts, fail, seed

    def run(self, c, **kw):
        self.calls.append((type(c).__name__, sorted(kw), kw.get("shots")))
        if self._fail:
            raise self._fail
        if self._counts is not None:
            return ionq_mocks._Job(ionq_mocks._Res(self._counts))
        return super().run(c, seed_simulator=self._seed, **kw)


def bridge(backend):
    js_api._reset_for_tests()
    with contextlib.redirect_stdout(io.StringIO()):
        text = js_api.run_court(backend)
    return json.loads(text)


def verify(text, tmp_path, name="evidence.txt"):
    f = tmp_path / name
    f.write_bytes(text.encode("utf-8"))
    return subprocess.run([sys.executable, "-I", str(STAGE / "verifier/verify_uqcc_r3b.py"), str(f), str(STAGE)],
                          capture_output=True, text=True)


def calls_of(b):
    return len(b.calls)


# ---------------------------------------------------------------- frozen releases preserved

def test_frozen_r1_files_match_pins_in_r3b_stage():
    for rel, want in PINS["files"].items():
        assert hashlib.sha256((STAGE / rel).read_bytes()).hexdigest() == want, rel


def test_r2_zip_still_rebuilds_byte_identical(tmp_path):
    _, h = build_r2_zip.build(tmp_path / "r2.zip")
    assert h == PINS["zips"]["uqcc_r2_claim_court_app.zip"]


def test_r3b_build_refuses_to_overwrite_frozen_zips():
    for name in ("uqcc_r1_qollab_smoke.zip", "uqcc_r2_claim_court_app.zip"):
        with pytest.raises(SystemExit):
            build_r3b_zip.build(ROOT / "dist" / name)


def test_r3b_zip_is_deterministic_and_has_expected_files(tmp_path):
    p1, h1 = build_r3b_zip.build(tmp_path / "a.zip")
    p2, h2 = build_r3b_zip.build(tmp_path / "b.zip")
    assert h1 == h2
    names = zipfile.ZipFile(p1).namelist()
    assert sorted(names) == sorted(build_r3b_zip.FROZEN + build_r3b_zip.APP)
    assert "verifier/verify_uqcc_r2.py" not in names and "uqcc_app/backend_policy.py" in names


# ---------------------------------------------------------------- circuit identity

def test_circuit_is_the_frozen_r1_circuit():
    qc = circuit.build()
    assert [i.operation.name for i in qc.data] == ["ry", "rz", "ry", "ry", "cry", "cx", "cx", "cx", "cx",
                                                   "rz", "ry", "rz", "ry", "measure", "measure"]
    assert qc.num_qubits == 3 and qc.num_clbits == 2
    assert "transpile(" not in inspect.getsource(runner)          # no gate conversion: IonQ accepts these gates


def test_runner_equals_frozen_r1_run_for_basic_simulator():
    """The R3b runner and the frozen uqcc_r1.app.run give byte-identical evidence for the same backend."""
    a, b = Counting(seed=7), Counting(seed=7)
    ev1, t1, h1 = r1_app.run(a)
    ev2, t2, h2, ctx = runner.run(b)
    assert t1 == t2 and h1 == h2
    assert ctx["kind"] == backend_policy.KIND_BASIC and a.calls == b.calls == [("QuantumCircuit", ["shots"], 2000)]


def test_runner_differs_from_frozen_run_only_in_authorization():
    frozen = inspect.getsource(r1_app.run).splitlines()
    mine = inspect.getsource(runner.run).splitlines()
    norm = [ln.split("#")[0].rstrip().replace("r1_app.", "").replace("_result_shots", "_result_shots")
            for ln in mine]
    fro = [ln.split("#")[0].rstrip() for ln in frozen]
    diff = [d for d in difflib.unified_diff(fro, norm, lineterm="", n=0) if d[:1] in "+-" and d[:3] not in ("+++", "---")]
    joined = "\n".join(diff)
    assert "backend.run(qc, shots=SHOTS)" in "\n".join(norm)
    # remaining differences: signature-neutral auth line, return tuple, and nothing about counts/claims/statistics
    for d in diff:
        assert any(k in d for k in ("check_backend", "classify", "return evidence", "backend_identity")), joined


def test_r3b_verifier_measurement_copy_differs_only_in_backend_check():
    frozen = (STAGE / "verifier/verify_uqcc_r1.py").read_text()
    mine = (STAGE / "verifier/verify_uqcc_r3b.py").read_text()
    f_body = frozen[frozen.index("def verify(raw_bytes, pkg):"):frozen.index("\ndef main(argv):")].rstrip().splitlines()
    m_body = mine[mine.index("def verify_measurement("):mine.index("\ndef main(argv):")].rstrip().splitlines()
    diff = [d for d in difflib.ndiff(f_body, m_body) if d[:1] in "+-"]
    assert len(diff) == 4, diff
    assert "def verify(raw_bytes, pkg):" in diff[0] and "verify_measurement(raw_bytes, pkg, backend_ok)" in diff[1]
    assert "backend is BasicSimulator" in diff[2] and "backend_ok(b)" in diff[3]


# ---------------------------------------------------------------- BasicSimulator regression

def test_basic_simulator_regression_one_job_and_both_verifiers(tmp_path):
    b = Counting()
    env = bridge(b)
    assert env["status"] == "ok" and b.calls == [("QuantumCircuit", ["shots"], 2000)]
    ctx = json.loads(env["court_text"])["backend_context"]
    assert ctx["kind"] == "builtin_basic_simulator" and ctx["ideal_reference_applies"] is True
    r = verify(env["export_text"], tmp_path)
    assert r.returncode == 0, r.stdout
    assert json.loads(r.stdout)["challenge_cells_verified"] == 84
    # the measurement block of a BasicSimulator Run still passes the UNCHANGED frozen R1 verifier
    f = tmp_path / "e.txt"
    f.write_text(env["export_text"])
    r1 = subprocess.run([sys.executable, "-I", str(STAGE / "verifier/verify_uqcc_r1.py"), str(f), str(STAGE)],
                        capture_output=True, text=True)
    assert r1.returncode == 0, r1.stdout


def test_second_call_in_same_run_refused_without_job():
    b = Counting()
    bridge(b)
    n = len(b.calls)
    again = json.loads(js_api.run_court(b))           # same Run, no reset
    assert again["status"] == "refused" and len(b.calls) == n
    js_api._reset_for_tests()


# ---------------------------------------------------------------- IonQ free simulator (synthetic)

@pytest.mark.parametrize("noise,ideal", [("ideal", True), ("aria-1", False), ("forte-1", False)])
def test_ionq_simulator_accepted_one_job(noise, ideal, tmp_path):
    b = ionq_mocks.IonQSimulatorBackend(noise_model=noise)
    env = bridge(b)
    assert env["status"] == "ok" and len(b.calls) == 1 and b.calls[0] == {"shots": 2000}
    ctx = json.loads(env["court_text"])["backend_context"]
    assert ctx == {**ctx, "kind": "ionq_remote_simulator", "free_simulator": True, "noise_model": noise,
                   "ideal_reference_applies": ideal}
    assert ctx["mro"][0] == "qiskit_ionq.ionq_backend.IonQSimulatorBackend"
    r = verify(env["export_text"], tmp_path)
    assert r.returncode in (0, 2), r.stdout
    assert json.loads(r.stdout)["backend"]["noise_model"] == noise


def test_ionq_name_variant_with_system_suffix_accepted():
    assert backend_policy.classify(ionq_mocks.IonQSimulatorBackend(name="ionq_simulator.forte-1"))["kind"] == \
        "ionq_remote_simulator"


# ---------------------------------------------------------------- required negative tests (zero jobs each)

def _fake_class(name, module, base=object):
    cls = type(name, (base,), {})
    cls.__module__, cls.__qualname__ = module, name
    return cls


def _qpu_subclass_of_sim():
    cls = type("Weird", (ionq_mocks.IonQSimulatorBackend, ionq_mocks.IonQQPUBackend), {})
    o = cls.__new__(cls)
    ionq_mocks.IonQBackend.__init__(o, "ionq_simulator", True, "ideal")
    return o


NEGATIVE = {
    "ionq_qpu_generic": lambda: ionq_mocks.IonQQPUBackend(name="ionq_qpu"),
    "ionq_qpu_forte_1": lambda: ionq_mocks.IonQQPUBackend(name="ionq_qpu.forte-1"),
    "ionq_qpu_forte_enterprise_1": lambda: ionq_mocks.IonQQPUBackend(name="ionq_qpu.forte-enterprise-1"),
    "credit_backend_named_as_simulator": lambda: ionq_mocks.IonQQPUBackend(name="ionq_simulator"),
    "simulator_class_with_qpu_name": lambda: ionq_mocks.IonQSimulatorBackend(name="ionq_qpu.forte-1"),
    "class_with_both_sim_and_qpu_in_mro": _qpu_subclass_of_sim,
    "duck_typed_name_only": lambda: types.SimpleNamespace(name="ionq_simulator", run=None),
    "sim_class_name_wrong_module": lambda: _fake_class("IonQSimulatorBackend", "not_ionq.backends")(),
    "unknown_backend": lambda: types.SimpleNamespace(name="aer_simulator"),
    "simulator_flag_missing": lambda: _strip(ionq_mocks.IonQSimulatorBackend(), "_simulator"),
    "simulator_flag_false": lambda: _set(ionq_mocks.IonQSimulatorBackend(), "_simulator", False),
    "simulator_flag_truthy_not_true": lambda: _set(ionq_mocks.IonQSimulatorBackend(), "_simulator", 1),
    "noise_model_missing": lambda: _set(ionq_mocks.IonQSimulatorBackend(), "options", types.SimpleNamespace()),
    "noise_model_none": lambda: ionq_mocks.IonQSimulatorBackend(noise_model=None),
    "noise_model_ambiguous": lambda: ionq_mocks.IonQSimulatorBackend(noise_model="forte-1; qpu=true"),
    "name_substring_trick": lambda: ionq_mocks.IonQSimulatorBackend(name="my_ionq_simulator"),
    "name_prefix_trick": lambda: ionq_mocks.IonQSimulatorBackend(name="ionq_simulator_hw"),
    "name_missing": lambda: ionq_mocks.IonQSimulatorBackend(name=None),
    "name_empty": lambda: ionq_mocks.IonQSimulatorBackend(name=""),
    "basic_name_on_qpu_class": lambda: ionq_mocks.IonQQPUBackend(name="basic_simulator"),
}


def _strip(o, attr):
    delattr(o, attr)
    return o


def _set(o, attr, v):
    setattr(o, attr, v)
    return o


@pytest.mark.parametrize("case", sorted(NEGATIVE))
def test_backend_denied_before_any_job(case):
    b = NEGATIVE[case]()
    with pytest.raises(backend_policy.Refused):
        backend_policy.classify(b)
    env = bridge(b)
    assert env["status"] == "refused" and env["job_attempted"] is False and env["live"] is False
    assert "Zero jobs submitted" in env["message"]
    assert getattr(b, "calls", []) == []


def test_no_backend_refused():
    env = bridge(None)
    assert env["status"] == "refused" and env["job_attempted"] is False


def test_unsupported_gate_refused_safely_without_job():
    b = ionq_mocks.IonQSimulatorBackend(noise_model="forte-1", ops=["ry", "rz", "cx", "measure"])   # no cry
    env = bridge(b)
    assert env["status"] == "refused" and "cry" in env["message"] and b.calls == []


@pytest.mark.parametrize("make", [lambda e: Counting(fail=e),
                                  lambda e: ionq_mocks.IonQSimulatorBackend(noise_model="forte-1", fail=e)])
def test_provider_failure_visible_and_not_retried(make):
    b = make(ConnectionError("simulated provider failure"))
    env = bridge(b)
    assert env["status"] == "error" and env["job_attempted"] is True and "simulated provider failure" in env["message"]
    assert len(b.calls) == 1
    again = json.loads(js_api.run_court(b))            # same Run: still no second job
    assert again["status"] == "refused" and len(b.calls) == 1
    js_api._reset_for_tests()


# ---------------------------------------------------------------- invalid evidence never accepted

def _ionq_env():
    return bridge(ionq_mocks.IonQSimulatorBackend(noise_model="forte-1"))


def _rehash(export_text, block, mutate):
    """Tamper with a block and RECOMPUTE its printed SHA (an attacker who knows the format)."""
    lines = export_text.split("\n")
    i = lines.index(f"{block}_BEGIN") + 1
    obj = json.loads(lines[i])
    mutate(obj)
    lines[i] = json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    j = [k for k, ln in enumerate(lines) if ln.startswith(f"{block}_SHA256=")][0]
    lines[j] = f"{block}_SHA256=" + hashlib.sha256(lines[i].encode()).hexdigest()
    return "\n".join(lines)


def test_verifier_rejects_missing_and_tampered_evidence(tmp_path):
    t = _ionq_env()["export_text"]
    cases = {
        "empty": "",
        "no_court_block": t.split("UQCC_R2_COURT_SHA256=")[0],
        "edited_without_rehash": t.replace('"noise_model":"forte-1"', '"noise_model":"ideal"', 1),
        "court_noise_ideal_rehashed": _rehash(t, "UQCC_R2_COURT",
                                              lambda o: o["backend_context"].update(noise_model="ideal")),
        "court_context_removed_rehashed": _rehash(t, "UQCC_R2_COURT", lambda o: o.pop("backend_context")),
        "court_kind_qpu_rehashed": _rehash(t, "UQCC_R2_COURT",
                                           lambda o: o["backend_context"].update(mro=["qiskit_ionq.ionq_backend.IonQQPUBackend"])),
        "court_free_false_rehashed": _rehash(t, "UQCC_R2_COURT",
                                             lambda o: o["backend_context"].update(free_simulator=False)),
        "noisy_reason_swapped_rehashed": _rehash(t, "UQCC_R2_COURT", lambda o: o["value_decisions"][0].update(
            reason=json.loads(bridge(Counting(counts={"00": 1240, "01": 420, "10": 340}))["court_text"])
            ["value_decisions"][0]["reason"])),
    }
    for name, text in cases.items():
        r = verify(text, tmp_path, f"{name}.txt")
        assert r.returncode == 1, (name, r.stdout)
        assert json.loads(r.stdout)["status"] == "FAIL", name


def test_verifier_rejects_qpu_in_measurement_block_even_if_rehashed(tmp_path):
    t = _ionq_env()["export_text"]
    bad = _rehash(t, "UQCC_R1_EVIDENCE", lambda o: o["backend"].update(name="ionq_qpu.forte-1"))
    r = verify(bad, tmp_path)
    assert r.returncode == 1, r.stdout                   # binding and QPU checks both fail closed


# ---------------------------------------------------------------- ideal vs noisy interpretation

def test_noisy_disagreement_not_presented_as_theorem_failure():
    noisy = _ionq_env()
    ideal = bridge(Counting())
    cn, ci = json.loads(noisy["court_text"]), json.loads(ideal["court_text"])
    vn = {d["id"]: d for d in cn["value_decisions"]}
    assert vn["V1"]["verdict"] == "DISPUTED"
    assert vn["V1"]["reason"] == court.NOISY_DISPUTE_REASON and "1.4%" not in vn["V1"]["reason"]
    assert "not evidence against the mathematics or the no-cloning theorem" in vn["V1"]["reason"]
    assert cn["backend_context"]["interpretation"].startswith("Noise-model simulation")
    assert "noise cannot disprove the no-cloning theorem" in cn["backend_context"]["interpretation"]
    # theorem / literature / scope claims are decided identically on the noisy and the ideal run
    dn = {d["id"]: d["verdict"] for d in json.loads(noisy["r1_evidence_text"])["decisions"]}
    di = {d["id"]: d["verdict"] for d in json.loads(ideal["r1_evidence_text"])["decisions"]}
    for cid in THEOREM_CLAIMS:
        assert dn[cid] == di[cid], cid
    assert dn["RT1"] == "BLOCK"                         # perfect cloning still blocked under noise
    # the challenge matrix does not depend on the measurement at all
    assert cn["challenge"]["matrix"] == ci["challenge"]["matrix"]


def test_verdict_rules_unchanged_between_r2_and_r3b():
    """The R3b court differs from the R2 court only by the backend context and the noisy reason text."""
    r2 = (ROOT / "app/uqcc_app/court.py").read_text().splitlines()
    r3b = (ROOT / "app_r3b/uqcc_app/court.py").read_text().splitlines()
    removed = [d[2:] for d in difflib.ndiff(r2, r3b) if d.startswith("- ")]
    assert all(any(k in ln for k in ("UQCC-R2 court addendum", "COURT_SCHEMA", "def decide_value(vc, measurement):",
                                     "def build(", "vdec = [decide_value", 'court = {"schema"')) for ln in removed), removed
    meas = json.loads(_ionq_env()["r1_evidence_text"])["measurement"]
    for vc in court.VALUE_CLAIMS:
        assert court.decide_value(vc, meas, False)["verdict"] == court.decide_value(vc, meas, True)["verdict"]


def test_ideal_ionq_noise_model_keeps_statistical_wording():
    env = bridge(ionq_mocks.IonQSimulatorBackend(noise_model="ideal", counts={"00": 1240, "01": 420, "10": 340}))
    v1 = json.loads(env["court_text"])["value_decisions"][0]
    assert v1["verdict"] == "DISPUTED" and "1.4%" in v1["reason"]


# ---------------------------------------------------------------- UI contract (static)

def test_main_js_single_bridge_call_and_backend_context_rendered():
    js = (ROOT / "app_r3b/main.js").read_text()
    code = "\n".join(ln for ln in js.splitlines() if not ln.strip().startswith("//"))
    assert code.count("callPromising(") == 1 and "R.renderBackend(evidence, court)" in code
    html_ = (ROOT / "app_r3b/index.html").read_text().lower()
    for tag in ("<html", "<head", "<body", "<script"):
        assert tag + " " not in html_ and tag + ">" not in html_
    assert 'id="backend-context"' in html_


def test_r3b_readme_states_hardware_exclusion_and_noise():
    readme = (ROOT / "app_r3b/README.md").read_text()
    assert "IonQ quantum computers (hardware, credits) are always refused" in readme
    assert "noise cannot disprove the no-cloning theorem" in readme
    assert "verify_uqcc_r3b.py" in readme and "This effort is supported by Qollab & IonQ" in readme


def test_r3b_zip_rebuild_matches_pin(tmp_path):
    want = json.loads((ROOT / "scripts/r3b_pins.json").read_text())["zips"]["uqcc_r3b_ionq_compatible_rc.zip"]
    _, h = build_r3b_zip.build(tmp_path / "r3b.zip")
    assert h == want
    p = ROOT / "dist" / "uqcc_r3b_ionq_compatible_rc.zip"
    if p.exists():
        assert hashlib.sha256(p.read_bytes()).hexdigest() == want
