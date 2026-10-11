"""UQCC-R1 Qollab smoke run: exactly one bare QuantumCircuit, one backend.run, no fallback, no retry."""
import hashlib
import json
import platform

from . import circuit, claims, interpret
from .sources_manifest import MANIFEST_TEXT

SHOTS = 2000
EVIDENCE_SCHEMA = "uqcc-r1-evidence/1"
ALLOWED_NAMES = {"basic_simulator"}
ALLOWED_CLASSES = {"BasicSimulator"}


class Refused(Exception):
    pass


def backend_identity(backend):
    name = getattr(backend, "name", None)
    name = name() if callable(name) else name
    cls = type(backend)
    return {"name": str(name), "class": f"{cls.__module__}.{cls.__qualname__}", "class_name": cls.__name__}


def check_backend(ident):
    if ident["name"] not in ALLOWED_NAMES and ident["class_name"] not in ALLOWED_CLASSES:
        raise Refused(f"backend {ident['name']!r} / {ident['class']} is not BasicSimulator; R1 runs on the "
                      "simulator only (no IonQ, no hardware). Zero jobs submitted.")


def check_gate_support(backend, qc):
    target = getattr(backend, "target", None)
    names = getattr(target, "operation_names", None)
    if names is None:
        return "target not advertised; not checked"
    missing = sorted({i.operation.name for i in qc.data} - set(names))
    if missing:
        raise Refused(f"backend target lacks {missing}; refusing (no transpile fallback in R1). Zero jobs submitted.")
    return "all circuit operations in backend target"


def canonical(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def run(backend):
    ident = backend_identity(backend)
    check_backend(ident)
    qc = circuit.build()
    gate_check = check_gate_support(backend, qc)

    jobs = 0
    job = backend.run(qc, shots=SHOTS)          # the one and only job; any exception propagates
    jobs += 1
    result = job.result()
    raw = result.get_counts()                  # bare circuit -> single dict
    counts = {str(k): int(v) for k, v in sorted(raw.items())}

    measurement = interpret.interpret(counts, SHOTS)
    manifest = json.loads(MANIFEST_TEXT)
    decisions = claims.decide_all(manifest, measurement)
    try:
        import qiskit
        qiskit_version = qiskit.__version__
    except Exception:  # pragma: no cover
        qiskit_version = "unknown"

    evidence = {
        "schema": EVIDENCE_SCHEMA,
        "project": "Quantum Claim Court (UQCC-R1 smoke)",
        "backend": ident, "gate_support_check": gate_check,
        "jobs_submitted": jobs, "shots_requested": SHOTS,
        "result_shots_field": _result_shots(result),
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
    text = canonical(evidence)
    return evidence, text, hashlib.sha256(text.encode("ascii")).hexdigest()


def _result_shots(result):
    try:
        return int(result.results[0].shots)
    except Exception:
        return None


def report(evidence, text, digest):
    m = evidence["measurement"]
    lines = ["=== UQCC-R1 Quantum Claim Court - cloning smoke test ===",
             f"backend: {evidence['backend']['name']} ({evidence['backend']['class']})",
             f"jobs submitted: {evidence['jobs_submitted']}   shots: {evidence['shots_requested']}",
             f"input: |psi> = Rz(0.7) Ry(1.1) |0>   circuit: {evidence['circuit']['metrics']}",
             f"raw counts: {evidence['counts']}"]
    if m["valid"]:
        for k, label in (("A", "clone A"), ("B", "clone B"), ("AB", "joint  ")):
            o = m["observables"][k]
            lines.append(f"{label}: {o['estimate']} = {o['estimate_dec']}  CI99/Bonf3 [{o['ci_low']}, {o['ci_high']}]"
                         f"  exact {o['expected']}  contains={o['contains_expected']}")
    else:
        lines.append("MEASUREMENT INVALID: " + "; ".join(m["errors"]))
    lines.append("claim decisions:")
    for d in evidence["decisions"]:
        lines.append(f"  {d['id']:<5} {d['verdict']:<12} {d['reason']}")
    lines.append("conclusion: a finite simulator run is CONSISTENT WITH (not proof of) the exact 5/6, 5/6, 2/3 of "
                 "this circuit; no-cloning and 5/6 optimality are literature results, not outputs of this run.")
    lines += [f"UQCC_R1_EVIDENCE_SHA256={digest}", "UQCC_R1_EVIDENCE_BEGIN", text, "UQCC_R1_EVIDENCE_END"]
    return "\n".join(lines)
