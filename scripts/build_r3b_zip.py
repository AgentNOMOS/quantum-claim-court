"""Deterministic Qollab ZIP for UQCC-R3b (IonQ free-simulator compatibility RC).

App files come from app_r3b/ (a patched copy of app/; app/ and the R2 ZIP are untouched).
Frozen R1 files are copied byte-for-byte from qollab_r1/ and checked against the uqcc-r1 pins;
the build aborts if any of them differ. The R1 and R2 ZIPs are never touched.
"""
import hashlib
import json
import pathlib
import shutil
import subprocess
import zipfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "dist" / "uqcc_r3b_ionq_compatible_rc.zip"
APP_DIR = "app_r3b"
FROZEN = ["uqcc_r1/__init__.py", "uqcc_r1/app.py", "uqcc_r1/circuit.py", "uqcc_r1/claims.py",
          "uqcc_r1/interpret.py", "uqcc_r1/sources_manifest.py", "verifier/verify_uqcc_r1.py"]
APP = ["index.html", "main.js", "main.css", "ui/logic.js", "ui/render.js", "ui/sha256.js",
       "uqcc_app/__init__.py", "uqcc_app/backend_policy.py", "uqcc_app/court.py", "uqcc_app/js_api.py",
       "uqcc_app/runner.py", "uqcc_app/source_display.py", "verifier/verify_uqcc_r3b.py", "README.md", "LICENSE"]


PINS = ROOT / "scripts" / "frozen_pins.json"


def frozen_check():
    """Frozen files must match the SHA-256 pins recorded from tag uqcc-r1 (works without git history).
    In the development repository the tag itself is compared as well."""
    pins = json.loads(PINS.read_text())["files"]
    for rel in FROZEN:
        if hashlib.sha256((ROOT / "qollab_r1" / rel).read_bytes()).hexdigest() != pins[rel]:
            raise SystemExit(f"FROZEN FILE CHANGED since uqcc-r1: {rel}")
        tagged = subprocess.run(["git", "-C", str(ROOT), "show", f"uqcc-r1:qollab_r1/{rel}"], capture_output=True)
        if tagged.returncode == 0 and tagged.stdout != (ROOT / "qollab_r1" / rel).read_bytes():
            raise SystemExit(f"FROZEN FILE differs from git tag uqcc-r1: {rel}")


def sources():
    return {**{rel: ROOT / "qollab_r1" / rel for rel in FROZEN}, **{rel: ROOT / APP_DIR / rel for rel in APP}}


def stage(dst):
    """Unzipped layout for local tests (same bytes as the ZIP)."""
    dst = pathlib.Path(dst)
    if dst.exists():
        shutil.rmtree(dst)
    for rel, src in sources().items():
        (dst / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, dst / rel)
    return dst


def build(out=OUT):
    frozen_check()
    out = pathlib.Path(out)
    if out.resolve() in {(ROOT / "dist" / n).resolve() for n in ("uqcc_r1_qollab_smoke.zip", "uqcc_r2_claim_court_app.zip")}:
        raise SystemExit("refusing to overwrite a frozen release ZIP")
    out.parent.mkdir(exist_ok=True)
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for rel, src in sorted(sources().items()):
            info = zipfile.ZipInfo(rel, date_time=(2026, 10, 10, 0, 0, 0))
            info.external_attr = 0o644 << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            z.writestr(info, src.read_bytes())
    return out, hashlib.sha256(out.read_bytes()).hexdigest()


if __name__ == "__main__":
    p, h = build()
    print(p, h)
