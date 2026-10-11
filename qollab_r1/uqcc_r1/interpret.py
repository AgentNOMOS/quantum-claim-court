"""Measurement interpretation. Python standard library only.

Decimals in evidence are fixed-width strings (never floats) so the evidence text is stable.
"""
import math
from fractions import Fraction
from statistics import NormalDist

CONFIDENCE = 0.99            # family-wise; measured false-DISPUTED 1.35% over 2000 seeds (95% gave 5.1%)
FAMILY = 3                      # A, B, AB reported together -> Bonferroni over 3 intervals
EXPECTED = {"A": Fraction(5, 6), "B": Fraction(5, 6), "AB": Fraction(2, 3)}
MAX_HALF_WIDTH = 0.05           # above this, the run is too small to say anything


def z_value():
    return NormalDist().inv_cdf(1 - (1 - CONFIDENCE) / FAMILY / 2)


def wilson(k, n, z):
    p = k / n
    den = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / den
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return max(0.0, centre - half), min(1.0, centre + half)


def d6(x):
    return f"{x:.6f}"


def validate_counts(counts, shots, width=2):
    errors = []
    if not isinstance(counts, dict) or not counts:
        return ["counts missing or empty"]
    for key, v in counts.items():
        if not (isinstance(key, str) and len(key) == width and set(key) <= {"0", "1"}):
            errors.append(f"invalid bitstring {key!r}")
        if not (isinstance(v, int) and not isinstance(v, bool) and v >= 0):
            errors.append(f"invalid count for {key!r}")
    if not errors and sum(counts.values()) != shots:
        errors.append(f"counts sum {sum(counts.values())} != requested shots {shots}")
    return errors


def interpret(counts, shots):
    """Clone A = clbit 0 = rightmost character; clone B = clbit 1 = leftmost."""
    errors = validate_counts(counts, shots)
    if errors:
        return {"valid": False, "errors": errors}
    hits = {"A": sum(v for k, v in counts.items() if k[1] == "0"),
            "B": sum(v for k, v in counts.items() if k[0] == "0"),
            "AB": counts.get("00", 0)}
    z = z_value()
    out = {"valid": True, "errors": [], "z": d6(z), "confidence": "0.99", "family": FAMILY, "observables": {}}
    for key in ("A", "B", "AB"):
        lo, hi = wilson(hits[key], shots, z)
        exp = EXPECTED[key]
        out["observables"][key] = {
            "hits": hits[key], "shots": shots, "estimate": f"{hits[key]}/{shots}",
            "estimate_dec": d6(hits[key] / shots), "ci_low": d6(lo), "ci_high": d6(hi),
            "half_width": d6((hi - lo) / 2), "expected": f"{exp.numerator}/{exp.denominator}",
            "contains_expected": lo <= float(exp) <= hi,
            "excludes_perfect_cloning": hi < 1.0,
        }
    return out
