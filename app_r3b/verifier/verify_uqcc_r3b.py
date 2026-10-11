#!/usr/bin/env python3
"""Independent UQCC-R3b verifier. Python standard library only; never imports Qiskit or uqcc_app.

Input: the text copied from the app's "Evidence export" box (or the Qollab console), verbatim.
It contains two blocks:
  UQCC_R1_EVIDENCE_*  - the measurement evidence (frozen R1 layout, schema uqcc-r1-evidence/1).
                        Checked by verify_measurement below: a verbatim copy of the FROZEN
                        verify_uqcc_r1.verify whose single backend check is replaced by the R3b policy
                        (tests/test_r3b.py asserts the copy differs in exactly that line). All helper
                        functions are imported from the frozen verifier/verify_uqcc_r1.py.
  UQCC_R2_COURT_*     - the court record (schema uqcc-r3b-court/1): exact-text SHA-256, binding to the
                        measurement hash, backend context, value claims and every challenge cell.
SHA-256 matches show the text is unchanged; they do not show who produced it.

Exit codes: 0 VERIFIED_CONSISTENT, 2 VERIFIED_INCONSISTENT (valid evidence, measurement disagrees
with an exact IDEAL value; on a noise-model backend this is expected and is not a theorem failure), 1 FAIL.

Usage: python3 -I verifier/verify_uqcc_r3b.py <evidence.txt> [package_dir]
"""
import hashlib
import importlib.util
import json
import pathlib
import re
import sys
from fractions import Fraction
from statistics import NormalDist

HERE = pathlib.Path(__file__).resolve().parent
EXACT = {"A": Fraction(5, 6), "B": Fraction(5, 6), "AB": Fraction(2, 3)}
EXPECTED_VALUE_CLAIMS = {"V1": (["A", "B"], "5/6"), "V2": (["A", "B"], "2/3"),
                         "V3": (["AB"], "2/3"), "V4": (["A", "B"], "1")}
# Pre-registered cells: these must hold whatever the measurement shows.
FIXED_CELLS = {("S3", "BDEFMS98", "as_stated"): "SUPPORTED", ("S3", "DJ92", "as_stated"): "REWRITE",
               ("S3", "BH96", "as_stated"): "INSUFFICIENT", ("S1", "WZ82", "as_stated"): "SUPPORTED",
               ("S1", "WZ82", "run_proves"): "REWRITE", ("S4", "none", "as_stated"): "BLOCK",
               ("S5", "WZ82", "as_stated"): "BLOCK", ("S6", "BDEFMS98", "as_stated"): "BLOCK",
               ("S3", "FORGED", "as_stated"): "BLOCK", ("S2", "WRONGMAP", "as_stated"): "BLOCK",
               ("S2", "BH96", "as_stated"): "SUPPORTED", ("S3", "none", "as_stated"): "INSUFFICIENT"}


def load_r1():
    spec = importlib.util.spec_from_file_location("verify_uqcc_r1", HERE / "verify_uqcc_r1.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


R1 = load_r1()
Fail = R1.Fail
# names used by the verbatim copy of the frozen R1 verify()
SHOTS, ALPHA, FAMILY, FIXED_VERDICTS = R1.SHOTS, R1.ALPHA, R1.FAMILY, R1.FIXED_VERDICTS
extract, exact_from_ops, wilson, load_manifest, redecide = (R1.extract, R1.exact_from_ops, R1.wilson,
                                                           R1.load_manifest, R1.redecide)

# ---------- R3b backend policy (mirrors app uqcc_app/backend_policy.py, re-implemented here) ----------
IONQ_SIM_NAME = re.compile(r"^ionq_simulator(\.[a-z0-9-]{1,32})?$")
NOISE_MODEL = re.compile(r"^[a-z0-9._-]{1,40}$")
NOISY_DISPUTE_REASON = ("The live interval excludes the exact IDEAL value. This Run used a noise-model simulator, so "
                        "deviation from the ideal prediction is expected; it is not evidence against the mathematics "
                        "or the no-cloning theorem.")
IDEAL_DISPUTE_REASON = ("The live interval excludes the exact value. For this correct circuit this happens by "
                        "chance in about 1.4% of runs; it is a statistical outcome, not a fault finding.")


def backend_kind(b, ctx):
    """Return the policy kind for recorded identity b and court backend_context ctx, or raise Fail."""
    name, mro = b.get("name"), ctx.get("mro") or []
    if not isinstance(name, str) or not name or not mro or mro[0] != b.get("class"):
        raise Fail("backend identity missing or inconsistent with backend_context.mro")
    qpu = "qpu" in name.lower() or any(m.split(".")[-1] == "IonQQPUBackend" for m in mro)
    if qpu:
        raise Fail("IonQ QPU (hardware, credits) recorded: not an authorised backend")
    if ctx.get("free_simulator") is not True:
        raise Fail("backend_context.free_simulator is not true")
    if name == "basic_simulator" or b.get("class_name") == "BasicSimulator":
        if ctx.get("kind") != "builtin_basic_simulator" or ctx.get("ideal_reference_applies") is not True:
            raise Fail("BasicSimulator context mismatch")
        return "builtin_basic_simulator"
    sim = any(m.startswith("qiskit_ionq.") and m.endswith(".IonQSimulatorBackend") for m in mro)
    noise = ctx.get("noise_model")
    if not (sim and IONQ_SIM_NAME.match(name) and ctx.get("kind") == "ionq_remote_simulator"
            and isinstance(noise, str) and NOISE_MODEL.match(noise)):
        raise Fail("backend not positively identified as BasicSimulator or the free IonQ remote simulator")
    if ctx.get("ideal_reference_applies") is not (noise == "ideal"):
        raise Fail("ideal_reference_applies inconsistent with noise_model")
    return "ionq_remote_simulator"


def _recorded_court(raw_bytes):
    line, _ = extract_r2(raw_bytes)
    return json.loads(line)




def extract_r2(raw_bytes):
    lines = [ln[:-1] if ln.endswith("\r") else ln for ln in raw_bytes.decode("utf-8-sig").split("\n")]
    sha = [ln.split("=", 1)[1].strip() for ln in lines if ln.startswith("UQCC_R2_COURT_SHA256=")]
    try:
        b, e = lines.index("UQCC_R2_COURT_BEGIN"), lines.index("UQCC_R2_COURT_END")
    except ValueError:
        raise Fail("R2 court block missing")
    if e != b + 2 or len(sha) != 1:
        raise Fail("R2 court block must be exactly one line with one SHA-256 line")
    return lines[b + 1], sha[0]


def value_verdict(observables, value, obs_strings):
    v = Fraction(value)
    math_ok = all(EXACT[k] == v for k in observables)
    meas_ok = all(float(obs_strings[k]["ci_low"]) <= float(v) <= float(obs_strings[k]["ci_high"]) for k in observables)
    return "SUPPORTED" if (math_ok and meas_ok) else "DISPUTED"


def verify(raw_bytes, pkg):
    court = _recorded_court(raw_bytes)
    ctx = court.get("backend_context")
    if not isinstance(ctx, dict):
        raise Fail("court record lacks backend_context")
    kinds = []
    base = verify_measurement(raw_bytes, pkg, lambda b: kinds.append(backend_kind(b, ctx)) or True)
    checks = base["checks_passed"]
    line, printed = extract_r2(raw_bytes)
    digest = hashlib.sha256(line.encode("utf-8")).hexdigest()

    def check(ok, msg):
        nonlocal checks
        if not ok:
            raise Fail(msg)
        checks += 1

    check(digest == printed, "R2 court SHA-256 matches printed value (integrity only)")
    check(court.get("schema") == "uqcc-r3b-court/1", "court schema uqcc-r3b-court/1")
    check(court["r1_evidence_sha256"] == base["evidence_sha256"], "court addendum bound to this measurement evidence")
    ideal = ctx["ideal_reference_applies"] is True
    check(isinstance(ctx.get("interpretation"), str) and
          ctx["interpretation"].startswith("Ideal reference applies" if ideal else "Noise-model simulation"),
          "interpretation text matches ideal/noise-model context")

    r1_line, _ = R1.extract(raw_bytes)
    ev = json.loads(r1_line)
    obs = ev["measurement"]["observables"]           # strings already re-derived above
    manifest = json.loads(R1.load_manifest(pathlib.Path(pkg)))

    got = {d["id"]: d["verdict"] for d in court["value_decisions"]}
    reasons = {d["id"]: d["reason"] for d in court["value_decisions"]}
    check({vc["id"]: (vc["observables"], vc["value"]) for vc in court["value_claims"]} == EXPECTED_VALUE_CLAIMS,
          "value claims are the registered V1-V4")
    for vid, (keys, value) in EXPECTED_VALUE_CLAIMS.items():
        mine = value_verdict(keys, value, obs)
        check(mine == got[vid], f"{vid}: independent verdict {mine} == court {got[vid]}")
        math_ok = all(EXACT[k] == Fraction(value) for k in keys)
        if mine == "DISPUTED" and math_ok:
            want = IDEAL_DISPUTE_REASON if ideal else NOISY_DISPUTE_REASON
            check(reasons[vid] == want, f"{vid}: dispute reason matches the backend context")
    check(got["V2"] == "DISPUTED" and got["V4"] == "DISPUTED", "V2/V4 contradicted by exact values")

    ch = court["challenge"]
    stm = {s[0]: s[1] for s in ch["statements"]}
    cit = {c[0]: c[2] for c in ch["citations"]}
    frm = {f[0]: f[2] for f in ch["framings"]}
    check(len(ch["matrix"]) == len(stm) * len(cit) * len(frm), "challenge matrix complete")
    cells = {}
    for s, c, f, verdict, ri in ch["matrix"]:
        claim = {"id": "X", "kind": "attribution", "asserts": stm[s], "cites": [cit[c]] if cit[c] else []}
        if frm[f]:
            claim["overreach"] = frm[f]
        mine = R1.redecide(claim, manifest, True, {})
        check(mine == verdict, f"challenge {s}/{c}/{f}: independent {mine} == court {verdict}")
        check(0 <= ri < len(ch["reasons"]), "reason index valid")
        cells[(s, c, f)] = verdict
    for key, want in FIXED_CELLS.items():
        check(cells[key] == want, f"pre-registered cell {key} == {want}")

    consistent = base["status"] == "VERIFIED_CONSISTENT" and got["V1"] == "SUPPORTED" and got["V3"] == "SUPPORTED"
    return {"status": "VERIFIED_CONSISTENT" if consistent else "VERIFIED_INCONSISTENT",
            "backend": {"kind": kinds[0], "name": ev["backend"]["name"], "class": ev["backend"]["class"],
                        "noise_model": ctx["noise_model"], "ideal_reference_applies": ideal},
            "r1_evidence_sha256": base["evidence_sha256"], "r2_court_sha256": digest,
            "c1_verdict": base["c1_verdict"], "value_verdicts": got, "measured": base["measured"],
            "challenge_cells_verified": len(ch["matrix"]), "checks_passed": checks,
            "interpretation": ctx["interpretation"],
            "note": "SHA-256 shows integrity of the pasted text only, not origin. Local evaluations reuse this "
                    "Run's single measurement; no extra quantum job is implied."}


# ---------- verbatim copy of the FROZEN verify_uqcc_r1.verify; only the backend check differs ----------

def verify_measurement(raw_bytes, pkg, backend_ok):
    checks = []

    def check(ok, msg):
        checks.append({"ok": bool(ok), "check": msg})
        if not ok:
            raise Fail(msg)

    line, printed = extract(raw_bytes)
    digest = hashlib.sha256(line.encode("utf-8")).hexdigest()
    check(digest == printed, f"evidence SHA-256 {digest[:16]}.. matches printed {printed[:16]}.. (integrity only)")
    ev = json.loads(line)
    check(ev.get("schema") == "uqcc-r1-evidence/1", "schema uqcc-r1-evidence/1")
    check(ev["jobs_submitted"] == 1, "exactly one job submitted")
    check(ev["shots_requested"] == SHOTS, f"shots requested == {SHOTS}")
    check(ev["result_shots_field"] in (SHOTS, None), "result shots field == requested (or absent)")
    b = ev["backend"]
    check(backend_ok(b), "backend authorised by the R3b policy (BasicSimulator or free IonQ remote simulator)")

    counts = ev["counts"]
    check(isinstance(counts, dict) and counts, "counts present")
    check(all(isinstance(k, str) and len(k) == 2 and set(k) <= {"0", "1"} for k in counts), "all bitstrings 2-bit binary")
    check(all(isinstance(v, int) and v >= 0 for v in counts.values()), "all counts non-negative integers")
    check(sum(counts.values()) == SHOTS, f"counts sum {sum(counts.values())} == {SHOTS}")

    ops = ev["circuit"]["ops"]
    th, ph = float(ev["input_state"]["theta"]), float(ev["input_state"]["phi"])
    check(ops[0]["name"] == "ry" and float(ops[0]["params"][0]) == th and ops[0]["qubits"] == [0] and
          ops[1]["name"] == "rz" and float(ops[1]["params"][0]) == ph and ops[1]["qubits"] == [0],
          "input-state preparation matches the documented input")
    check(ev["circuit"]["metrics"]["qubits"] == 3, "3-qubit circuit")
    exact = exact_from_ops(ops, 3)
    for k, want in (("A", Fraction(5, 6)), ("B", Fraction(5, 6)), ("AB", Fraction(2, 3))):
        check(abs(exact[k] - float(want)) < 1e-9, f"independent state-vector: {k} exact = {want} ({exact[k]:.12f})")

    m = ev["measurement"]
    check(m["valid"] is True, "app marked measurement valid")
    z = NormalDist().inv_cdf(1 - ALPHA / FAMILY / 2)
    check(m["z"] == f"{z:.6f}", "Bonferroni-3 z recomputed")
    hits = {"A": sum(v for k, v in counts.items() if k[1] == "0"),
            "B": sum(v for k, v in counts.items() if k[0] == "0"),
            "AB": counts.get("00", 0)}
    obs = {}
    for k in ("A", "B", "AB"):
        o = m["observables"][k]
        lo, hi = wilson(hits[k], SHOTS, z)
        check(o["hits"] == hits[k], f"{k}: hits recomputed from raw counts ({hits[k]})")
        check(o["estimate"] == f"{hits[k]}/{SHOTS}" and o["estimate_dec"] == f"{hits[k] / SHOTS:.6f}",
              f"{k}: fidelity estimate recomputed")
        check(o["ci_low"] == f"{lo:.6f}" and o["ci_high"] == f"{hi:.6f}", f"{k}: Wilson interval recomputed")
        contains = lo <= exact[k] <= hi
        check(o["contains_expected"] == contains, f"{k}: containment flag reproduced")
        obs[k] = {"contains": contains, "half": (hi - lo) / 2, "est": hits[k] / SHOTS, "lo": lo, "hi": hi}

    text = load_manifest(pkg)
    check(hashlib.sha256(text.encode("ascii")).hexdigest() == ev["manifest_sha256"], "manifest SHA-256 matches shipped manifest")
    manifest = json.loads(text)
    for s in manifest["sources"]:
        check(s["levels"]["SOURCE_TEXT_VERIFIED"]["value"] is False, f"{s['id']}: no full-text verification claimed")

    ids = [c["id"] for c in ev["claims"]]
    check(set(FIXED_VERDICTS) | {"C1"} == set(ids), "claim set is the registered R1 docket")
    decided = {d["id"]: d["verdict"] for d in ev["decisions"]}
    for c in ev["claims"]:
        mine = redecide(c, manifest, True, obs)
        check(mine == decided[c["id"]], f"{c['id']}: independent decision {mine} == app {decided[c['id']]}")
        if c["id"] in FIXED_VERDICTS:
            check(mine == FIXED_VERDICTS[c["id"]], f"{c['id']}: pre-registered verdict {FIXED_VERDICTS[c['id']]}")

    consistent = decided["C1"] == "SUPPORTED"
    return {"status": "VERIFIED_CONSISTENT" if consistent else "VERIFIED_INCONSISTENT",
            "evidence_sha256": digest, "c1_verdict": decided["C1"],
            "measured": {k: f"{v['est']:.6f} [{v['lo']:.6f},{v['hi']:.6f}]" for k, v in obs.items()},
            "checks_passed": len(checks), "note": "SHA-256 shows integrity of the pasted text only, not origin. "
            "Consistency on one state/backend is not proof of universality or optimality."}

def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 1
    pkg = pathlib.Path(argv[2]) if len(argv) > 2 else HERE.parent
    try:
        rep = verify(pathlib.Path(argv[1]).read_bytes(), pkg)
    except (Fail, KeyError, ValueError, TypeError, IndexError) as exc:
        print(json.dumps({"status": "FAIL", "reason": f"{type(exc).__name__}: {exc}"}, indent=1))
        return 1
    print(json.dumps(rep, indent=1))
    return 0 if rep["status"] == "VERIFIED_CONSISTENT" else 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
