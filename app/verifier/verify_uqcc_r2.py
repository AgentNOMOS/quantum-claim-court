#!/usr/bin/env python3
"""Independent UQCC-R2 verifier. Python standard library only; never imports Qiskit or uqcc_app.

Input: the text copied from the app's "Evidence export" box (or the Qollab console), verbatim.
It contains two blocks:
  UQCC_R1_EVIDENCE_*  - checked by the FROZEN R1 verifier (verifier/verify_uqcc_r1.py, unchanged)
  UQCC_R2_COURT_*     - checked here: exact-text SHA-256, binding to the R1 evidence hash, and an
                        independent re-decision of the four value claims and of every cell of the
                        challenge matrix.
SHA-256 matches show the text is unchanged; they do not show who produced it.

Exit codes: 0 VERIFIED_CONSISTENT, 2 VERIFIED_INCONSISTENT (valid evidence, measurement disagrees
with an exact value), 1 FAIL.

Usage: python3 -I verifier/verify_uqcc_r2.py <evidence.txt> [package_dir]
"""
import hashlib
import importlib.util
import json
import pathlib
import sys
from fractions import Fraction

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
    base = R1.verify(raw_bytes, pkg)            # frozen R1 checks (raises Fail)
    checks = base["checks_passed"]
    line, printed = extract_r2(raw_bytes)
    digest = hashlib.sha256(line.encode("utf-8")).hexdigest()

    def check(ok, msg):
        nonlocal checks
        if not ok:
            raise Fail(msg)
        checks += 1

    check(digest == printed, "R2 court SHA-256 matches printed value (integrity only)")
    court = json.loads(line)
    check(court.get("schema") == "uqcc-r2-court/1", "court schema")
    check(court["r1_evidence_sha256"] == base["evidence_sha256"], "court addendum bound to this R1 evidence")

    r1_line, _ = R1.extract(raw_bytes)
    ev = json.loads(r1_line)
    obs = ev["measurement"]["observables"]           # strings already re-derived by the R1 verifier
    manifest = json.loads(R1.load_manifest(pathlib.Path(pkg)))

    got = {d["id"]: d["verdict"] for d in court["value_decisions"]}
    check({vc["id"]: (vc["observables"], vc["value"]) for vc in court["value_claims"]} == EXPECTED_VALUE_CLAIMS,
          "value claims are the registered V1-V4")
    for vid, (keys, value) in EXPECTED_VALUE_CLAIMS.items():
        mine = value_verdict(keys, value, obs)
        check(mine == got[vid], f"{vid}: independent verdict {mine} == court {got[vid]}")
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
            "r1_evidence_sha256": base["evidence_sha256"], "r2_court_sha256": digest,
            "c1_verdict": base["c1_verdict"], "value_verdicts": got, "measured": base["measured"],
            "challenge_cells_verified": len(ch["matrix"]), "checks_passed": checks,
            "note": "SHA-256 shows integrity of the pasted text only, not origin. Local evaluations reuse this "
                    "Run's single measurement; no extra quantum job is implied."}


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
