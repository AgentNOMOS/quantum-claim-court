"""UQCC-R2 court addendum. Python standard library + the FROZEN uqcc_r1 package (unchanged).

Adds, without altering any R1 rule:
  * four measurement-value claims (V1-V4) about THIS circuit, decided against the exact values
    (mathematics) and the live 99% family-wise intervals (measurement) -- this is where a
    measurement can DISPUTE a claim;
  * a challenge matrix: statement x citation x framing, every cell decided by the frozen
    uqcc_r1.claims.decide during the single Run (shown in the UI as LOCAL EVALUATION);
  * witness codes (literature / mathematics / measurement) for display.
"""
import hashlib
import json
from fractions import Fraction

from uqcc_r1 import claims as r1_claims
from uqcc_r1 import interpret as r1_interpret

COURT_SCHEMA = "uqcc-r2-court/1"

# ---------------------------------------------------------------- value claims (R2 addendum)

VALUE_CLAIMS = [
    {"id": "V1", "observables": ["A", "B"], "value": "5/6",
     "text": "Each clone produced by this circuit has fidelity 5/6 (for this run's input state)."},
    {"id": "V2", "observables": ["A", "B"], "value": "2/3",
     "text": "Each clone produced by this circuit has fidelity 2/3."},
    {"id": "V3", "observables": ["AB"], "value": "2/3",
     "text": "The two clones jointly match the two-copy target state with probability 2/3."},
    {"id": "V4", "observables": ["A", "B"], "value": "1",
     "text": "Each clone produced by this circuit is a perfect copy (fidelity 1)."},
]


def decide_value(vc, measurement):
    v = Fraction(vc["value"])
    exact = {k: r1_interpret.EXPECTED[k] for k in vc["observables"]}
    math_ok = all(e == v for e in exact.values())
    ev = {"literature": "NOT_REQUIRED",
          "mathematics": ("M_THIS_CIRCUIT: exact " + ", ".join(f"{k}={e.numerator}/{e.denominator}" for k, e in exact.items())
                          + (" AGREES" if math_ok else " CONTRADICTS claimed " + vc["value"])),
          "measurement": "NOT_USED"}

    def out(verdict, reason):
        return {"id": vc["id"], "verdict": verdict, "reason": reason, "evidence": ev}

    if not measurement or not measurement.get("valid"):
        ev["measurement"] = "MISSING_OR_INVALID"
        return out("INSUFFICIENT", "Measurement evidence missing or invalid.")
    obs = measurement["observables"]
    inside = {k: float(obs[k]["ci_low"]) <= float(v) <= float(obs[k]["ci_high"]) for k in vc["observables"]}
    meas_ok = all(inside.values())
    ev["measurement"] = "SIMULATOR_MEASUREMENT_OBSERVED: " + ", ".join(
        f"{k} {obs[k]['estimate_dec']} [{obs[k]['ci_low']},{obs[k]['ci_high']}] "
        f"{'contains' if inside[k] else 'EXCLUDES'} {vc['value']}" for k in vc["observables"])
    if math_ok and meas_ok:
        return out("SUPPORTED", "Exact value and live interval agree (one input state, one simulator run).")
    if not math_ok and not meas_ok:
        return out("DISPUTED", "Both the exact calculation and the live measurement disagree with the claimed value.")
    if not math_ok:
        return out("DISPUTED", "The exact calculation disagrees; this finite run alone cannot separate the values.")
    return out("DISPUTED", "The live interval excludes the exact value. For this correct circuit this happens by "
                           "chance in about 1.4% of runs; it is a statistical outcome, not a fault finding.")


# ---------------------------------------------------------------- challenge matrix

BH96 = {"doi": "10.1103/physreva.54.1844", "title": "Quantum copying: Beyond the no-cloning theorem",
        "year": 1996, "first_author": "Bužek"}
STATEMENTS = [
    ["S1", "S_NO_PERFECT_UNIVERSAL_CLONING", "An unknown quantum state cannot be cloned perfectly."],
    ["S2", "S_APPROX_UNIVERSAL_COPIER_EXISTS",
     "A universal copier exists whose (imperfect) output quality does not depend on the input."],
    ["S3", "S_OPTIMAL_UNIVERSAL_1TO2_FIDELITY_5_6",
     "The optimal single-copy fidelity of deterministic, symmetric, universal 1->2 qubit cloning is 5/6."],
    ["S4", "S_PERFECT_UNIVERSAL_CLONING", "Unknown quantum states can be copied perfectly."],
    ["S5", "S_CNOT_COPIES_ALL_STATES", "A CNOT gate copies all quantum states."],
    ["S6", "S_OPTIMAL_SYMMETRIC_UNIVERSAL_FIDELITY_0_9", "The optimal symmetric universal clone fidelity is 0.9."],
]
CITATIONS = [
    ["none", "No citation", None],
    ["WZ82", "Wootters & Zurek 1982 (genuine)",
     {"doi": "10.1038/299802a0", "title": "A single quantum cannot be cloned", "year": 1982, "first_author": "Wootters"}],
    ["BH96", "Bužek & Hillery 1996 (genuine)", BH96],
    ["BDEFMS98", "Bruß et al. 1998 (genuine)",
     {"doi": "10.1103/physreva.57.2368", "title": "Optimal universal and state-dependent quantum cloning",
      "year": 1998, "first_author": "Bruß"}],
    ["DJ92", "Deutsch & Jozsa 1992 (genuine, unrelated topic)",
     {"doi": "10.1098/rspa.1992.0167", "title": "Rapid solution of problems by quantum computation",
      "year": 1992, "first_author": "Deutsch"}],
    ["FORGED", "Forged DOI (fictitious control)", r1_claims.FORGED],
    ["WRONGMAP", "Bužek & Hillery title + wrong DOI (Cory et al. 1998)",
     dict(BH96, doi="10.1103/physrevlett.81.2152")],
]
FRAMINGS = [
    ["as_stated", "Stated as a literature claim", None],
    ["run_proves", "\"...and this experiment proves it\"", "experiment_proves_theorem"],
]
# Permissible wording per statement (what the court would accept), with its source.
STATEMENT_REWRITE = {
    "S1": "An unknown quantum state cannot be cloned perfectly (Wootters & Zurek 1982). This run is consistent with that theorem but does not prove it.",
    "S2": "Bužek & Hillery (1996) describe a universal copying machine whose output quality does not depend on the input.",
    "S3": "For deterministic, symmetric, universal 1->2 qubit cloning the optimal single-copy fidelity is 5/6 (Bruß et al. 1998).",
    "S4": "Unknown quantum states cannot be copied perfectly (Wootters & Zurek 1982); approximate universal copies are possible.",
    "S5": "A CNOT copies the basis states |0> and |1>; for a superposition such as |+> each output has fidelity 1/2 (exact calculation, not measured in this run).",
    "S6": "For deterministic, symmetric, universal 1->2 qubit cloning the optimal single-copy fidelity is 5/6, not 0.9 (Bruß et al. 1998).",
}


def challenge(manifest, measurement):
    reasons, matrix = [], []
    for sid, asserts, label in STATEMENTS:
        for cid, _, cite in CITATIONS:
            for fid, _, overreach in FRAMINGS:
                claim = {"id": f"X-{sid}-{cid}-{fid}", "kind": "attribution", "asserts": asserts,
                         "cites": [cite] if cite else [], "math": None, "text": label}
                if overreach:
                    claim["overreach"] = overreach
                d = r1_claims.decide(claim, manifest, measurement)
                if d["reason"] not in reasons:
                    reasons.append(d["reason"])
                matrix.append([sid, cid, fid, d["verdict"], reasons.index(d["reason"])])
    # full building blocks are recorded so an independent verifier can re-decide every cell
    return {"statements": STATEMENTS, "citations": CITATIONS, "framings": FRAMINGS,
            "statement_rewrite": STATEMENT_REWRITE,
            "reasons": reasons, "matrix": matrix}


# ---------------------------------------------------------------- docket presentation

REWRITE = {
    "RT1": "An unknown quantum state cannot be copied perfectly (Wootters & Zurek 1982); approximate universal copies are possible.",
    "RT2": STATEMENT_REWRITE["S5"],
    "RT3": "This run is consistent with the no-cloning theorem; the theorem itself is a mathematical result (Wootters & Zurek 1982).",
    "RT4": STATEMENT_REWRITE["S6"],
    "RT5": "The optimal universal 1->2 cloning fidelity is 5/6 (Bruß et al. 1998).",
    "RT6": "Remove the citation: the DOI does not exist (Crossref 404 recorded).",
    "RT7": "Bužek & Hillery (1996) describe a universal copier with input-independent quality; for the 5/6 optimum cite Bruß et al. (1998).",
    "RT8": "For this input state and this simulator run, the measured fidelities are consistent with the circuit's exact values 5/6, 5/6 and 2/3.",
    "RT9": "5/6 is optimal for deterministic, symmetric, universal 1->2 qubit cloning; asymmetric, probabilistic and state-dependent cloning are governed by different results.",
    "RT10": "Cite Bužek & Hillery, Phys. Rev. A 54, 1844 (1996), doi:10.1103/PhysRevA.54.1844.",
    "V2": "Each clone has exact fidelity 5/6; 2/3 is the JOINT two-copy fidelity.",
    "V4": "Each clone has fidelity 5/6, not 1: the copies are good but imperfect.",
}
NEEDS_MEASUREMENT = {"C1", "V1", "V2", "V3", "V4"}   # RT8 is ABOUT a measurement but is decided by a scope rule


def witnesses(decision):
    """Map evidence strings to display codes. Codes: SUPPORTS, CONTRADICTS, FAILS, INSUFFICIENT,
    NOT_NEEDED, SILENT, CONSISTENT, INCONSISTENT, MISSING, CONTEXT."""
    ev = decision["evidence"]
    lit = ev["literature"]
    if lit == "NOT_REQUIRED":
        lc = "NOT_NEEDED"
    elif "TITLE_TEXT" in lit or "ABSTRACT_QUOTE" in lit:
        lc = "SUPPORTS"
    elif lit.startswith(("FORGED_DOI", "METADATA_MISMATCH", "IRRELEVANT_SOURCE")):
        lc = "FAILS"
    else:
        lc = "INSUFFICIENT"
    m = ev["mathematics"]
    if m == "NOT_APPLICABLE":
        mc = "SILENT"
    elif "CONTRADICT" in m:
        mc = "CONTRADICTS"
    else:
        mc = "SUPPORTS"
    s = ev["measurement"]
    if s == "NOT_USED":
        sc = "NOT_NEEDED"
    elif s.startswith("MISSING"):
        sc = "MISSING"
    elif decision["id"] in NEEDS_MEASUREMENT:
        if "too imprecise" in s:
            sc = "INSUFFICIENT"
        elif decision["verdict"] == "DISPUTED" and ("EXCLUDES" in s or decision["id"] == "C1"):
            sc = "INCONSISTENT"
        else:
            sc = "CONSISTENT"
    else:
        sc = "CONTEXT"    # measurement shown alongside a theorem claim, never as its proof
    return {"literature": lc, "mathematics": mc, "measurement": sc}


def canonical(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def build(r1_evidence, r1_digest, manifest):
    measurement = r1_evidence["measurement"]
    vdec = [decide_value(vc, measurement) for vc in VALUE_CLAIMS]
    court = {"schema": COURT_SCHEMA, "r1_evidence_sha256": r1_digest,
             "value_claims": VALUE_CLAIMS, "value_decisions": vdec,
             "challenge": challenge(manifest, measurement),
             "note": "Value claims and the challenge matrix are evaluated locally from this Run's single "
                     "measurement and the frozen rules; no additional quantum job is executed."}
    text = canonical(court)
    return court, text, hashlib.sha256(text.encode("ascii")).hexdigest()
