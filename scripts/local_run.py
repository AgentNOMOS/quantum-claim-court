"""Reproduce one Run locally: the same bridge Qollab calls (uqcc_app.js_api.run_court), on Qiskit's
local BasicSimulator, UNSEEDED, so every invocation yields genuinely new counts.

This is a local simulator run, not a Qollab run and not hardware.

Usage: python scripts/local_run.py [out_dir] [--r3b]     (writes evidence.txt and console.txt)
       --r3b stages the R3b package (app_r3b/) instead of the R2 package.
"""
import contextlib
import io
import json
import pathlib
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import build_r2_zip  # noqa: E402
import build_r3b_zip  # noqa: E402


def main():
    args = [a for a in sys.argv[1:] if a != "--r3b"]
    r3b = "--r3b" in sys.argv[1:]
    out = pathlib.Path(args[0] if args else "local_run_out")
    out.mkdir(parents=True, exist_ok=True)
    build = build_r3b_zip if r3b else build_r2_zip
    stage = build.stage(pathlib.Path(tempfile.mkdtemp()) / "pkg")    # exact ZIP contents
    sys.path.insert(0, str(stage))
    from qiskit.providers.basic_provider import BasicSimulator
    from uqcc_app import js_api
    console = io.StringIO()
    with contextlib.redirect_stdout(console):
        env = json.loads(js_api.run_court(BasicSimulator()))
    if env["status"] != "ok":
        raise SystemExit(f"run failed: {env}")
    (out / "evidence.txt").write_text(env["export_text"], encoding="ascii")
    (out / "console.txt").write_text(console.getvalue(), encoding="utf-8")
    ev = json.loads(env["r1_evidence_text"])
    print("counts:", ev["counts"])
    for k, o in ev["measurement"]["observables"].items():
        print(f"{k}: {o['estimate']} = {o['estimate_dec']}  99% CI [{o['ci_low']}, {o['ci_high']}]  exact {o['expected']}")
    print("wrote", out / "evidence.txt", "and", out / "console.txt")
    verifier = "verify_uqcc_r3b.py" if r3b else "verify_uqcc_r2.py"
    print("verify with: python3 -I", stage / "verifier" / verifier, out / "evidence.txt", stage)


if __name__ == "__main__":
    main()
