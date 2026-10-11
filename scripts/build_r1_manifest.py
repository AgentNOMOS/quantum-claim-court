"""Generate qollab_r1/uqcc_r1/sources_manifest.py from the frozen R0 evidence (no network).

Evidence levels are kept separate and are never inferred from each other:
  SOURCE_METADATA_VERIFIED  Crossref record (DOI -> title/authors/year) retrieved, HTTP 200
  SOURCE_ABSTRACT_CHECKED   the stated quote occurs verbatim in the retrieved arXiv abstract
  SOURCE_TEXT_VERIFIED      full text reviewed -- FALSE for every source in this manifest
The title-only basis for Wootters & Zurek is recorded as TITLE_TEXT, not as an abstract check.
"""
import hashlib
import json
import pathlib
import xml.etree.ElementTree as ET

ROOT = pathlib.Path(__file__).resolve().parent.parent
R0 = json.loads((ROOT / "uqcc" / "sources.json").read_text(encoding="utf-8"))
OUT = ROOT / "qollab_r1" / "uqcc_r1" / "sources_manifest.py"

KEEP = {
    "WZ82": ["quantum_cloning"],
    "BH96": ["quantum_cloning"],
    "BBHB97": ["quantum_cloning", "cloning_circuit"],
    "BDEFMS98": ["quantum_cloning"],
    "GM97": ["quantum_cloning"],
    "DJ92": ["quantum_algorithms"],
    "CORY98": ["quantum_error_correction"],
}

# Statements a source is recorded as making, with the basis on which that was checked.
# Only TITLE_TEXT / ABSTRACT_QUOTE entries exist; anything else is simply absent.
STATEMENTS = {
    "WZ82": [("S_NO_PERFECT_UNIVERSAL_CLONING", "TITLE_TEXT", "A single quantum cannot be cloned")],
    "BH96": [("S_APPROX_UNIVERSAL_COPIER_EXISTS", "ABSTRACT_QUOTE",
              "there exists a \"universal quantum copying machine\", which approximately copies quantum "
              "mechanical states in such a way that the quality of its output does not depend on the input")],
    "BBHB97": [("S_CLONING_GATE_NETWORK", "ABSTRACT_QUOTE",
                "a network consisting of quantum gates which produces two imperfect copies of an arbitrary "
                "qubit. The quality of the copies does not depend on the input qubit")],
    "BDEFMS98": [("S_OPTIMAL_UNIVERSAL_1TO2_FIDELITY_5_6", "ABSTRACT_QUOTE",
                  "The maximal fidelity of cloning is shown to be 5/6 for universal cloners")],
    "GM97": [("S_NM_CLONING_OPTIMALITY_PROVED", "ABSTRACT_QUOTE",
              "we prove that the fidelity (quality) of these copies is optimal")],
}

# Mathematical results register. "Established" refers to the published literature (or, for
# M_THIS_CIRCUIT, to exact computation); none of these originate from the measurement.
MATH = [
    {"id": "M_NO_CLONING", "statement": "No unitary process maps |psi>|0>|M> to |psi>|psi>|M_psi> for all "
     "unknown pure qubit states |psi> (no-cloning theorem).",
     "status": "MATHEMATICAL_RESULT_ESTABLISHED", "origin": "literature", "sources": ["WZ82"],
     "note": "Established by linearity arguments in the literature; NOT derived from or proved by this "
             "experiment. WZ82 support is title-level; full text not reviewed by us."},
    {"id": "M_OPT_5_6", "statement": "For deterministic, symmetric, universal 1->2 qubit cloning the maximal "
     "single-copy fidelity is 5/6.",
     "status": "MATHEMATICAL_RESULT_ESTABLISHED", "origin": "literature", "sources": ["BDEFMS98", "GM97"],
     "note": "Abstract-level check only. Scope: deterministic, symmetric, universal, 1->2, qubits. Does NOT "
             "transfer to asymmetric, probabilistic, state-dependent or N->M cloning."},
    {"id": "M_THIS_CIRCUIT", "statement": "For the shipped 3-qubit circuit, single-copy fidelities are exactly "
     "5/6 and 5/6, and the joint fidelity <psi psi|rho_AB|psi psi> is exactly 2/3, for every input state.",
     "status": "MATHEMATICAL_RESULT_ESTABLISHED", "origin": "exact_computation",
     "sources": ["BBHB97"],
     "note": "Computed exactly (state vector) in R0 and recomputed by the stdlib verifier from the gate list "
             "that was actually submitted. Says nothing about optimality."},
]


def main():
    by_id = {s["id"]: s for s in R0["sources"]}
    arxiv = " ".join((ROOT / "evidence/raw/arxiv.xml").read_text(encoding="utf-8").split())
    sources = []
    for sid, topics in KEEP.items():
        s = by_id[sid]
        stmts = []
        for st, basis, quote in STATEMENTS.get(sid, []):
            if basis == "ABSTRACT_QUOTE":
                assert "arxiv_id" in s and quote in arxiv, (sid, st)
            if basis == "TITLE_TEXT":
                assert quote.lower() == s["title"].lower()
            stmts.append({"statement": st, "basis": basis, "quote": quote})
        sources.append({
            "id": sid, "doi": s["doi"], "title": s["title"], "first_author": s["authors"][0],
            "year": s["year"], "venue": s["venue"], "volume": s["volume"], "pages": s["pages"],
            "topics": topics,
            "levels": {
                "SOURCE_METADATA_VERIFIED": {"value": True, "how": "Crossref REST API, HTTP 200",
                                             "utc": s["crossref_retrieved_utc"]},
                "SOURCE_ABSTRACT_CHECKED": ({"value": True, "how": "arXiv API abstract " + s["arxiv_id"],
                                             "utc": s["arxiv_retrieved_utc"]} if "arxiv_id" in s else
                                            {"value": False, "how": "no abstract retrieved"}),
                "SOURCE_TEXT_VERIFIED": {"value": False, "how": "full text not reviewed"},
            },
            "statements": stmts,
        })
    manifest = {
        "manifest": "UQCC-R1-SOURCES", "version": "r1.0", "derived_from": "UQCC-R0 sources.json r0.1",
        "r0_manifest_sha256": hashlib.sha256((ROOT / "uqcc" / "sources.json").read_bytes()).hexdigest(),
        "frozen_utc": R0["frozen_utc"],
        "notice": "FROZEN offline snapshot; not a live academic search. Its SHA-256 shows the text is "
                  "unchanged, not who wrote it or where it came from.",
        "sources": sources,
        "crossref_not_found": R0["crossref_not_found"],
        "math_results": MATH,
    }
    text = json.dumps(manifest, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    assert "'''" not in text and not text.endswith("\\")  # raw literal keeps \uXXXX and \" verbatim
    body = ('"""Frozen offline source manifest (generated by scripts/build_r1_manifest.py; do not edit)."""\n'
            f"MANIFEST_TEXT = r'''{text}'''\n")
    OUT.write_text(body, encoding="ascii")
    print(OUT, hashlib.sha256(text.encode("ascii")).hexdigest())


if __name__ == "__main__":
    main()
