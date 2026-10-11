"""UQCC-R1 claim decisions. Python standard library only, deterministic, offline.

Three evidence classes are reported separately for every claim:
  literature  - frozen manifest levels: SOURCE_METADATA_VERIFIED / SOURCE_ABSTRACT_CHECKED /
                SOURCE_TEXT_VERIFIED (the last is false for every source; we did not review full texts)
  mathematics - MATHEMATICAL_RESULT_ESTABLISHED (literature theorem or exact computation)
  measurement - SIMULATOR_MEASUREMENT_OBSERVED (this run's counts), never a proof of a theorem
Verdicts: SUPPORTED, DISPUTED, INSUFFICIENT, REWRITE, BLOCK.
"""
from . import interpret

CLONING_TOPIC = "quantum_cloning"

# asserted statement -> (math result that rules it out)
CONTRADICTIONS = {
    "S_PERFECT_UNIVERSAL_CLONING": "M_NO_CLONING",
    "S_CNOT_COPIES_ALL_STATES": "M_NO_CLONING",
    "S_OPTIMAL_SYMMETRIC_UNIVERSAL_FIDELITY_0_9": "M_OPT_5_6",
}
OVERREACH = {
    "experiment_proves_theorem": "A finite experiment is consistent with the no-cloning theorem; it cannot "
                                 "prove it. The theorem is a mathematical result from the literature.",
    "interval_proves_optimality": "An interval containing 5/6 for one input state on one simulator does not "
                                  "prove universality or optimality; optimality is a literature result.",
    "scope_generalization": "The 5/6 bound is for deterministic, symmetric, universal 1->2 qubit cloning only; "
                            "it does not transfer to asymmetric, probabilistic or state-dependent cloning.",
}

FORGED = {"doi": "10.1103/physrevlett.130.999999", "title": "Perfect quantum cloning on trapped ions",
          "year": 2023, "first_author": "Fictitious"}

CLAIMS = [
    {"id": "C1", "kind": "measurement", "asserts": "S_MEASURED_MATCHES_THIS_CIRCUIT", "cites": [],
     "math": "M_THIS_CIRCUIT",
     "text": "On the injected simulator, for the fixed input Rz(0.7)Ry(1.1)|0> and 2000 shots, the measured "
             "clone-A, clone-B and joint fidelities are consistent with this circuit's exact values 5/6, 5/6 "
             "and 2/3."},
    {"id": "C2", "kind": "attribution", "asserts": "S_NO_PERFECT_UNIVERSAL_CLONING", "math": "M_NO_CLONING",
     "cites": [{"doi": "10.1038/299802a0", "title": "A single quantum cannot be cloned", "year": 1982,
                "first_author": "Wootters"}],
     "text": "Wootters & Zurek (1982) established that an unknown quantum state cannot be cloned perfectly."},
    {"id": "C3", "kind": "attribution", "asserts": "S_OPTIMAL_UNIVERSAL_1TO2_FIDELITY_5_6", "math": "M_OPT_5_6",
     "cites": [{"doi": "10.1103/physreva.57.2368", "title": "Optimal universal and state-dependent quantum cloning",
                "year": 1998, "first_author": "Bruß"}],
     "text": "Bruß et al. (1998) showed that 5/6 is the maximal single-copy fidelity of deterministic, "
             "symmetric, universal 1->2 qubit cloning."},
    {"id": "C4", "kind": "attribution", "asserts": "S_APPROX_UNIVERSAL_COPIER_EXISTS", "math": None,
     "cites": [{"doi": "10.1103/physreva.54.1844", "title": "Quantum copying: Beyond the no-cloning theorem",
                "year": 1996, "first_author": "Bužek"}],
     "text": "Bužek & Hillery (1996) described a universal copying machine whose output quality does not "
             "depend on the input."},
    {"id": "RT1", "kind": "attribution", "asserts": "S_PERFECT_UNIVERSAL_CLONING", "cites": [], "math": None,
     "text": "Unknown quantum states can be copied perfectly."},
    {"id": "RT2", "kind": "attribution", "asserts": "S_CNOT_COPIES_ALL_STATES", "cites": [], "math": None,
     "text": "A CNOT gate copies all quantum states."},
    {"id": "RT3", "kind": "attribution", "asserts": "S_NO_PERFECT_UNIVERSAL_CLONING", "cites": [], "math": None,
     "overreach": "experiment_proves_theorem", "text": "This experiment proves the no-cloning theorem."},
    {"id": "RT4", "kind": "attribution", "asserts": "S_OPTIMAL_SYMMETRIC_UNIVERSAL_FIDELITY_0_9", "cites": [],
     "math": None, "text": "The optimal symmetric universal clone fidelity is 0.9."},
    {"id": "RT5", "kind": "attribution", "asserts": "S_OPTIMAL_UNIVERSAL_1TO2_FIDELITY_5_6", "math": None,
     "cites": [{"doi": "10.1098/rspa.1992.0167", "title": "Rapid solution of problems by quantum computation",
                "year": 1992, "first_author": "Deutsch"}],
     "text": "The optimal universal 1->2 cloning fidelity is 5/6 (Deutsch & Jozsa 1992)."},
    {"id": "RT6", "kind": "attribution", "asserts": "S_HARDWARE_PERFECT_CLONING", "cites": [FORGED], "math": None,
     "text": "[NEGATIVE CONTROL: forged DOI, fictitious authors] 'Fictitious & Placeholder (2023)' demonstrated "
             "perfect cloning on trapped ions."},
    {"id": "RT7", "kind": "attribution", "asserts": "S_OPTIMAL_UNIVERSAL_1TO2_FIDELITY_5_6", "math": None,
     "cites": [{"doi": "10.1103/physreva.54.1844", "title": "Quantum copying: Beyond the no-cloning theorem",
                "year": 1996, "first_author": "Bužek"}],
     "text": "Bužek & Hillery (1996) proved that 5/6 is the optimal universal cloning fidelity."},
    {"id": "RT8", "kind": "measurement", "asserts": "S_THIS_CIRCUIT_PROVEN_OPTIMAL", "cites": [], "math": None,
     "overreach": "interval_proves_optimality",
     "text": "Our measured interval contains 5/6, so this circuit is proven to be the optimal universal cloner."},
    {"id": "RT9", "kind": "attribution", "asserts": "S_5_6_LIMIT_ALL_CLONING", "cites": [], "math": None,
     "overreach": "scope_generalization",
     "text": "5/6 is the fidelity limit for every kind of quantum cloning, including asymmetric and "
             "probabilistic cloners."},
    {"id": "RT10", "kind": "attribution", "asserts": "S_APPROX_UNIVERSAL_COPIER_EXISTS", "math": None,
     "cites": [{"doi": "10.1103/physrevlett.81.2152", "title": "Quantum copying: Beyond the no-cloning theorem",
                "year": 1996, "first_author": "Bužek"}],
     "text": "A universal copier exists (Bužek & Hillery, 'Quantum copying: Beyond the no-cloning "
             "theorem', doi:10.1103/PhysRevLett.81.2152)."},
]


def _fold(s):
    return " ".join(str(s).lower().replace("ž", "z").replace("ß", "ss").split())


def _lit_level(src):
    lv = src["levels"]
    return {k: lv[k]["value"] for k in ("SOURCE_METADATA_VERIFIED", "SOURCE_ABSTRACT_CHECKED", "SOURCE_TEXT_VERIFIED")}


def decide(claim, manifest, measurement):
    sources = {s["doi"]: s for s in manifest["sources"]}
    forged = {n["doi"] for n in manifest["crossref_not_found"]}
    math_ids = {m["id"]: m for m in manifest["math_results"]}
    ev = {"literature": "NOT_REQUIRED", "mathematics": "NOT_APPLICABLE", "measurement": "NOT_USED"}

    def out(verdict, reason):
        return {"id": claim["id"], "verdict": verdict, "reason": reason, "evidence": ev}

    if claim.get("math") in math_ids:
        ev["mathematics"] = f"{claim['math']}: {math_ids[claim['math']]['status']} ({math_ids[claim['math']]['origin']})"

    cited = []
    for c in claim["cites"]:
        doi = c["doi"].lower()
        if doi in forged:
            ev["literature"] = f"FORGED_DOI {doi} (Crossref 404 recorded)"
            return out("BLOCK", "Cited DOI does not exist.")
        if doi not in sources:
            ev["literature"] = f"UNVERIFIED_DOI {doi}"
            return out("INSUFFICIENT", "Cited DOI is not in the frozen manifest.")
        s = sources[doi]
        if _fold(c["title"]) != _fold(s["title"]) or c["year"] != s["year"] or _fold(c["first_author"]) != _fold(s["first_author"]):
            ev["literature"] = f"METADATA_MISMATCH {doi} is '{s['title']}' ({s['first_author']} {s['year']})"
            return out("BLOCK", "Citation metadata does not match the DOI's registered record.")
        cited.append(s)

    if claim["asserts"] in CONTRADICTIONS:
        m = CONTRADICTIONS[claim["asserts"]]
        ev["mathematics"] = f"CONTRADICTED_BY {m}: {math_ids[m]['status']} ({math_ids[m]['origin']})"
        if claim["asserts"] == "S_PERFECT_UNIVERSAL_CLONING" and measurement and measurement.get("valid"):
            ok = all(measurement["observables"][k]["excludes_perfect_cloning"] for k in ("A", "B"))
            ev["measurement"] = ("SIMULATOR_MEASUREMENT_OBSERVED: clone CIs exclude F=1 (this state only)" if ok
                                 else "SIMULATOR_MEASUREMENT_OBSERVED: does not exclude F=1")
        return out("BLOCK", f"Contradicts established result {m}.")

    if claim.get("overreach"):
        return out("REWRITE", OVERREACH[claim["overreach"]])

    if claim["kind"] == "attribution":
        holders = [s["id"] for s in manifest["sources"] for st in s["statements"] if st["statement"] == claim["asserts"]]
        for s in cited:
            for st in s["statements"]:
                if st["statement"] == claim["asserts"]:
                    ev["literature"] = (f"{s['id']}: {st['basis']}; levels {_lit_level(s)}")
                    return out("SUPPORTED", "Cited source states this at the recorded level (full text not reviewed).")
        if not cited:
            ev["literature"] = "NO_CITATION"
            return out("INSUFFICIENT", "No source cited.")
        if all(CLONING_TOPIC not in s["topics"] for s in cited):
            ev["literature"] = f"IRRELEVANT_SOURCE {[s['id'] for s in cited]} (topics {[s['topics'] for s in cited]})"
            return out("REWRITE", f"Genuine source, irrelevant to the claim; cite {', '.join(holders) or 'a relevant source'}.")
        ev["literature"] = f"QUOTE_NOT_FOUND in checked abstract/title of {[s['id'] for s in cited]}; SOURCE_TEXT_VERIFIED=false"
        return out("INSUFFICIENT", "Relevant source, but the checked text does not contain this statement.")

    # measurement claims
    if not measurement or not measurement.get("valid"):
        ev["measurement"] = "MISSING_OR_INVALID: " + "; ".join((measurement or {}).get("errors", ["no measurement"]))
        return out("INSUFFICIENT", "Measurement evidence missing or invalid.")
    obs = measurement["observables"]
    if any(float(obs[k]["half_width"]) > interpret.MAX_HALF_WIDTH for k in obs):
        ev["measurement"] = "SIMULATOR_MEASUREMENT_OBSERVED: too imprecise"
        return out("INSUFFICIENT", "Intervals too wide.")
    summary = ", ".join(f"{k} {obs[k]['estimate_dec']} [{obs[k]['ci_low']},{obs[k]['ci_high']}]" for k in ("A", "B", "AB"))
    ev["measurement"] = "SIMULATOR_MEASUREMENT_OBSERVED: " + summary
    if all(obs[k]["contains_expected"] for k in obs):
        return out("SUPPORTED", "All three intervals contain the exact values (one input state, one backend; "
                                "consistency, not proof of universality or optimality).")
    return out("DISPUTED", "At least one interval excludes the exact value.")


def decide_all(manifest, measurement):
    return [decide(c, manifest, measurement) for c in CLAIMS]
