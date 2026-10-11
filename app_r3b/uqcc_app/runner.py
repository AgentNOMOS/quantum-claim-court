"""UQCC-R3b runner: the FROZEN R1 experiment, authorised by backend_policy instead of the R1 allow-list.

This mirrors uqcc_r1.app.run line for line, using only frozen R1 functions (circuit.build,
check_gate_support, interpret, claims.decide_all, canonical, _result_shots). The single difference
is the authorization step: backend_policy.classify(backend) replaces uqcc_r1.app.check_backend.
The measurement evidence keeps the R1 layout (schema uqcc-r1-evidence/1). tests/test_r3b.py proves
that for BasicSimulator this runner and the frozen uqcc_r1.app.run produce byte-identical evidence.

Exactly one bare QuantumCircuit, exactly one backend.run, no transpile, no retry, no fallback.
"""
import hashlib
import json
import platform

from uqcc_r1 import app as r1_app
from uqcc_r1 import circuit, claims, interpret
from uqcc_r1.sources_manifest import MANIFEST_TEXT

from . import backend_policy


def run(backend):
    context = backend_policy.classify(backend)          # raises backend_policy.Refused; no job sent
    ident = r1_app.backend_identity(backend)
    qc = circuit.build()
    gate_check = r1_app.check_gate_support(backend, qc)  # raises r1_app.Refused; no job sent

    jobs = 0
    job = backend.run(qc, shots=r1_app.SHOTS)           # the one and only job; any exception propagates
    jobs += 1
    result = job.result()
    raw = result.get_counts()                          # bare circuit -> single dict
    counts = {str(k): int(v) for k, v in sorted(raw.items())}

    measurement = interpret.interpret(counts, r1_app.SHOTS)
    manifest = json.loads(MANIFEST_TEXT)
    decisions = claims.decide_all(manifest, measurement)
    try:
        import qiskit
        qiskit_version = qiskit.__version__
    except Exception:  # pragma: no cover
        qiskit_version = "unknown"

    evidence = {
        "schema": r1_app.EVIDENCE_SCHEMA,
        "project": "Quantum Claim Court (UQCC-R1 smoke)",
        "backend": ident, "gate_support_check": gate_check,
        "jobs_submitted": jobs, "shots_requested": r1_app.SHOTS,
        "result_shots_field": r1_app._result_shots(result),
        "input_state": {"theta": repr(circuit.THETA), "phi": repr(circuit.PHI),
                        "definition": "|psi> = Rz(phi) Ry(theta) |0>"},
        "circuit": {"metrics": circuit.metrics(qc), "ops": circuit.export_ops(qc)},
        "counts": counts,
        "bit_order": "key = clone[1] clone[0]; clone A = clbit0 = rightmost, clone B = clbit1 = leftmost",
        "measurement": measurement,
        "manifest_sha256": hashlib.sha256(MANIFEST_TEXT.encode("ascii")).hexdigest(),
        "claims": claims.CLAIMS,
        "decisions": decisions,
        "runtime": {"python": platform.python_version(), "qiskit": qiskit_version},
        "scope_note": ("Simulator measurement on one input state. Consistent-with, not proof: the no-cloning "
                       "theorem and the 5/6 optimality bound are literature results and do not originate here."),
    }
    text = r1_app.canonical(evidence)
    return evidence, text, hashlib.sha256(text.encode("ascii")).hexdigest(), context
