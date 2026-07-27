"""The `EciaLabel` result type."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class EciaLabel:
    """The parsed result of one ECIA EIGP-114 / ANSI MH10.8.2 label.

    Every value handed back from this class is either the untouched raw
    string found on the label, or an explicitly best-effort typed
    conversion (currently only :attr:`quantity`). Nothing here is ever
    invented: a field that was not present is ``None`` or an empty tuple,
    never a guess.
    """

    #: The exact bytes `parse()` was given, unmodified. Kept so that
    #: vendor formats this parser does not (yet) understand can be mined
    #: from real-world captures later instead of being lost.
    raw: bytes

    #: Every Data Identifier found on the label, mapped to *all* of its
    #: values in the order they appeared. A tuple (not a single value)
    #: because DIs legitimately repeat — e.g. multiple `1T` lot codes on a
    #: split-reel label.
    fields: Mapping[str, tuple[str, ...]] = field(default_factory=dict)

    #: Stable, machine-greppable strings, one per degradation
    #: `parse()` had to work around. See `ecia_barcode._penalties` for the
    #: full vocabulary and what each one costs `confidence`.
    warnings: tuple[str, ...] = ()

    #: 1.0 for a clean, fully-standard-compliant label, decreasing with
    #: each degradation encountered. See `ecia_barcode.PENALTIES`.
    confidence: float = 1.0

    def _first(self, *di_codes: str) -> str | None:
        """The first value found under any of `di_codes`, in order.

        Used for fields with more than one valid DI (revision is `30P` or
        `2P`; purchase order is `K` or `4K`; date code is `9D` or `10D`).
        The order of `di_codes` as passed by each property below is the
        preference order — it mirrors the DI table's own column order and
        is not a claim that one code is more "correct" than the other.
        """
        for di in di_codes:
            values = self.fields.get(di)
            if values:
                return values[0]
        return None

    @property
    def customer_part_number(self) -> str | None:
        """DI `P` — the customer's own part number for this item."""
        return self._first("P")

    @property
    def supplier_part_number(self) -> str | None:
        """DI `1P` — the supplier's (distributor's) part number."""
        return self._first("1P")

    @property
    def manufacturer(self) -> str | None:
        """DI `1V` — the component manufacturer."""
        return self._first("1V")

    @property
    def lot_code(self) -> str | None:
        """DI `1T` — the manufacturing lot code."""
        return self._first("1T")

    @property
    def quantity(self) -> int | None:
        """DI `Q`, parsed as an integer if it looks like a whole number.

        `None` if `Q` is absent *or* present but not parseable as `int`
        (e.g. it contains a decimal point or stray characters) — the raw
        string is always still available via `fields["Q"]`.
        """
        raw_value = self._first("Q")
        if raw_value is None:
            return None
        try:
            return int(raw_value.strip())
        except ValueError:
            return None

    @property
    def date_code(self) -> str | None:
        """DI `9D` or `10D`, verbatim.

        Distributors disagree on date-code format (YYWW vs. YYMMDD vs.
        Julian day), and there is no marker on the label saying which one
        was used. This deliberately returns the **raw string only** —
        guessing a format would produce a wrong-but-confident date, which
        is worse than an un-parsed one.
        """
        return self._first("9D", "10D")

    @property
    def country_of_origin(self) -> str | None:
        """DI `4L` — country of origin, verbatim (usually ISO 3166)."""
        return self._first("4L")

    @property
    def purchase_order(self) -> str | None:
        """DI `K` or `4K` — the purchase order number."""
        return self._first("K", "4K")

    @property
    def serial(self) -> str | None:
        """DI `S` — a serial number, when the part is serialized."""
        return self._first("S")

    @property
    def revision(self) -> str | None:
        """DI `30P` or `2P` — a revision/version marking."""
        return self._first("30P", "2P")

    @property
    def bin_code(self) -> str | None:
        """DI `33P` — a distributor bin/location code."""
        return self._first("33P")
