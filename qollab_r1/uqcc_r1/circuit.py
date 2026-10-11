"""The R0-validated Buzek-Braunstein-Hillery-Bruss 1->2 universal cloner (unchanged from UQCC-R0).

Fixed documented input:  |psi> = Rz(0.7) Ry(1.1) |0>
  = e^{-0.35i} cos(0.55)|0> + e^{+0.35i} sin(0.55)|1>
  Bloch vector (sin1.1 cos0.7, sin1.1 sin0.7, cos1.1) ~= (0.6828, 0.5768, 0.4536)

q0 = input -> clone A, q1 = clone B, q2 = machine qubit.
Machine preparation on (q1, q2): (2|00> + |01> + |11>)/sqrt(6)  (|q1 q2> order).
Readout: undo Rz(0.7)Ry(1.1) on both clones, measure q0 -> clone[0], q1 -> clone[1].
  P(clone A reads 0) = F_A,  P(clone B reads 0) = F_B,  P(both 0) = <psi psi|rho_AB|psi psi>.
"""
import math

from qiskit import ClassicalRegister, QuantumCircuit, QuantumRegister

THETA = 1.1
PHI = 0.7
ALPHA = 2 * math.acos(math.sqrt(5 / 6))
BETA = 2 * math.acos(2 / math.sqrt(5))


def build(theta=THETA, phi=PHI):
    q = QuantumRegister(3, "q")
    c = ClassicalRegister(2, "clone")
    qc = QuantumCircuit(q, c, name="uqcc_bh_cloner")
    qc.ry(theta, 0)
    qc.rz(phi, 0)
    qc.ry(ALPHA, 1)
    qc.ry(BETA, 2)
    qc.cry(math.pi - BETA, 1, 2)
    qc.cx(0, 1)
    qc.cx(0, 2)
    qc.cx(1, 0)
    qc.cx(2, 0)
    for k in (0, 1):
        qc.rz(-phi, k)
        qc.ry(-theta, k)
    qc.measure(0, c[0])
    qc.measure(1, c[1])
    return qc


def export_ops(qc):
    """Gate list of the circuit actually submitted, for the independent verifier."""
    return [{"name": i.operation.name,
             "qubits": [qc.find_bit(x).index for x in i.qubits],
             "clbits": [qc.find_bit(x).index for x in i.clbits],
             "params": [repr(float(p)) for p in i.operation.params]} for i in qc.data]


def metrics(qc):
    return {"qubits": qc.num_qubits, "clbits": qc.num_clbits, "depth": qc.depth(),
            "size": qc.size(), "ops": dict(sorted(qc.count_ops().items()))}
