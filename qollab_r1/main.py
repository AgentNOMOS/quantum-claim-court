"""Qollab entrypoint. Uses ONLY the backend injected by Qollab as the global name `backend`.

No backend is ever created here: no local-simulator fallback, no retries, exactly one job.
"""
from uqcc_r1 import app

try:
    _backend = backend  # noqa: F821  (injected by Qollab)
except NameError:
    raise SystemExit("UQCC-R1 REFUSED: no injected `backend` global. Run inside Qollab. Zero jobs submitted.")

try:
    _evidence, _text, _digest = app.run(_backend)
except app.Refused as exc:
    raise SystemExit(f"UQCC-R1 REFUSED: {exc}")

print(app.report(_evidence, _text, _digest))
