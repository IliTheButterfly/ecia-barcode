"""Ordinary unit tests: empty/garbage input, type handling, and the
convenience-property logic that isn't already covered by a fixture."""

from __future__ import annotations

import pytest

from ecia_barcode import EciaLabel, parse

RS = "\x1e"
GS = "\x1d"
EOT = "\x04"
HEADER = "[)>" + RS + "06" + GS
TERMINATOR = RS + EOT


def _envelope(*fields: str) -> bytes:
    """A well-formed envelope wrapping `fields` (each already `<DI><value>`)."""
    return (HEADER + GS.join(fields) + TERMINATOR).encode("latin-1")


# ---------------------------------------------------------------------------
# Empty / degenerate input
# ---------------------------------------------------------------------------


def test_empty_bytes_does_not_raise() -> None:
    label = parse(b"")
    assert label.fields == {}
    assert label.raw == b""
    assert "missing_envelope" in label.warnings
    assert "missing_terminator" in label.warnings


def test_empty_str_does_not_raise() -> None:
    label = parse("")
    assert label.fields == {}
    assert label.confidence < 1.0


def test_whitespace_only_does_not_raise() -> None:
    label = parse("   ")
    assert label.fields == {}
    assert any(w.startswith("unrecognized_fragment:") for w in label.warnings)


def test_garbage_bytes_does_not_raise() -> None:
    garbage = bytes([0xFF, 0x00, 0x01, 0x02, 0xAB, 0xCD, 0x7F])
    label = parse(garbage)
    assert isinstance(label, EciaLabel)
    assert label.raw == garbage
    assert 0.0 <= label.confidence <= 1.0


# ---------------------------------------------------------------------------
# bytes vs str
# ---------------------------------------------------------------------------


def test_bytes_and_str_equivalent_input_parse_identically() -> None:
    raw_bytes = _envelope("P" + "SAMEPART", "Q" + "10")
    raw_str = raw_bytes.decode("latin-1")

    from_bytes = parse(raw_bytes)
    from_str = parse(raw_str)

    assert from_bytes == from_str
    assert from_bytes.raw == from_str.raw == raw_bytes


def test_wrong_argument_type_raises_type_error() -> None:
    with pytest.raises(TypeError):
        parse(12345)  # type: ignore[arg-type]


def test_none_argument_raises_type_error() -> None:
    with pytest.raises(TypeError):
        parse(None)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Confidence monotonicity — more degradation must never score higher.
# ---------------------------------------------------------------------------


def test_confidence_monotonicity_across_degradation_levels() -> None:
    clean = parse(_envelope("P" + "CLEANPART"))

    missing_envelope_only = parse(("P" + "NOENV" + GS + "Q" + "1" + TERMINATOR).encode("latin-1"))

    missing_both = parse(("P" + "NOENV" + GS + "Q" + "1").encode("latin-1"))

    assert clean.confidence == 1.0
    assert missing_envelope_only.confidence < clean.confidence
    assert missing_both.confidence < missing_envelope_only.confidence


def test_confidence_never_negative() -> None:
    # Stack several degradations onto one payload: no envelope, no
    # terminator, a leading orphan fragment, a too-short '1T' that
    # triggers one repair attempt, and a second orphan that exhausts it.
    raw = (
        ">"
        + "P"
        + "A"
        + GS
        + "1T"
        + "X"  # too short for its shape check
        + GS
        + "???"  # orphan; gets glued onto '1T' (its one repair attempt)
        + GS
        + "9Z"  # unknown DI entirely; '1T' has no repair attempts left
        + "MORE"
    ).encode("latin-1")
    label = parse(raw)
    assert 0.0 <= label.confidence <= 1.0


# ---------------------------------------------------------------------------
# Convenience-property behaviour not already covered by a fixture.
# ---------------------------------------------------------------------------


def test_quantity_is_none_when_not_numeric() -> None:
    label = parse(_envelope("Q" + "N/A"))
    assert label.fields["Q"] == ("N/A",)
    assert label.quantity is None


def test_quantity_is_none_when_absent() -> None:
    label = parse(_envelope("P" + "NOQTY"))
    assert label.quantity is None


def test_date_code_prefers_9d_over_10d_when_both_present() -> None:
    label = parse(_envelope("9D" + "2409", "10D" + "20240315"))
    assert label.date_code == "2409"


def test_date_code_falls_back_to_10d_when_9d_absent() -> None:
    label = parse(_envelope("10D" + "20240315"))
    assert label.date_code == "20240315"


def test_purchase_order_falls_back_to_4k_when_k_absent() -> None:
    label = parse(_envelope("4K" + "PO-ONLY-4K"))
    assert label.purchase_order == "PO-ONLY-4K"


def test_revision_falls_back_to_2p_when_30p_absent() -> None:
    label = parse(_envelope("2P" + "REV-ONLY-2P"))
    assert label.revision == "REV-ONLY-2P"


def test_serial_and_bin_code() -> None:
    label = parse(_envelope("S" + "SN00042", "33P" + "BIN-A7"))
    assert label.serial == "SN00042"
    assert label.bin_code == "BIN-A7"


def test_unknown_di_is_dropped_from_fields_but_never_loses_raw_bytes() -> None:
    raw = _envelope("P" + "KNOWNPART", "9Z" + "SOMEVALUE")
    label = parse(raw)
    assert "9Z" not in label.fields
    assert "P" in label.fields
    assert any(w.startswith("unrecognized_fragment:") for w in label.warnings)
    assert label.confidence < 1.0
    assert label.raw == raw


def test_fields_is_read_only_mapping() -> None:
    label = parse(_envelope("P" + "X"))
    with pytest.raises(TypeError):
        label.fields["P"] = ("Y",)  # type: ignore[index]


def test_label_is_frozen() -> None:
    label = parse(_envelope("P" + "X"))
    with pytest.raises(AttributeError):
        label.confidence = 0.0  # type: ignore[misc]
