"""Run cloning circuits on the free local BasicSimulator and turn counts into fidelity evidence."""
import math

from qiskit import transpile
from qiskit.providers.basic_provider import BasicSimulator
from qiskit.quantum_info import DensityMatrix, Statevector, partial_trace

from . import circuits
from .stats import wilson, z_for


def exact_fidelities(builder, theta, phi):
    """Mathematical evidence: exact single-copy and joint fidelities from the unmeasured circuit."""
    qc = builder(theta, phi, measure=False)
    sv = Statevector(qc)
    enc = circuits.QuantumCircuit(1)
    circuits._encode(enc, 0, theta, phi)
    psi = Statevector(enc)
    n = qc.num_qubits
    out = {}
    for name, k in (("A", 0), ("B", 1)):
        rho = partial_trace(sv, [j for j in range(n) if j != k])
        out[name] = float(psi.expectation_value(DensityMatrix(rho)).real)
    rho_ab = partial_trace(sv, list(range(2, n))) if n > 2 else DensityMatrix(sv)
    out["AB"] = float(psi.tensor(psi).expectation_value(rho_ab).real)
    return out


def marginals(counts):
    """counts keys are 'c1c0' (Qiskit little-endian): clone A = c0 (right), clone B = c1 (left)."""
    shots = sum(counts.values())
    a0 = sum(v for k, v in counts.items() if k[-1] == "0")
    b0 = sum(v for k, v in counts.items() if k[-2] == "0")
    ab = counts.get("00", 0)
    return shots, {"A": a0, "B": b0, "AB": ab}


def run(builder, theta, phi, shots, seed):
    backend = BasicSimulator()
    qc = builder(theta, phi)
    tqc = transpile(qc, backend, seed_transpiler=seed, optimization_level=0)
    counts = backend.run(tqc, shots=shots, seed_simulator=seed).result().get_counts()
    return dict(sorted(counts.items()))


def measure_panel(builder, shots, seed, states=None, confidence=0.95):
    """One circuit (= one Qollab-sized Run) per input state. Bonferroni over the panel."""
    states = states or circuits.STATES
    z = z_for(confidence, comparisons=len(states))
    rows = []
    for i, (label, (theta, phi)) in enumerate(states.items()):
        counts = run(builder, theta, phi, shots, seed + i)
        n, k = marginals(counts)
        exact = exact_fidelities(builder, theta, phi)
        row = {"state": label, "theta": theta, "phi": phi, "shots": n, "seed": seed + i,
               "counts": counts, "exact": exact, "measured": {}}
        for key in ("A", "B", "AB"):
            lo, hi = wilson(k[key], n, z)
            row["measured"][key] = {"hits": k[key], "f_hat": k[key] / n, "ci": [lo, hi]}
        rows.append(row)
    return {"circuit": builder.__name__, "confidence": confidence, "bonferroni_k": len(states),
            "z": z, "rows": rows}


def circuit_stats(qc):
    ops = dict(qc.count_ops())
    t = transpile(qc, basis_gates=["rz", "sx", "x", "cx", "measure"], optimization_level=1, seed_transpiler=7)
    return {"qubits": qc.num_qubits, "clbits": qc.num_clbits, "depth": qc.depth(), "ops": ops,
            "basis_rz_sx_x_cx": {"depth": t.depth(), "ops": dict(t.count_ops())}}


def worst_case(panel, key):
    return min(r["measured"][key]["ci"][0] for r in panel["rows"]), max(r["measured"][key]["ci"][1] for r in panel["rows"])


def is_close(a, b, tol=1e-9):
    return math.isclose(a, b, abs_tol=tol)
