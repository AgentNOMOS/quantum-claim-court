"""UQCC-R2 Python tests: frozen baseline, bridge (one job), court addendum, R2 verifier, ZIP, scan."""
import contextlib
import hashlib
import io
import json
import pathlib
import re
import subprocess
import sys
import zipfile

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import build_r2_zip  # noqa: E402

STAGE = build_r2_zip.stage(ROOT / "dev" / "_stage_tests")
for p in (str(STAGE),):
    if p not in sys.path:
        sys.path.insert(0, p)
# the staged uqcc_r1 must be the one imported here (identical bytes to qollab_r1/)
for m in [m for m in sys.modules if m.startswith(("uqcc_r1", "uqcc_app"))]:
    del sys.modules[m]

from qiskit import QuantumCircuit  # noqa: E402
from qiskit.providers.basic_provider import BasicSimulator  # noqa: E402

from uqcc_app import court, js_api  # noqa: E402
from uqcc_r1 import claims as r1_claims, interpret  # noqa: E402
from uqcc_r1.sources_manifest import MANIFEST_TEXT  # noqa: E402

MANIFEST = json.loads(MANIFEST_TEXT)
R1_ZIP_SHA = "b20b03f766c0f837ec3941b5cb50dddd3bc7e9f121f1b0642090aa6e50e7f502"


class _Res:
    def __init__(self, counts):
        self._c, self.results = counts, [type("R", (), {"shots": sum(counts.values())})()]

    def get_counts(self):
        return self._c


class _Job:
    def __init__(self, r):
        self._r = r

    def result(self):
        return self._r


class Counting(BasicSimulator):
    def __init__(self, counts=None, fail=False):
        super().__init__()
        self.calls, self._counts, self._fail = [], counts, fail

    def run(self, c, **kw):
        self.calls.append((type(c).__name__, sorted(kw), kw.get("shots")))
        if self._fail:
            raise RuntimeError("provider down")
        if self._counts is not None:
            return _Job(_Res(self._counts))
        return super().run(c, seed_simulator=99, **kw)


def run_bridge(backend):
    js_api._reset_for_tests()
    with contextlib.redirect_stdout(io.StringIO()) as out:
        text = js_api.run_court(backend)
    return json.loads(text), text, out.getvalue()


@pytest.fixture(scope="module")
def live():
    b = Counting()
    env, text, console = run_bridge(b)
    return b, env, text, console


# ---------------------------------------------------------------- frozen baseline

PINS = json.loads((ROOT / "scripts/frozen_pins.json").read_text())


def test_frozen_files_identical_to_uqcc_r1_pins():
    build_r2_zip.frozen_check()
    for rel in build_r2_zip.FROZEN:
        assert hashlib.sha256((STAGE / rel).read_bytes()).hexdigest() == PINS["files"][rel], rel
        tagged = subprocess.run(["git", "-C", str(ROOT), "show", f"uqcc-r1:qollab_r1/{rel}"], capture_output=True)
        if tagged.returncode == 0:                       # development repo only
            assert (STAGE / rel).read_bytes() == tagged.stdout, rel


def test_rebuilt_r1_zip_is_byte_identical(tmp_path):
    import build_r1_zip
    _, h = build_r1_zip.build(tmp_path / "r1.zip")
    assert h == R1_ZIP_SHA == PINS["zips"]["uqcc_r1_qollab_smoke.zip"]


def test_rebuilt_r2_zip_is_byte_identical_to_owner_tested_zip(tmp_path):
    _, h = build_r2_zip.build(tmp_path / "r2.zip")
    assert h == PINS["zips"]["uqcc_r2_claim_court_app.zip"]


def test_dist_zips_unchanged_if_present():
    for name, want in PINS["zips"].items():
        p = ROOT / "dist" / name
        if p.exists():
            assert hashlib.sha256(p.read_bytes()).hexdigest() == want, name


def test_confidence_methodology_unchanged():
    assert interpret.CONFIDENCE == 0.99 and interpret.FAMILY == 3


# ---------------------------------------------------------------- bridge / one job

def test_exactly_one_bare_circuit_job(live):
    b, env, _, _ = live
    assert env["status"] == "ok" and env["live"] is True
    assert b.calls == [("QuantumCircuit", ["shots"], 2000)]


def test_second_call_in_same_run_is_refused_without_job(live):
    b, _, _, _ = live
    n = len(b.calls)
    second = json.loads(js_api.run_court(b))          # no reset: same Run
    assert second["status"] == "refused" and len(b.calls) == n
    js_api._reset_for_tests()


@pytest.mark.parametrize("backend", [None, type("N", (), {"name": "ionq_simulator"})()])
def test_refusals_submit_no_job(backend):
    env, _, _ = run_bridge(backend)
    assert env["status"] == "refused" and env["job_attempted"] is False and "export_text" not in env


def test_provider_failure_is_not_retried():
    b = Counting(fail=True)
    env, _, _ = run_bridge(b)
    assert env["status"] == "error" and env["job_attempted"] is True and len(b.calls) == 1


def test_console_copy_verifies_with_frozen_r1_verifier(live, tmp_path):
    f = tmp_path / "console.txt"
    f.write_text(live[3])
    r = subprocess.run([sys.executable, "-I", str(STAGE / "verifier/verify_uqcc_r1.py"), str(f), str(STAGE)],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stdout


def test_export_text_blocks_are_exact_python_texts(live):
    env = live[1]
    assert f"UQCC_R1_EVIDENCE_BEGIN\n{env['r1_evidence_text']}\nUQCC_R1_EVIDENCE_END" in env["export_text"]
    assert f"UQCC_R2_COURT_BEGIN\n{env['court_text']}\nUQCC_R2_COURT_END" in env["export_text"]
    assert hashlib.sha256(env["court_text"].encode()).hexdigest() == env["court_sha256"]
    assert json.loads(env["court_text"])["r1_evidence_sha256"] == env["r1_evidence_sha256"]


def test_court_text_is_canonical_and_float_free(live):
    txt = live[1]["court_text"]
    obj = json.loads(txt)
    assert court.canonical(obj) == txt

    def walk(x):
        assert not isinstance(x, float), x
        for v in (x.values() if isinstance(x, dict) else x if isinstance(x, list) else []):
            walk(v)
    walk(obj)


# ---------------------------------------------------------------- input & bit order

def test_input_preparation_and_inverse_rotation(live):
    ev = json.loads(live[1]["r1_evidence_text"])
    ops = ev["circuit"]["ops"]
    assert [(o["name"], o["qubits"], o["params"]) for o in ops[:2]] == [("ry", [0], ["1.1"]), ("rz", [0], ["0.7"])]
    tail = [(o["name"], o["qubits"], o["params"]) for o in ops[-6:]]
    assert tail == [("rz", [0], ["-0.7"]), ("ry", [0], ["-1.1"]), ("rz", [1], ["-0.7"]), ("ry", [1], ["-1.1"]),
                    ("measure", [0], []), ("measure", [1], [])]
    assert [o["clbits"] for o in ops[-2:]] == [[0], [1]]


def test_bit_order_clone_a_is_rightmost():
    env, _, _ = run_bridge(Counting(counts={"01": 2000}))   # clbit0=1 (A wrong), clbit1=0 (B right)
    obs = json.loads(env["r1_evidence_text"])["measurement"]["observables"]
    assert obs["A"]["hits"] == 0 and obs["B"]["hits"] == 2000 and obs["AB"]["hits"] == 0


# ---------------------------------------------------------------- court decisions

def _meas(counts):
    return interpret.interpret(counts, 2000)


EXACTISH = {"00": 1333, "01": 334, "10": 333}


def test_value_claims_on_consistent_run():
    got = {vc["id"]: court.decide_value(vc, _meas(EXACTISH))["verdict"] for vc in court.VALUE_CLAIMS}
    assert got == {"V1": "SUPPORTED", "V2": "DISPUTED", "V3": "SUPPORTED", "V4": "DISPUTED"}


def test_statistical_disagreement_disputes_measurement_claims_only():
    m = _meas({"00": 1240, "01": 420, "10": 340})            # A = 0.79
    v1 = court.decide_value(court.VALUE_CLAIMS[0], m)
    assert v1["verdict"] == "DISPUTED" and "1.4%" in v1["reason"]
    w = court.witnesses(v1)
    assert w == {"literature": "NOT_NEEDED", "mathematics": "SUPPORTS", "measurement": "INCONSISTENT"}
    lit = {d["id"]: d["verdict"] for d in r1_claims.decide_all(MANIFEST, m)}
    assert lit["C1"] == "DISPUTED" and lit["C3"] == "SUPPORTED" and lit["RT4"] == "BLOCK"


@pytest.mark.parametrize("meas", [None, {"valid": False, "errors": ["x"]}])
def test_missing_measurement_is_insufficient(meas):
    for vc in court.VALUE_CLAIMS:
        assert court.decide_value(vc, meas)["verdict"] == "INSUFFICIENT"


def test_challenge_matrix_equals_frozen_rules_and_independent_verifier(live):
    sys.path.insert(0, str(STAGE / "verifier"))
    import verify_uqcc_r1 as v1
    ch = json.loads(live[1]["court_text"])["challenge"]
    stm = {s[0]: s[1] for s in ch["statements"]}
    cit = {c[0]: c[2] for c in ch["citations"]}
    frm = {f[0]: f[2] for f in ch["framings"]}
    assert len(ch["matrix"]) == 6 * 7 * 2
    for s, c, f, verdict, _ in ch["matrix"]:
        claim = {"id": "X", "kind": "attribution", "asserts": stm[s], "cites": [cit[c]] if cit[c] else [], "math": None, "text": ""}
        if frm[f]:
            claim["overreach"] = frm[f]
        assert r1_claims.decide(claim, MANIFEST, None)["verdict"] == verdict
        assert v1.redecide(claim, MANIFEST, True, {}) == verdict


def test_metadata_mismatch_and_forgery_always_block(live):
    ch = json.loads(live[1]["court_text"])["challenge"]
    for s, c, f, verdict, _ in ch["matrix"]:
        if c in ("FORGED", "WRONGMAP"):
            assert verdict == "BLOCK", (s, c, f)
    wrong_year = {"id": "X", "kind": "attribution", "asserts": "S_OPTIMAL_UNIVERSAL_1TO2_FIDELITY_5_6", "math": None,
                  "cites": [dict(court.CITATIONS[3][2], year=1997)], "text": ""}
    d = r1_claims.decide(wrong_year, MANIFEST, None)
    assert d["verdict"] == "BLOCK" and "METADATA_MISMATCH" in d["evidence"]["literature"]


def test_witness_codes_keep_classes_separate(live):
    w = {d["id"]: d["witness"] for d in live[1]["view"]["docket"]}
    assert w["C2"] == {"literature": "SUPPORTS", "mathematics": "SUPPORTS", "measurement": "NOT_NEEDED"}
    assert w["C1"]["literature"] == "NOT_NEEDED" and w["C1"]["measurement"] == "CONSISTENT"
    assert w["RT1"]["mathematics"] == "CONTRADICTS" and w["RT1"]["measurement"] == "CONTEXT"
    assert w["RT6"]["literature"] == "FAILS" and w["RT7"]["literature"] == "INSUFFICIENT"
    needs = {d["id"] for d in live[1]["view"]["docket"] if d["needs_measurement"]}
    assert needs == {"C1", "V1", "V2", "V3", "V4"}


def test_rewrites_present_for_every_non_supported_claim(live):
    for d in live[1]["view"]["docket"]:
        if d["decision"]["verdict"] in ("BLOCK", "REWRITE", "DISPUTED") or d["id"] == "RT7":
            assert d["rewrite"], d["id"]


# ---------------------------------------------------------------- R2 verifier

def verify(text, tmp_path):
    f = tmp_path / "e.txt"
    f.write_bytes(text.encode() if isinstance(text, str) else text)
    return subprocess.run([sys.executable, "-I", str(STAGE / "verifier/verify_uqcc_r2.py"), str(f), str(STAGE)],
                          capture_output=True, text=True)


def test_r2_verifier_pass_and_crlf(live, tmp_path):
    assert verify(live[1]["export_text"], tmp_path).returncode == 0
    assert verify(live[1]["export_text"].replace("\n", "\r\n"), tmp_path).returncode == 0


def test_r2_verifier_disputed_run_exit_2(tmp_path):
    env, _, _ = run_bridge(Counting(counts={"00": 1240, "01": 420, "10": 340}))
    r = verify(env["export_text"], tmp_path)
    assert r.returncode == 2 and json.loads(r.stdout)["value_verdicts"]["V1"] == "DISPUTED"


def _reseal(export, court_obj):
    new = court.canonical(court_obj)
    h = hashlib.sha256(new.encode()).hexdigest()
    lines = export.split("\n")
    i = lines.index("UQCC_R2_COURT_BEGIN")
    lines[i + 1] = new
    return "\n".join(re.sub(r"^UQCC_R2_COURT_SHA256=\w+$", f"UQCC_R2_COURT_SHA256={h}", ln) for ln in lines)


@pytest.mark.parametrize("mutate", ["court_byte", "r1_byte", "rebind", "forge_cell", "forge_value", "drop_block", "reserialise"])
def test_r2_verifier_rejects_tampering(live, tmp_path, mutate):
    env = live[1]
    text = env["export_text"]
    c = json.loads(env["court_text"])
    if mutate == "court_byte":
        text = text.replace('"schema":"uqcc-r2-court/1"', '"schema":"uqcc-r2-court/1" ', 1)
    elif mutate == "r1_byte":
        text = text.replace('"shots_requested":2000', '"shots_requested":2001', 1)
    elif mutate == "rebind":
        c["r1_evidence_sha256"] = "0" * 64
        text = _reseal(text, c)
    elif mutate == "forge_cell":
        for row in c["challenge"]["matrix"]:
            if row[1] == "FORGED":
                row[3] = "SUPPORTED"
                break
        text = _reseal(text, c)
    elif mutate == "forge_value":
        c["value_decisions"][1]["verdict"] = "SUPPORTED"
        text = _reseal(text, c)
    elif mutate == "drop_block":
        text = text.split("UQCC_R2_COURT_SHA256")[0]
    elif mutate == "reserialise":
        text = text.replace(env["court_text"], json.dumps(c, sort_keys=True))
    assert verify(text, tmp_path).returncode == 1


# ---------------------------------------------------------------- package

def test_zip_deterministic_and_exact_contents(tmp_path):
    a, ha = build_r2_zip.build(tmp_path / "a.zip")
    b, hb = build_r2_zip.build(tmp_path / "b.zip")
    assert ha == hb
    names = zipfile.ZipFile(a).namelist()
    assert sorted(names) == sorted(build_r2_zip.FROZEN + build_r2_zip.APP)
    assert "main.py" not in names and not any("pycache" in n or n.startswith("dev/") for n in names)
    assert {"index.html", "main.js", "main.css", "LICENSE", "README.md"} <= set(names)


def test_index_is_fragment_without_stripped_tags():
    src = (ROOT / "app/index.html").read_text().lower()
    for tag in (r"<html[\s>]", r"<head[\s>]", r"<header[\s>]", r"<body[\s>]", r"<script[\s>]"):
        assert not re.search(tag, src), tag      # <header> avoided too, in case stripping is prefix-based


def test_main_js_single_bridge_call_and_no_fake_values():
    js = (ROOT / "app/main.js").read_text()
    code = "\n".join(ln for ln in js.splitlines() if not ln.lstrip().startswith("//"))
    assert code.count("callPromising(") == 1 and "state.started" in code
    allsrc = "".join((ROOT / "app" / p).read_text() for p in ("main.js", "ui/logic.js", "ui/render.js", "index.html"))
    for bad in ("1331", "1671", "8df0de20", "fetch(", "XMLHttpRequest", "localStorage"):
        assert bad not in allsrc, bad


GENERIC = [r"BEGIN [A-Z ]*PRIVATE KEY", r"(?i)api[_-]?key\s*[=:]", r"(?i)secret\s*[=:]", r"(?i)bearer\s+[a-z0-9]",
           r"(?i)password", r"@gmail\.com", r"/root/", r"/home/", r"\b(?:\d{1,3}\.){3}\d{1,3}\b(?<!127\.0\.0\.1)"]
# Private patterns (hostnames, addresses, names) live OUTSIDE the public tree in a git-ignored file.
_DENY = ROOT / ".release-denylist"
PRIVATE = GENERIC + ([ln.strip() for ln in _DENY.read_text().splitlines() if ln.strip() and not ln.startswith("#")]
                     if _DENY.exists() else [])


def test_security_scan_of_package(tmp_path):
    z, _ = build_r2_zip.build(tmp_path / "p.zip")
    hits = []
    with zipfile.ZipFile(z) as zf:
        for n in zf.namelist():
            text = zf.read(n).decode("utf-8", "replace")
            for pat in PRIVATE:
                if re.search(pat, text):
                    hits.append((n, pat))
    assert hits == []


def test_package_attribution_and_disclosures():
    readme = (ROOT / "app/README.md").read_text()
    for s in ("This effort is supported by Qollab & IonQ", "MIT", "AI assistance", "Prior work", "10.1038/299802a0",
              "10.1103/PhysRevA.54.1844", "10.1103/PhysRevA.57.2368"):
        assert s in readme, s
    assert (ROOT / "app/LICENSE").read_text().startswith("MIT License")
