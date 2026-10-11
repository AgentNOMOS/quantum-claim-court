#!/usr/bin/env python3
"""Exact reference values, computed with the Python standard library only (no Qiskit, no project code).

The circuit is rebuilt from its documented definition:
  input  : Ry(theta), Rz(phi) on q0
  machine: Ry(alpha) q1, Ry(beta) q2, CRy(pi - beta) q1->q2   with cos(alpha/2)=sqrt(5/6), cos(beta/2)=2/sqrt(5)
  copy   : CX(0,1), CX(0,2), CX(1,0), CX(2,0)
  readout: Rz(-phi), Ry(-theta) on q0 and q1; measure q0 -> clone[0], q1 -> clone[1]
Prints P(00), P(01), P(10), P(11) for the live input (theta=1.1, phi=0.7), and checks that the clone
fidelities are 5/6 and the joint fidelity 2/3 on a grid of other inputs (universality of THIS circuit;
this is not a proof that 5/6 is optimal -- that is a literature result).
"""
import cmath
import math


def ry(t):
    c, s = math.cos(t / 2), math.sin(t / 2)
    return ((c, -s), (s, c))


def rz(t):
    return ((cmath.exp(-0.5j * t), 0), (0, cmath.exp(0.5j * t)))


def apply(st, tgt, m, ctrl=None):
    out = list(st)
    for i in range(8):
        if (i >> tgt) & 1 or (ctrl is not None and not (i >> ctrl) & 1):
            continue
        j = i | (1 << tgt)
        out[i], out[j] = m[0][0] * st[i] + m[0][1] * st[j], m[1][0] * st[i] + m[1][1] * st[j]
    return out


X = ((0, 1), (1, 0))


def probabilities(theta, phi):
    alpha, beta = 2 * math.acos(math.sqrt(5 / 6)), 2 * math.acos(2 / math.sqrt(5))
    st = [1] + [0] * 7
    st = apply(st, 0, ry(theta)); st = apply(st, 0, rz(phi))
    st = apply(st, 1, ry(alpha)); st = apply(st, 2, ry(beta)); st = apply(st, 2, ry(math.pi - beta), ctrl=1)
    for c, t in ((0, 1), (0, 2), (1, 0), (2, 0)):
        st = apply(st, t, X, ctrl=c)
    for q in (0, 1):
        st = apply(st, q, rz(-phi)); st = apply(st, q, ry(-theta))
    p = {}
    for i, a in enumerate(st):            # key = clone[1] clone[0] = bit(q1) bit(q0)
        key = f"{(i >> 1) & 1}{i & 1}"
        p[key] = p.get(key, 0) + abs(a) ** 2
    return p


def main():
    p = probabilities(1.1, 0.7)
    print("live input Rz(0.7)Ry(1.1)|0>:", {k: round(v, 12) for k, v in sorted(p.items())})
    assert abs(p["00"] - 2 / 3) < 1e-12 and abs(p["01"] - 1 / 6) < 1e-12 and abs(p["10"] - 1 / 6) < 1e-12 and p["11"] < 1e-24
    worst = 0.0
    for i in range(13):
        for j in range(13):
            q = probabilities(math.pi * i / 12, 2 * math.pi * j / 12)
            fa, fb, fab = q["00"] + q["10"], q["00"] + q["01"], q["00"]
            worst = max(worst, abs(fa - 5 / 6), abs(fb - 5 / 6), abs(fab - 2 / 3))
    print(f"169-input grid: max |F_A-5/6|, |F_B-5/6|, |F_AB-2/3| = {worst:.2e}")
    assert worst < 1e-12
    print("OK: P(00)=2/3, P(01)=P(10)=1/6, P(11)=0; clone fidelities 5/6 and joint 2/3 for every grid input.")


if __name__ == "__main__":
    main()
