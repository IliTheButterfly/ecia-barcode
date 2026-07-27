"""The confidence penalty table.

:func:`ecia_barcode.parse` starts every label at confidence ``1.0`` and
subtracts one named penalty per degradation it had to work around. Keeping
the numbers here — instead of scattered as magic literals through the
parser — is what makes them auditable and lets a single table-driven test
assert that a more-degraded label never outscores a less-degraded one.

These weights are a judgement call, not a measurement: there is no ground
truth for "how much should a repeated DI cost". They are deliberately
small and additive so that stacking several degradations keeps pushing the
score down (never up), and floor at 0.0 rather than going negative.
"""

from __future__ import annotations

from typing import Final

PENALTIES: Final[dict[str, float]] = {
    # Mouser's stray leading '>' before the '[)>' header. Cosmetic once
    # stripped, so the smallest penalty in the table.
    "malformed_header": 0.05,
    # No '[)>'+RS+'06'+GS envelope at all. We can still split on GS, but
    # we've lost the explicit signal that this is well-formed MH10.8.2.
    "missing_envelope": 0.20,
    # No RS+EOT terminator — usually a cropped photo of the label. We
    # parse what's there, but can't be sure the last field is complete.
    "missing_terminator": 0.10,
    # A DI already seen once on this label. Not wrong (labels legitimately
    # repeat 1T across multiple reels), just a reason to look twice.
    "repeated_di": 0.03,
    # A GS byte turned up inside what looks like a single value; we
    # re-glued the two halves. Charged once per repair attempt.
    "embedded_gs_repaired": 0.08,
    # A token that matched no known DI at all, and that we had no reason
    # to believe was a continuation of the previous field. Kept out of
    # `fields` (there is no DI to key it under) but the raw payload still
    # has it — see `EciaLabel.raw`.
    "unrecognized_fragment": 0.10,
}
