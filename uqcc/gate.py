"""UQCC claim gate (clean-room R0). Deterministic, narrowly scoped, no network.

Three evidence classes are evaluated separately and never substitute for each other:
  literature   - frozen source manifest (uqcc/sources.json): does a verified primary
                 source state this proposition, and do the cited references match it?
  mathematics  - exact value computed from the circuit (Statevector), or a theorem register
  measurement  - shot counts from a circuit that actually ran, with a confidence interval

Verdicts: SUPPORTED, DISPUTED, INSUFFICIENT, REWRITE, BLOCK.
Rule order is fixed; the first rule that fires decides. Every rule that was evaluated is
reported, so the decision path is auditable.
"""
import json
import pathlib

MANIFEST_PATH = pathlib.Path(__file__).with_name("sources.json")

# Theorem / literature register: proposition -> propositions that it rules out.
# BLOCK = contradicted by a theorem; DISPUTED = contradicted by a positive literature result.
CONTRADICTS = {
    "P_NOCLONE_UNIVERSAL": {"P_PERFECT_UNIVERSAL_CLONING": "BLOCK"},
    "P_UQCM_OPTIMAL_5_6": {"P_UQCM_FIDELITY_ABOVE_5_6": "BLOCK"},
    "P_UQCM_EXISTS_INPUT_INDEPENDENT": {"P_NO_APPROXIMATE_CLONING": "DISPUTED"},
}
STRONG_BASIS = {"ABSTRACT_TEXT", "TITLE_TEXT"}
UNIVERSAL_KINDS = {"theorem"}


def load_manifest(path=MANIFEST_PATH):
    return json.loads(pathlib.Path(path).read_text(encoding="utf-8"))


def _norm(s):
    return " ".join(str(s).lower().replace("ž", "z").replace("ß", "ss").split())


def check_citation(cite, manifest):
    """Return (status, detail). Status: VERIFIED, NOT_FOUND_404, UNKNOWN, MISMATCH."""
    doi = cite["doi"].lower()
    for s in manifest["sources"]:
        if s["doi"] == doi:
            problems = []
            if _norm(cite.get("title", s["title"])) != _norm(s["title"]):
                problems.append(f"title: cited '{cite['title']}' but DOI resolves to '{s['title']}'")
            if "year" in cite and cite["year"] != s["year"]:
                problems.append(f"year: cited {cite['year']} but record says {s['year']}")
            if "first_author" in cite and _norm(cite["first_author"]) != _norm(s["authors"][0]):
                problems.append(f"first author: cited {cite['first_author']} but record says {s['authors'][0]}")
            return ("MISMATCH", "; ".join(problems), s) if problems else ("VERIFIED", s["id"], s)
    for n in manifest["crossref_not_found"]:
        if n["doi"] == doi:
            return "NOT_FOUND_404", f"Crossref returned 404 at {n['checked_utc']}", None
    return "UNKNOWN", "DOI not in frozen manifest (needs research-time lookup)", None


def literature_support(prop, manifest):
    strong, curated = [], []
    for s in manifest["sources"]:
        for p in s["propositions"]:
            if p["proposition"] == prop:
                (strong if p["basis"] in STRONG_BASIS else curated).append(s["id"])
    return strong, curated


def contradiction(prop):
    for established, ruled_out in CONTRADICTS.items():
        if prop in ruled_out:
            return established, ruled_out[prop]
    return None


def decide(claim, manifest, evidence):
    """claim: dict (see docket.py). evidence: {'measurement': {...}|None, 'math': {...}|None}."""
    trace = []
    ev = {"literature": "NOT_EVALUATED", "mathematics": "NOT_EVALUATED", "measurement": "NOT_EVALUATED"}

    def out(verdict, reason, rewrite=None):
        return {"claim_id": claim["id"], "verdict": verdict, "reason": reason, "rewrite": rewrite,
                "evidence": ev, "trace": trace}

    prop = claim["proposition"]

    # R1 citation integrity
    cite_status = []
    for c in claim.get("citations", []):
        st, detail, src = check_citation(c, manifest)
        cite_status.append((st, detail, src))
        trace.append(f"R1 citation {c['doi']}: {st} ({detail})")
    if any(st == "NOT_FOUND_404" for st, _, _ in cite_status):
        ev["literature"] = "FABRICATED_OR_NONEXISTENT_CITATION"
        return out("BLOCK", "A cited DOI does not exist (Crossref 404). Do not publish this claim.")
    if any(st == "MISMATCH" for st, _, _ in cite_status):
        ev["literature"] = "CITATION_METADATA_MISMATCH"
        return out("BLOCK", "Citation metadata does not match the DOI's registered record.")

    # R2 contradiction with theorem / established result
    hit = contradiction(prop)
    trace.append(f"R2 contradiction check: {hit}")
    if hit:
        established, verdict = hit
        strong, _ = literature_support(established, manifest)
        ev["literature"] = f"CONTRADICTED_BY {established} ({', '.join(strong) or 'register'})"
        if evidence.get("math"):
            ev["mathematics"] = evidence["math"]["status"]
        if claim.get("measurement_key") and evidence.get("measurement"):
            ev["measurement"] = _measurement_status(claim, evidence["measurement"])[0]
        return out(verdict, f"Claim contradicts {established}.",
                   rewrite=claim.get("rewrite_hint"))

    # R3 provenance overreach (hash used as authenticity)
    if claim.get("authenticity_basis") == "sha256":
        trace.append("R3 hash-as-authenticity: fired")
        return out("REWRITE", "A SHA-256 shows a file is unchanged; it does not authenticate who wrote it "
                   "or where it came from.",
                   rewrite="The manifest file matches its recorded SHA-256 (integrity only); source "
                           "metadata was retrieved from Crossref/arXiv at the recorded timestamps.")

    # R4 universal statement 'proved' by a finite experiment
    if claim["kind"] in UNIVERSAL_KINDS and claim.get("verb") == "proves" and claim.get("basis") == "own_experiment":
        trace.append("R4 finite-experiment-proves-universal: fired")
        return out("REWRITE", "A finite number of shots on finitely many input states cannot prove a "
                   "universal impossibility theorem.", rewrite=claim.get("rewrite_hint"))

    # R5 literature: cited sources must state the proposition
    if claim.get("needs_literature", True):
        strong, curated = literature_support(prop, manifest)
        cited_ids = [src["id"] for st, _, src in cite_status if st == "VERIFIED"]
        cited_strong = [i for i in cited_ids if i in strong]
        cited_curated = [i for i in cited_ids if i in curated]
        trace.append(f"R5 literature: strong={strong} curated={curated} cited={cited_ids}")
        if any(st == "UNKNOWN" for st, _, _ in cite_status) and not cited_strong:
            ev["literature"] = "UNVERIFIED_CITATION"
            return out("INSUFFICIENT", "Cited DOI is not in the verified manifest; verify it at research time first.")
        if not cited_strong and not cited_curated:
            ev["literature"] = "CITED_SOURCE_DOES_NOT_STATE_PROPOSITION"
            if strong:
                return out("REWRITE", "The cited reference is genuine but does not support this claim.",
                           rewrite=f"Cite {', '.join(strong)} instead.")
            return out("INSUFFICIENT", "No verified source in the manifest states this proposition.")
        if not cited_strong:
            ev["literature"] = "CURATED_ONLY (primary text not verified in R0)"
            return out("INSUFFICIENT", "Source metadata verified, but the proposition itself has not been "
                       "checked against primary text.")
        ev["literature"] = f"SUPPORTED_BY {', '.join(cited_strong)}"
    else:
        ev["literature"] = "NOT_REQUIRED (claim about our own circuit)"

    # R6 mathematics (exact value) -- recorded, decided together with R8
    m = evidence.get("math")
    if m is not None:
        ev["mathematics"] = m["status"]
        trace.append(f"R6 mathematics: {m}")

    # R7 platform scope
    if claim.get("platform") and claim["platform"] != "ideal_simulator":
        ev["measurement"] = "NO_EVIDENCE_ON_CLAIMED_PLATFORM"
        trace.append(f"R7 platform {claim['platform']}: no runs")
        return out("INSUFFICIENT", f"No measurement on '{claim['platform']}' exists; simulator results do not transfer.")

    # R8 measurement
    status, why = None, None
    if claim.get("measurement_key"):
        meas = evidence.get("measurement")
        if meas is None:
            ev["measurement"] = "MISSING"
            return out("INSUFFICIENT", "Claim needs a measurement that was not run.")
        status, why = _measurement_status(claim, meas)
        ev["measurement"] = status
        trace.append(f"R8 measurement: {status} ({why})")
    if (m is not None and m["status"] == "CONTRADICTS") or status == "DISPUTES":
        return out("DISPUTED", why or "Exact calculation contradicts the claimed value.",
                   rewrite=claim.get("rewrite_hint"))
    if status == "TOO_IMPRECISE":
        return out("INSUFFICIENT", why)

    return out("SUPPORTED", "All required evidence classes agree within the stated scope.",
               rewrite=None)


def _measurement_status(claim, panel):
    """Every row's Bonferroni-adjusted Wilson CI must contain the claimed value and be narrower
    than the claimed tolerance. Any CI excluding the value -> DISPUTES."""
    keys, value, tol = claim["measurement_key"], claim["claimed_value"], claim["tolerance"]
    keys = [keys] if isinstance(keys, str) else keys
    rows = [r for r in panel["rows"] if r["state"] in claim.get("states", [r["state"] for r in panel["rows"]])]
    for r in rows:
        for key in keys:
            lo, hi = r["measured"][key]["ci"]
            if not (lo <= value <= hi):
                return "DISPUTES", (f"state {r['state']} clone {key}: CI [{lo:.4f}, {hi:.4f}] "
                                    f"excludes claimed {value:.4f}")
    widest = max(r["measured"][k]["ci"][1] - r["measured"][k]["ci"][0] for r in rows for k in keys)
    if widest / 2 > tol:
        return "TOO_IMPRECISE", (f"CI half-width {widest / 2:.4f} exceeds claimed tolerance {tol}")
    return "CONSISTENT", f"{len(rows)} CIs contain {value:.4f}; max half-width {widest / 2:.4f} <= {tol}"
