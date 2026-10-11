"""Generate app/uqcc_app/source_display.py: full author lists for display, copied from the raw
Crossref responses in evidence/raw/ (never typed by hand). Display-only; the frozen R1 manifest
remains the authority for evidence levels."""
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW = ROOT / "evidence" / "raw"
FILES = {
    "WZ82": "10.1038_299802a0.json",
    "BH96": "10.1103_PhysRevA.54.1844.json",
    "BBHB97": "10.1103_PhysRevA.56.3446.json",
    "GM97": "10.1103_PhysRevLett.79.2153.json",
    "BDEFMS98": "10.1103_PhysRevA.57.2368.json",
    "DJ92": "10.1098_rspa.1992.0167.json",
    "CORY98": "10.1103_PhysRevLett.81.2152.json",
}


def main():
    out = {}
    for sid, f in FILES.items():
        m = json.loads((RAW / f).read_text(encoding="utf-8"))["message"]
        out[sid] = [" ".join(p for p in (a.get("given", ""), a.get("family", "")) if p) for a in m["author"]]
    text = json.dumps(out, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    dst = ROOT / "app" / "uqcc_app" / "source_display.py"
    dst.write_text('"""Display-only author lists from raw Crossref records (generated; do not edit)."""\n'
                   f"AUTHORS_TEXT = r'''{text}'''\n", encoding="ascii")
    print(dst)


if __name__ == "__main__":
    main()
