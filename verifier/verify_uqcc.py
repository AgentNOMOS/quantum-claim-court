#!/usr/bin/env python3
"""Independent UQCC verifier. Python stdlib only -- imports neither Qiskit nor the uqcc package.

Checks, from the result files and raw evidence alone:
  V1 own statevector simulation of every exported circuit -> exact clone fidelities
     (5/6 per BH clone, 2/3 joint; CNOT copier values) agree with the app's exact values
  V2 raw counts: shot totals, marginal hits and Wilson/Bonferroni CIs recomputed from scratch
  V3 every measured fidelity lies within 5 sigma of the independently simulated exact value
  V4 source manifest SHA-256 equals the one recorded in decisions.json (integrity ONLY)
  V5 citation controls re-derived from the raw Crossref responses, not from the manifest
  V6 every verdict equals the pre-registered expected verdict

Usage: python3 -I verifier/verify_uqcc.py [project_root]
"""
import cmath
import hashlib
import json
import math
import pathlib
import sys
from statistics import NormalDist


def apply_1q(state, n, q, m):
    out = list(state)
    bit = 1 << q
    for i in range(1 << n):
        if not i & bit:
            a, b = state[i], state[i | bit]
            out[i] = m[0][0] * a + m[0][1] * b
            out[i | bit] = m[1][0] * a + m[1][1] * b
    return out


def ry(t):
    c, s = math.cos(t / 2), math.sin(t / 2)
    return [[c, -s], [s, c]]


def rz(t):
    return [[cmath.exp(-0.5j * t), 0], [0, cmath.exp(0.5j * t)]]


def apply_controlled(state, n, ctrl, tgt, m):
    out = list(state)
    cb, tb = 1 << ctrl, 1 << tgt
    for i in range(1 << n):
        if i & cb and not i & tb:
            a, b = state[i], state[i | tb]
            out[i] = m[0][0] * a + m[0][1] * b
            out[i | tb] = m[1][0] * a + m[1][1] * b
    return out


def simulate(circ):
    """Returns the final state BEFORE measurement (measurements are terminal here)."""
    n = circ["num_qubits"]
    st = [0j] * (1 << n)
    st[0] = 1
    measured = {}
    for op in circ["ops"]:
        name, q, p = op["name"], op["qubits"], op["params"]
        if name == "ry":
            st = apply_1q(st, n, q[0], ry(p[0]))
        elif name == "rz":
            st = apply_1q(st, n, q[0], rz(p[0]))
        elif name == "cx":
            st = apply_controlled(st, n, q[0], q[1], [[0, 1], [1, 0]])
        elif name == "cry":
            st = apply_controlled(st, n, q[0], q[1], ry(p[0]))
        elif name == "measure":
            measured[op["clbits"][0]] = q[0]
        else:
            raise ValueError(f"unsupported gate {name}")
    return st, measured


def prob_zero(st, qubits):
    return sum(abs(a) ** 2 for i, a in enumerate(st) if all(not (i >> q) & 1 for q in qubits))


def wilson(k, n, z):
    p = k / n
    den = 1 + z * z / n
    c = (p + z * z / (2 * n)) / den
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return max(0.0, c - h), min(1.0, c + h)


def main(root):
    root = pathlib.Path(root)
    panels = json.loads((root / "results" / "panels.json").read_text())
    dec = json.loads((root / "results" / "decisions.json").read_text())
    fails, checks = [], 0

    def check(ok, msg):
        nonlocal checks
        checks += 1
        if not ok:
            fails.append(msg)

    for pname, panel in panels.items():
        k = len(panel["rows"])
        z = NormalDist().inv_cdf(1 - (1 - panel["confidence"]) / k / 2)
        check(abs(z - panel["z"]) < 1e-12, f"{pname}: z mismatch")
        for r in panel["rows"]:
            st, meas = simulate(r["circuit"])
            qa, qb = meas[0], meas[1]
            exact = {"A": prob_zero(st, [qa]), "B": prob_zero(st, [qb]), "AB": prob_zero(st, [qa, qb])}
            n = sum(r["counts"].values())
            check(n == r["shots"], f"{pname}/{r['state']}: shot total")
            hits = {"A": sum(v for s, v in r["counts"].items() if s[-1] == "0"),
                    "B": sum(v for s, v in r["counts"].items() if s[-2] == "0"),
                    "AB": r["counts"].get("00", 0)}
            for key in ("A", "B", "AB"):
                check(abs(exact[key] - r["exact"][key]) < 1e-9,
                      f"{pname}/{r['state']}/{key}: exact {exact[key]} vs app {r['exact'][key]}")
                m = r["measured"][key]
                check(m["hits"] == hits[key], f"{pname}/{r['state']}/{key}: hits")
                lo, hi = wilson(hits[key], n, z)
                check(abs(lo - m["ci"][0]) < 1e-12 and abs(hi - m["ci"][1]) < 1e-12,
                      f"{pname}/{r['state']}/{key}: CI recompute")
                sigma = math.sqrt(max(exact[key] * (1 - exact[key]), 1e-12) / n)
                check(abs(hits[key] / n - exact[key]) <= 5 * sigma + 1e-12,
                      f"{pname}/{r['state']}/{key}: measured {hits[key] / n:.4f} vs exact {exact[key]:.4f}")
            if pname.startswith("BH"):
                check(abs(exact["A"] - 5 / 6) < 1e-9 and abs(exact["B"] - 5 / 6) < 1e-9,
                      f"{pname}/{r['state']}: BH clone fidelity != 5/6")
                check(abs(exact["AB"] - 2 / 3) < 1e-9, f"{pname}/{r['state']}: BH joint != 2/3")

    sha = hashlib.sha256((root / "uqcc" / "sources.json").read_bytes()).hexdigest()
    check(sha == dec["manifest_sha256"], "V4 manifest sha256 mismatch (integrity only)")

    raw = root / "evidence" / "raw"
    fict = (raw / "10.1103_PhysRevLett.130.999999.json").read_text().strip()
    check(fict == "Resource not found.", "V5 fictitious DOI should be a recorded Crossref 404")
    cory = json.loads((raw / "10.1103_PhysRevLett.81.2152.json").read_text())["message"]["title"][0]
    check(cory == "Experimental Quantum Error Correction", "V5 wrong-DOI control title")
    bruss = json.loads((raw / "10.1103_PhysRevA.57.2368.json").read_text())["message"]
    check(bruss["title"][0] == "Optimal universal and state-dependent quantum cloning" and
          bruss["issued"]["date-parts"][0][0] == 1998, "V5 Bruss et al. metadata")
    arxiv = (raw / "arxiv.xml").read_text()
    check("The maximal fidelity of cloning is shown to be 5/6 for universal cloners" in arxiv,
          "V5 5/6 statement missing from retrieved arXiv abstract")

    for d in dec["decisions"]:
        check(d["verdict"] == d["expected"], f"V6 {d['claim_id']}: {d['verdict']} != expected {d['expected']}")

    print(json.dumps({"verifier": "verify_uqcc.py", "checks": checks, "failures": fails,
                      "status": "PASS" if not fails else "FAIL"}, indent=1))
    return 0 if not fails else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else pathlib.Path(__file__).resolve().parent.parent))
