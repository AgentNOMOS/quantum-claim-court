#!/usr/bin/env python3
"""Independent UQCC-R1 verifier. Python standard library only; never imports Qiskit or uqcc_r1.

Input: a text file holding the Qollab console output (or just the evidence block), pasted verbatim.
The evidence line is hashed EXACTLY as printed (only a trailing CR from Windows line endings is
dropped) and is never re-serialised. The printed SHA-256 sits in the same paste, so a match proves
only that the text was not damaged in transit -- not who produced it.

Exit codes: 0 VERIFIED_CONSISTENT, 2 VERIFIED_INCONSISTENT (evidence valid, measurement disagrees
with the exact values), 1 FAIL (corrupt/missing evidence or a decision that does not reproduce).

Usage: python3 -I verifier/verify_uqcc_r1.py <console_paste.txt> [package_dir]
"""
import ast
import cmath
import hashlib
import json
import math
import pathlib
import sys
from fractions import Fraction
from statistics import NormalDist

SHOTS = 2000
FAMILY = 3
ALPHA = 0.01   # family-wise, matches the app (99% / Bonferroni over 3)
MAX_HALF = 0.05
# Pre-registered verdicts for claims that must never pass, whatever the data say.
FIXED_VERDICTS = {"C2": "SUPPORTED", "C3": "SUPPORTED", "C4": "SUPPORTED", "RT1": "BLOCK", "RT2": "BLOCK",
                  "RT3": "REWRITE", "RT4": "BLOCK", "RT5": "REWRITE", "RT6": "BLOCK", "RT7": "INSUFFICIENT",
                  "RT8": "REWRITE", "RT9": "REWRITE", "RT10": "BLOCK"}
THEOREM_CONFLICTS = {"S_PERFECT_UNIVERSAL_CLONING", "S_CNOT_COPIES_ALL_STATES",
                     "S_OPTIMAL_SYMMETRIC_UNIVERSAL_FIDELITY_0_9"}


class Fail(Exception):
    pass


# ---------- evidence extraction ----------

def extract(raw_bytes):
    text = raw_bytes.decode("utf-8-sig")
    lines = [ln[:-1] if ln.endswith("\r") else ln for ln in text.split("\n")]
    sha = [ln.split("=", 1)[1].strip() for ln in lines if ln.startswith("UQCC_R1_EVIDENCE_SHA256=")]
    try:
        b = lines.index("UQCC_R1_EVIDENCE_BEGIN")
        e = lines.index("UQCC_R1_EVIDENCE_END")
    except ValueError:
        raise Fail("evidence markers missing -> claim C1 cannot be assessed (INSUFFICIENT)")
    body = lines[b + 1:e]
    if len(body) != 1:
        raise Fail(f"evidence must be exactly one line, found {len(body)} (line wrapped or truncated?)")
    if len(sha) != 1:
        raise Fail("exactly one UQCC_R1_EVIDENCE_SHA256 line required")
    return body[0], sha[0]


# ---------- independent physics ----------

def _ry(t):
    c, s = math.cos(t / 2), math.sin(t / 2)
    return ((c, -s), (s, c))


def _rz(t):
    return ((cmath.exp(-0.5j * t), 0), (0, cmath.exp(0.5j * t)))


def _apply(st, n, tgt, m, ctrl=None):
    out = list(st)
    tb = 1 << tgt
    for i in range(1 << n):
        if i & tb or (ctrl is not None and not (i >> ctrl) & 1):
            continue
        a, b = st[i], st[i | tb]
        out[i] = m[0][0] * a + m[0][1] * b
        out[i | tb] = m[1][0] * a + m[1][1] * b
    return out


def exact_from_ops(ops, n):
    st = [0j] * (1 << n)
    st[0] = 1
    meas = {}
    for op in ops:
        nm, q, p = op["name"], op["qubits"], [float(x) for x in op["params"]]
        if meas and nm != "measure":
            raise Fail("gate after measurement")
        if nm == "ry":
            st = _apply(st, n, q[0], _ry(p[0]))
        elif nm == "rz":
            st = _apply(st, n, q[0], _rz(p[0]))
        elif nm == "cx":
            st = _apply(st, n, q[1], ((0, 1), (1, 0)), ctrl=q[0])
        elif nm == "cry":
            st = _apply(st, n, q[1], _ry(p[0]), ctrl=q[0])
        elif nm == "measure":
            meas[op["clbits"][0]] = q[0]
        else:
            raise Fail(f"unsupported gate {nm}")
    if sorted(meas) != [0, 1]:
        raise Fail("expected clbits 0 and 1 measured")

    def p0(qs):
        return sum(abs(a) ** 2 for i, a in enumerate(st) if all(not (i >> q) & 1 for q in qs))
    return {"A": p0([meas[0]]), "B": p0([meas[1]]), "AB": p0([meas[0], meas[1]])}


def wilson(k, n, z):
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return max(0.0, c - h), min(1.0, c + h)


# ---------- independent claim decision ----------

def fold(s):
    return " ".join(str(s).lower().replace("ž", "z").replace("ß", "ss").split())


def redecide(claim, manifest, meas_ok, obs):
    src = {s["doi"]: s for s in manifest["sources"]}
    nf = {x["doi"] for x in manifest["crossref_not_found"]}
    cited = []
    for c in claim["cites"]:
        d = c["doi"].lower()
        if d in nf:
            return "BLOCK"
        if d not in src:
            return "INSUFFICIENT"
        s = src[d]
        if (fold(c["title"]), c["year"], fold(c["first_author"])) != (fold(s["title"]), s["year"], fold(s["first_author"])):
            return "BLOCK"
        cited.append(s)
    if claim["asserts"] in THEOREM_CONFLICTS:
        return "BLOCK"
    if claim.get("overreach"):
        return "REWRITE"
    if claim["kind"] == "attribution":
        if any(st["statement"] == claim["asserts"] and st["basis"] in ("TITLE_TEXT", "ABSTRACT_QUOTE")
               for s in cited for st in s["statements"]):
            return "SUPPORTED"
        if not cited:
            return "INSUFFICIENT"
        if all("quantum_cloning" not in s["topics"] for s in cited):
            return "REWRITE"
        return "INSUFFICIENT"
    if not meas_ok:
        return "INSUFFICIENT"
    if any(o["half"] > MAX_HALF for o in obs.values()):
        return "INSUFFICIENT"
    return "SUPPORTED" if all(o["contains"] for o in obs.values()) else "DISPUTED"


def load_manifest(pkg):
    tree = ast.parse((pkg / "uqcc_r1" / "sources_manifest.py").read_text(encoding="ascii"))
    for node in tree.body:
        if isinstance(node, ast.Assign) and node.targets[0].id == "MANIFEST_TEXT":
            return ast.literal_eval(node.value)
    raise Fail("MANIFEST_TEXT not found")


# ---------- main ----------

def verify(raw_bytes, pkg):
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
    check(b["name"] == "basic_simulator" or b["class_name"] == "BasicSimulator", "backend is BasicSimulator")

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
    pkg = pathlib.Path(argv[2]) if len(argv) > 2 else pathlib.Path(__file__).resolve().parent.parent
    try:
        rep = verify(pathlib.Path(argv[1]).read_bytes(), pkg)
    except (Fail, KeyError, ValueError, TypeError, IndexError) as exc:
        print(json.dumps({"status": "FAIL", "reason": f"{type(exc).__name__}: {exc}",
                          "claim_C1": "INSUFFICIENT (evidence missing or invalid)"}, indent=1))
        return 1
    print(json.dumps(rep, indent=1))
    return 0 if rep["status"] == "VERIFIED_CONSISTENT" else 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
