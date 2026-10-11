"""Deterministic Qollab upload ZIP for UQCC-R1 (fixed timestamps/permissions, sorted entries)."""
import hashlib
import pathlib
import zipfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
SRC = ROOT / "qollab_r1"
OUT = ROOT / "dist" / "uqcc_r1_qollab_smoke.zip"
FILES = ["LICENSE", "README.md", "main.py",
         "uqcc_r1/__init__.py", "uqcc_r1/app.py", "uqcc_r1/circuit.py", "uqcc_r1/claims.py",
         "uqcc_r1/interpret.py", "uqcc_r1/sources_manifest.py",
         "verifier/verify_uqcc_r1.py"]


def build(out=OUT):
    out.parent.mkdir(exist_ok=True)
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for rel in sorted(FILES):
            info = zipfile.ZipInfo(rel, date_time=(2026, 10, 10, 0, 0, 0))
            info.external_attr = 0o644 << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            z.writestr(info, (SRC / rel).read_bytes())
    return out, hashlib.sha256(out.read_bytes()).hexdigest()


if __name__ == "__main__":
    p, h = build()
    print(p, h)
