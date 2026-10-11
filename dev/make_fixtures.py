"""Generate browser-test fixtures from the REAL Python bridge (staged package) with mock backends.

Each fixture is the exact string returned by uqcc_app.js_api.run_court. Fixtures are test inputs
only; they are never shipped and never shown as live measurements.
"""
import contextlib
import io
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import build_r2_zip  # noqa: E402

STAGE = build_r2_zip.stage(ROOT / "dev" / "_stage_fixtures")
sys.path.insert(0, str(STAGE))

from qiskit.providers.basic_provider import BasicSimulator  # noqa: E402
from uqcc_app import js_api  # noqa: E402


class _Res:
    def __init__(self, counts):
        self._c, self.results = counts, [type("R", (), {"shots": sum(counts.values())})()]

    def get_counts(self):
        return self._c


class _Job:
    def __init__(self, r):
        self._r = r

    def result(self):
        return self._r


class Seeded(BasicSimulator):
    def run(self, c, **kw):
        return super().run(c, seed_simulator=1234, **kw)


class Fixed(BasicSimulator):
    """Returns preset counts: used to exercise statistical disagreement in the UI."""
    def __init__(self, counts):
        super().__init__()
        self._counts = counts

    def run(self, c, **kw):
        return _Job(_Res(self._counts))


class Named:
    def __init__(self, name):
        self.name = name


class Raising(BasicSimulator):
    def run(self, c, **kw):
        raise RuntimeError("simulated provider failure")


CASES = {
    "ok": Seeded(),
    # clone A = 00+10 = 1580/2000 = 0.79 -> interval excludes 5/6 (statistical disagreement case)
    "disputed": Fixed({"00": 1240, "01": 420, "10": 340}),
    "refused": Named("ionq_simulator"),
    "error": Raising(),
}


def main():
    out = ROOT / "dev" / "fixtures"
    for name, backend in CASES.items():
        js_api._reset_for_tests()
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            text = js_api.run_court(backend)
        (out / f"{name}.txt").write_text(text, encoding="ascii")
        print(name, json.loads(text)["status"], len(text))


if __name__ == "__main__":
    main()
