"""The MH10.8.2 / EIGP-114 envelope parser.

Layout of a well-formed label, as bytes::

    [)>  RS  06  GS  <DI><value>  GS  <DI><value>  GS  ...  RS  EOT

- ``[)>`` (3 literal ASCII chars) opens the envelope.
- ``RS`` (0x1E) separates the opener from the format version.
- ``06`` is the ANSI MH10.8.2 format version this parser understands.
- ``GS`` (0x1D) separates fields, including the one right after ``06``.
- ``RS EOT`` (0x1E 0x04) closes the envelope.

Every degradation this module knows how to work around is documented in
the class docstring of `ecia_barcode.EciaLabel` and the penalty table in
`ecia_barcode._penalties`. None of them raise: a scanner produced this
data, a human cannot re-scan a component that already went back in the
bin, and a `ValueError` at that point helps nobody. The only exception
this module raises is `TypeError`, and only for an argument that is
neither `bytes` nor `str`.
"""

from __future__ import annotations

import re
from types import MappingProxyType

from ._di_table import DI_MATCH_ORDER
from ._label import EciaLabel
from ._penalties import PENALTIES

RS = "\x1e"  # Record Separator
GS = "\x1d"  # Group Separator
EOT = "\x04"  # End of Transmission

_HEADER = "[)>" + RS + "06" + GS
_MALFORMED_LEADING_HEADER = ">" + "[)>"
_TERMINATOR = RS + EOT

#: Best-effort shape checks used only to decide whether an unmatched token
#: is likely a continuation of the previous field's value (see
#: `_repair_embedded_gs`). These are *not* a validation contract on the
#: public API — a value that fails its pattern is still returned as-is,
#: verbatim, in `EciaLabel.fields`.
_VALUE_PATTERNS: dict[str, re.Pattern[str]] = {
    "1T": re.compile(r"^[A-Za-z0-9\-]{6,}$"),
    "Q": re.compile(r"^[0-9]+$"),
    "4L": re.compile(r"^[A-Za-z]{2,3}$"),
}
_DEFAULT_VALUE_PATTERN = re.compile(r".*", re.DOTALL)

_MAX_FRAGMENT_IN_WARNING = 24


def parse(raw: bytes | str) -> EciaLabel:
    """Parse one ECIA EIGP-114 / ANSI MH10.8.2 label.

    Accepts `bytes` (what a scanner actually emits) or `str`. Never raises
    on malformed input — see the module docstring — it degrades instead,
    recording a warning and a confidence penalty for each thing it had to
    work around.

    Raises:
        TypeError: `raw` is neither `bytes` nor `str`.
    """
    raw_bytes = _coerce_to_bytes(raw)
    text = raw_bytes.decode("latin-1")

    warnings: list[str] = []
    penalties: list[float] = []

    if text.startswith(_MALFORMED_LEADING_HEADER):
        text = text[1:]
        warnings.append("malformed_header")
        penalties.append(PENALTIES["malformed_header"])

    if text.startswith(_HEADER):
        body = text[len(_HEADER) :]
    else:
        body = text
        warnings.append("missing_envelope")
        penalties.append(PENALTIES["missing_envelope"])

    if body.endswith(_TERMINATOR):
        body = body[: -len(_TERMINATOR)]
    else:
        warnings.append("missing_terminator")
        penalties.append(PENALTIES["missing_terminator"])

    fields = _split_fields(body, warnings, penalties)

    confidence = max(0.0, 1.0 - sum(penalties))
    return EciaLabel(
        raw=raw_bytes,
        fields=MappingProxyType({di: tuple(values) for di, values in fields.items()}),
        warnings=tuple(warnings),
        confidence=confidence,
    )


def _coerce_to_bytes(raw: bytes | str) -> bytes:
    if isinstance(raw, bytes):
        return raw
    if isinstance(raw, str):
        try:
            return raw.encode("latin-1")
        except UnicodeEncodeError:
            # `raw` contains a codepoint above U+00FF, which cannot have
            # come from decoding scanner bytes via latin-1. Genuinely
            # unusual input, but still not a programmer error — fall back
            # to a lossless-for-Unicode encoding rather than raising.
            return raw.encode("utf-8", errors="backslashreplace")
    raise TypeError(f"parse() expects bytes or str, got {type(raw).__name__}")


def _split_fields(body: str, warnings: list[str], penalties: list[float]) -> dict[str, list[str]]:
    """Split the envelope body on GS and resolve each token to a DI.

    Handles repeated DIs (case 4) and a single embedded-GS repair attempt
    per field (case 5) inline, since both need to see fields as they are
    assembled rather than after the fact.
    """
    fields: dict[str, list[str]] = {}
    tokens = [token for token in body.split(GS) if token != ""]

    pending_di: str | None = None
    pending_value = ""
    pending_repaired = False

    def flush() -> None:
        nonlocal pending_di
        if pending_di is None:
            return
        bucket = fields.setdefault(pending_di, [])
        if bucket:
            warnings.append(f"repeated_di:{pending_di}")
            penalties.append(PENALTIES["repeated_di"])
        bucket.append(pending_value)
        pending_di = None

    for token in tokens:
        di = _match_di(token)
        if di is not None:
            flush()
            pending_di = di
            pending_value = token[len(di) :]
            pending_repaired = False
            continue

        # `token` matched no known DI. If the field currently being
        # built looks incomplete (fails its best-effort shape check) and
        # we have not already tried once, assume `token` is the back half
        # of a value that had a GS byte embedded in it, and glue the two
        # halves back together with the separator dropped. Otherwise
        # there is no principled reason to believe `token` belongs to
        # anything — it is warned about and left out of `fields`, since
        # there is no DI to key it under. `EciaLabel.raw` still has it.
        if (
            pending_di is not None
            and not pending_repaired
            and not _validates(pending_di, pending_value)
        ):
            pending_value += token
            pending_repaired = True
            warnings.append(f"embedded_gs_repaired:{pending_di}")
            penalties.append(PENALTIES["embedded_gs_repaired"])
        else:
            warnings.append(f"unrecognized_fragment:{_shorten(token)}")
            penalties.append(PENALTIES["unrecognized_fragment"])

    flush()
    return fields


def _match_di(token: str) -> str | None:
    """The longest DI in the table that prefixes `token`, if any."""
    for di in DI_MATCH_ORDER:
        if token.startswith(di):
            return di
    return None


def _validates(di: str, value: str) -> bool:
    pattern = _VALUE_PATTERNS.get(di, _DEFAULT_VALUE_PATTERN)
    return pattern.fullmatch(value) is not None


def _shorten(token: str) -> str:
    if len(token) > _MAX_FRAGMENT_IN_WARNING:
        token = token[:_MAX_FRAGMENT_IN_WARNING] + "..."
    return ascii(token)
