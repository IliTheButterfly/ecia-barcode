"""Invariants on the DI table itself, independent of any fixture.

If a future edit adds a DI that IS a literal prefix of another DI (unlike
every pair in the table today), longest-match-first stops being a no-op
optimization and starts being load-bearing. This test exists so that edit
fails loudly here instead of silently mis-parsing a real label.
"""

from __future__ import annotations

from ecia_barcode import DI_TABLE
from ecia_barcode._di_table import DI_MATCH_ORDER


def test_di_match_order_is_longest_first() -> None:
    lengths = [len(di) for di in DI_MATCH_ORDER]
    assert lengths == sorted(lengths, reverse=True)


def test_di_match_order_contains_every_table_entry_exactly_once() -> None:
    assert set(DI_MATCH_ORDER) == set(DI_TABLE)
    assert len(DI_MATCH_ORDER) == len(DI_TABLE)


def test_no_di_is_a_literal_prefix_of_another() -> None:
    codes = list(DI_TABLE)
    offenders = [
        (short, long_)
        for short in codes
        for long_ in codes
        if short != long_ and long_.startswith(short)
    ]
    assert offenders == []


def test_every_di_shares_a_first_character_with_at_least_one_other() -> None:
    # Documents *why* longest-match-first matters for this table: it's not
    # a hypothetical future concern, first characters already collide.
    first_chars = [di[0] for di in DI_TABLE]
    collisions = {c for c in first_chars if first_chars.count(c) > 1}
    assert collisions, "expected at least one shared leading character across DIs"
