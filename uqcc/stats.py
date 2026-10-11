"""Stdlib-only statistics (shared by the app; the verifier has its own copy on purpose)."""
import math
from statistics import NormalDist


def z_for(confidence=0.95, comparisons=1):
    """Two-sided z with Bonferroni correction over `comparisons` simultaneous intervals."""
    alpha = (1 - confidence) / comparisons
    return NormalDist().inv_cdf(1 - alpha / 2)


def wilson(k, n, z):
    if n <= 0:
        raise ValueError("n must be positive")
    p = k / n
    den = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / den
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return max(0.0, centre - half), min(1.0, centre + half)
