"""Build the frozen source manifest from raw retrieval evidence (R0, research-time only).

Metadata (title, authors, year, venue) is copied from the raw Crossref / arXiv
responses saved in evidence/raw/ -- it is never typed by hand. Only the
`propositions` mapping (which claim a source supports, and on what textual
basis) is curated, and each curated entry records its basis level.

The Qollab runtime never calls this script and never contacts a scholarly API.
"""
import hashlib
import json
import pathlib
import xml.etree.ElementTree as ET

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW = ROOT / "evidence" / "raw"
OUT = ROOT / "uqcc" / "sources.json"

# UTC retrieval timestamps as printed by the research shell (see docs/R0_REPORT.md).
CROSSREF_TS = {
    "10.1038/299802a0": "2026-10-10T12:04:44Z",
    "10.1103/PhysRevA.54.1844": "2026-10-10T12:04:44Z",
    "10.1103/PhysRevA.57.2368": "2026-10-10T12:04:44Z",
    "10.1103/PhysRevLett.81.2152": "2026-10-10T12:04:45Z",
    "10.1016/j.tcs.2014.05.025": "2026-10-10T12:04:45Z",
    "10.1103/PhysRevLett.67.661": "2026-10-10T12:04:46Z",
    "10.1098/rspa.1992.0167": "2026-10-10T12:04:46Z",
    "10.1103/RevModPhys.81.1301": "2026-10-10T12:04:56Z",
    "10.1103/PhysRevLett.79.2153": "2026-10-10T12:05:11Z",
    "10.1103/RevModPhys.77.1225": "2026-10-10T12:05:12Z",
    "10.1016/0375-9601(82)90084-6": "2026-10-10T12:05:12Z",
    "10.1103/PhysRevA.56.3446": "2026-10-10T12:05:12Z",
    "10.1103/PhysRevLett.81.3992": "2026-10-10T12:05:13Z",
    "10.1103/PhysRevLett.74.1259": "2026-10-10T12:08:22Z",
}
# DOIs that Crossref answered with HTTP 404 (negative evidence, also frozen).
CROSSREF_404 = {
    "10.1103/PhysRevLett.79.2156": "2026-10-10T12:04:45Z",
    "10.1103/PhysRevLett.130.999999": "2026-10-10T12:08:23Z",
}
ARXIV_TS = "2026-10-10T12:06:18Z"

SOURCE_IDS = {
    "10.1038/299802a0": "WZ82",
    "10.1016/0375-9601(82)90084-6": "DIEKS82",
    "10.1103/PhysRevA.54.1844": "BH96",
    "10.1103/PhysRevA.56.3446": "BBHB97",
    "10.1103/PhysRevLett.79.2153": "GM97",
    "10.1103/PhysRevA.57.2368": "BDEFMS98",
    "10.1103/RevModPhys.77.1225": "SIGA05",
    "10.1103/PhysRevLett.74.1259": "MP95",
    "10.1098/rspa.1992.0167": "DJ92",
    "10.1103/PhysRevLett.67.661": "EKERT91",
    "10.1016/j.tcs.2014.05.025": "BB84_TCS2014",
    "10.1103/RevModPhys.81.1301": "SBCDLP09",
    "10.1103/PhysRevLett.81.2152": "CORY98",
    "10.1103/PhysRevLett.81.3992": "AL98",
}

# basis levels, strongest first:
#   ABSTRACT_TEXT   - proposition stated in the primary abstract (quote stored)
#   TITLE_TEXT      - proposition stated by the primary title itself
#   CURATED         - widely reproduced content, primary text NOT retrieved in R0
PROPOSITIONS = {
    "WZ82": [("P_NOCLONE_UNIVERSAL", "TITLE_TEXT", "A single quantum cannot be cloned")],
    "DIEKS82": [("P_NOCLONE_UNIVERSAL", "CURATED", None)],
    "BH96": [("P_UQCM_EXISTS_INPUT_INDEPENDENT", "ABSTRACT_TEXT",
              "there exists a \"universal quantum copying machine\", which approximately copies "
              "quantum mechanical states in such a way that the quality of its output does not "
              "depend on the input")],
    "BBHB97": [("P_UQCM_GATE_NETWORK", "ABSTRACT_TEXT",
                "a network consisting of quantum gates which produces two imperfect copies of an "
                "arbitrary qubit. The quality of the copies does not depend on the input qubit"),
               ("P_UQCM_EXISTS_INPUT_INDEPENDENT", "ABSTRACT_TEXT",
                "The quality of the copies does not depend on the input qubit")],
    "BDEFMS98": [("P_UQCM_OPTIMAL_5_6", "ABSTRACT_TEXT",
                  "The maximal fidelity of cloning is shown to be 5/6 for universal cloners")],
    "GM97": [("P_QCM_N_TO_M_OPTIMAL", "ABSTRACT_TEXT",
              "we prove that the fidelity (quality) of these copies is optimal")],
    "MP95": [("P_MEASURE_PREPARE_2_3", "CURATED", None)],
    "SIGA05": [("P_UQCM_OPTIMAL_5_6", "CURATED", None)],
}


def crossref_record(doi):
    raw = RAW / (doi.replace("/", "_").replace("(", "_").replace(")", "_") + ".json")
    if not raw.exists():
        raw = RAW / (doi.replace("/", "_") + ".json")
    m = json.loads(raw.read_text())["message"]
    return {
        "doi": m["DOI"].lower(),
        "title": " ".join(m["title"][0].split()),
        "authors": [a.get("family", "") for a in m.get("author", [])],
        "year": m["issued"]["date-parts"][0][0],
        "venue": m["container-title"][0],
        "volume": m.get("volume"),
        "pages": m.get("page"),
        "raw_file": str(raw.relative_to(ROOT)),
        "raw_sha256": hashlib.sha256(raw.read_bytes()).hexdigest(),
    }


def arxiv_records():
    ns = {"a": "http://www.w3.org/2005/Atom", "x": "http://arxiv.org/schemas/atom"}
    root = ET.parse(RAW / "arxiv.xml").getroot()
    out = {}
    for e in root.findall("a:entry", ns):
        doi = e.find("x:doi", ns)
        if doi is None:
            continue
        out[doi.text.lower()] = {
            "arxiv_id": e.find("a:id", ns).text.rsplit("/abs/", 1)[1],
            "abstract": " ".join(e.find("a:summary", ns).text.split()),
        }
    return out


def main():
    arx = arxiv_records()
    sources = []
    for doi, sid in SOURCE_IDS.items():
        rec = {"id": sid, **crossref_record(doi)}
        rec["crossref_http"] = 200
        rec["crossref_retrieved_utc"] = CROSSREF_TS[doi]
        a = arx.get(rec["doi"])
        if a:
            rec["arxiv_id"] = a["arxiv_id"]
            rec["arxiv_retrieved_utc"] = ARXIV_TS
        rec["verification_level"] = "crossref_metadata+arxiv_abstract" if a else "crossref_metadata_only"
        props = []
        for pid, basis, quote in PROPOSITIONS.get(sid, []):
            if basis == "ABSTRACT_TEXT":
                assert a and quote in a["abstract"], (sid, pid)
            if basis == "TITLE_TEXT":
                assert quote.lower() == rec["title"].lower(), (sid, pid)
            props.append({"proposition": pid, "basis": basis, "quote": quote})
        rec["propositions"] = props
        sources.append(rec)
    manifest = {
        "manifest": "UQCC-SOURCES",
        "version": "r0.1",
        "frozen_utc": "2026-10-10T12:08:23Z",
        "notice": ("FROZEN research-time snapshot. Not a live academic search. A SHA-256 of this "
                   "file proves only that the file is unchanged, not where its contents came from."),
        "sources": sources,
        "crossref_not_found": [{"doi": d.lower(), "crossref_http": 404, "checked_utc": t}
                               for d, t in CROSSREF_404.items()],
    }
    OUT.write_text(json.dumps(manifest, indent=1, ensure_ascii=False, sort_keys=True) + "\n")
    print(OUT, hashlib.sha256(OUT.read_bytes()).hexdigest())


if __name__ == "__main__":
    main()
