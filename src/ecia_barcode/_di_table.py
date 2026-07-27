"""The Data Identifier (DI) table this parser understands.

ANSI MH10.8.2 defines a much larger DI set than EIGP-114 actually uses on
component labels; this module carries only the subset the electronic
component distributors listed in the project README emit. Extending
coverage later means adding a row here — nothing else needs to change,
*except* re-running :data:`DI_MATCH_ORDER`'s invariant check (see the test
suite) if a new DI could be a literal prefix of an existing one.
"""

from __future__ import annotations

from typing import Final

#: Data Identifier -> semantic field name (snake_case, matches the
#: :class:`~ecia_barcode.EciaLabel` convenience-property names, minus the
#: aliasing collapse for fields with more than one DI, e.g. revision).
DI_TABLE: Final[dict[str, str]] = {
    "P": "customer_part_number",
    "1P": "supplier_part_number",
    "30P": "revision",
    "2P": "revision",
    "1T": "lot_code",
    "Q": "quantity",
    "9D": "date_code",
    "10D": "date_code",
    "4L": "country_of_origin",
    "K": "purchase_order",
    "4K": "purchase_order",
    "S": "serial",
    "1V": "manufacturer",
    "33P": "bin_code",
}

#: DI codes ordered longest-first so prefix matching never stops at a
#: shorter code when a longer one also matches. See the module docstring
#: on why this matters even though, for the current table, no DI is a
#: literal string-prefix of another (a test asserts that invariant so a
#: future edit that breaks it is caught rather than silently mis-parsed).
DI_MATCH_ORDER: Final[tuple[str, ...]] = tuple(sorted(DI_TABLE, key=len, reverse=True))
