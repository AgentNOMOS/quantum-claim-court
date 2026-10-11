# Retrieval record

`raw/` holds the responses retrieved on 2026-10-10 while the source manifest was being researched:
- Crossref REST API (`https://api.crossref.org/works/<DOI>`), 12:04:44–12:08:23 UTC;
- arXiv API, 12:06:18 UTC.

The frozen manifests are generated from these files. Exact per-DOI timestamps are in `scripts/build_manifest.py`.

- Two DOIs returned **HTTP 404**, and their response bodies ("Resource not found.") are kept as negative evidence:
  - `10.1103/PhysRevLett.130.999999` (the fabricated control);
  - `10.1103/PhysRevLett.79.2156` (a mistyped page; the correct DOI is 79.2153).
- **arXiv metadata** (`arxiv.xml`, abstracts included) is CC0 1.0 under the arXiv API Terms of Use.
- **Crossref bibliographic metadata** is factual and reusable.

## Redaction in the public snapshot

- `10.1098_rspa.1992.0167.json` (Deutsch & Jozsa 1992) contained a publisher-deposited `abstract` field. In the public snapshot that field is **removed** and the file is re-serialised. All other fields are unchanged.
- Because of this, the file's SHA-256 differs from the `raw_sha256` recorded in `uqcc/sources.json` (computed on the original response). No test, build or verifier depends on that hash. The R0, R1 and R2 manifests and both ZIPs are unaffected.
- All other raw files are byte-identical to the retrieved responses.
