"""JavaScript bridge for Qollab: main.js calls run_court.callPromising(backend) exactly once.

run_court delegates the quantum work to runner.run: the FROZEN R1 experiment (one bare circuit, one
backend.run, no fallback, no retry) authorised by backend_policy (R3b: BasicSimulator or the free IonQ
remote simulator, positively identified; everything else refused before any job). Returns one JSON string. The evidence texts inside it are
exact strings; JavaScript must display them verbatim and never re-serialise them.
"""
import json

from uqcc_r1 import app as r1_app
from uqcc_r1 import claims as r1_claims
from uqcc_r1.sources_manifest import MANIFEST_TEXT

from . import backend_policy, court, runner
from .source_display import AUTHORS_TEXT

ENVELOPE_SCHEMA = "uqcc-r2-envelope/1"
_STATE = {"calls": 0}


def export_text(r1_text, r1_digest, court_text, court_digest):
    return "\n".join([f"UQCC_R1_EVIDENCE_SHA256={r1_digest}", "UQCC_R1_EVIDENCE_BEGIN", r1_text,
                      "UQCC_R1_EVIDENCE_END", f"UQCC_R2_COURT_SHA256={court_digest}", "UQCC_R2_COURT_BEGIN",
                      court_text, "UQCC_R2_COURT_END"]) + "\n"


def _failure(status, message, job_attempted):
    return json.dumps({"schema": ENVELOPE_SCHEMA, "status": status, "message": message,
                       "job_attempted": job_attempted, "live": False}, ensure_ascii=True)


def run_court(backend=None):
    _STATE["calls"] += 1
    if _STATE["calls"] > 1:
        return _failure("refused", "run_court was already called in this Run; a second quantum job is not allowed.", False)
    if backend is None:
        return _failure("refused", "No injected backend. Zero jobs submitted.", False)
    try:
        backend_policy.classify(backend)
    except backend_policy.Refused as exc:
        return _failure("refused", str(exc), False)
    try:
        evidence, r1_text, r1_digest, context = runner.run(backend)   # the single backend.run
    except (backend_policy.Refused, r1_app.Refused) as exc:
        return _failure("refused", str(exc), False)
    except Exception as exc:  # provider failure: report, never retry
        return _failure("error", f"{type(exc).__name__}: {exc}", True)
    print(r1_app.report(evidence, r1_text, r1_digest))         # console copy, R1 format
    manifest = json.loads(MANIFEST_TEXT)
    court_obj, court_text, court_digest = court.build(evidence, r1_digest, manifest, context)
    decisions = evidence["decisions"] + court_obj["value_decisions"]
    claims_all = r1_claims.CLAIMS + [dict(vc, kind="measurement_value") for vc in court.VALUE_CLAIMS]
    view = {
        "docket": [{"id": c["id"], "text": c["text"], "kind": c["kind"],
                    "needs_measurement": c["id"] in court.NEEDS_MEASUREMENT,
                    "cites": c.get("cites", []), "addendum": c["id"].startswith("V"),
                    "rewrite": court.REWRITE.get(c["id"]),
                    "witness": court.witnesses(d), "decision": d}
                   for c, d in zip(claims_all, decisions)],
        "authors": json.loads(AUTHORS_TEXT),
    }
    return json.dumps({"schema": ENVELOPE_SCHEMA, "status": "ok", "live": True,
                       "r1_evidence_text": r1_text, "r1_evidence_sha256": r1_digest,
                       "court_text": court_text, "court_sha256": court_digest,
                       "manifest_text": MANIFEST_TEXT,
                       "export_text": export_text(r1_text, r1_digest, court_text, court_digest),
                       "view": view}, ensure_ascii=True)


def _reset_for_tests():
    _STATE["calls"] = 0
