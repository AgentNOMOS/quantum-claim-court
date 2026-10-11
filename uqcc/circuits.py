"""Quantum circuits for the no-cloning claim court.

Input encoding: |psi(theta, phi)> = Rz(phi) Ry(theta) |0>  (global phase irrelevant).

Fidelity readout: for a clone qubit with reduced state rho, F = <psi|rho|psi>.
Applying U^dagger = Ry(-theta) Rz(-phi) to that qubit and measuring Z gives
P(0) = F exactly, so each clone's fidelity is a measured outcome frequency.
Undoing U on BOTH clones in the same shot also gives the joint (two-copy)
fidelity <psi psi|rho_AB|psi psi> = P(00).
"""
import math

from qiskit import ClassicalRegister, QuantumCircuit, QuantumRegister

# Machine (ancilla) preparation for the Buzek-Braunstein-Hillery-Bruss 1->2
# network [BBHB97], qubits (b, c):  (2|00> + |01> + |11>) / sqrt(6)   (|b c> order).
# Factorisation: b: cos(a/2)=sqrt(5/6); c|b=0: (2|0>+|1>)/sqrt(5); c|b=1: |1>.
ALPHA = 2 * math.acos(math.sqrt(5 / 6))
BETA = 2 * math.acos(2 / math.sqrt(5))


def _encode(qc, q, theta, phi):
    qc.ry(theta, q)
    qc.rz(phi, q)


def _decode(qc, q, theta, phi):
    qc.rz(-phi, q)
    qc.ry(-theta, q)


def bh_cloner(theta, phi, measure=True):
    """3-qubit universal 1->2 cloner. q0 = input / clone A, q1 = clone B, q2 = machine."""
    q = QuantumRegister(3, "q")
    qc = QuantumCircuit(q, name="bh_cloner")
    _encode(qc, 0, theta, phi)
    qc.ry(ALPHA, 1)
    qc.ry(BETA, 2)
    qc.cry(math.pi - BETA, 1, 2)
    qc.cx(0, 1)
    qc.cx(0, 2)
    qc.cx(1, 0)
    qc.cx(2, 0)
    if measure:
        c = ClassicalRegister(2, "clone")
        qc.add_register(c)
        _decode(qc, 0, theta, phi)
        _decode(qc, 1, theta, phi)
        qc.measure(0, c[0])
        qc.measure(1, c[1])
    return qc


def cnot_copier(theta, phi, measure=True):
    """2-qubit 'copy by CNOT' (a classical-bit fan-out applied to a qubit). q0 = original, q1 = copy."""
    q = QuantumRegister(2, "q")
    qc = QuantumCircuit(q, name="cnot_copier")
    _encode(qc, 0, theta, phi)
    qc.cx(0, 1)
    if measure:
        c = ClassicalRegister(2, "clone")
        qc.add_register(c)
        _decode(qc, 0, theta, phi)
        _decode(qc, 1, theta, phi)
        qc.measure(0, c[0])
        qc.measure(1, c[1])
    return qc


def flagship_circuit():
    """The single bare QuantumCircuit for one Qollab Run: BH cloner on a generic, non-basis input."""
    return bh_cloner(1.1, 0.7)


# Test-state panel: the 6 Pauli eigenstates + 2 fixed generic states.
STATES = {
    "Z+": (0.0, 0.0),
    "Z-": (math.pi, 0.0),
    "X+": (math.pi / 2, 0.0),
    "X-": (math.pi / 2, math.pi),
    "Y+": (math.pi / 2, math.pi / 2),
    "Y-": (math.pi / 2, -math.pi / 2),
    "G1": (1.1, 0.7),
    "G2": (2.3, -1.9),
}
