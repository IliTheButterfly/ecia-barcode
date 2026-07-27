"""Table-driven test walking `tests/fixtures/ecia/`.

Each `NAME.bin` / `NAME.expected.json` pair is hand-verified ground truth
(see `tests/fixtures/ecia/README.md`) — there is no reference MH10.8.2
parser to diff against, so these pairs *are* the spec as far as this test
suite is concerned.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from ecia_barcode import parse

FIXTURES_DIR = Path(__file__).parent / "fixtures" / "ecia"

#: Every typed convenience property `EciaLabel` exposes, in the order
#: listed in the project README's DI table.
CONVENIENCE_PROPERTIES = (
    "customer_part_number",
    "supplier_part_number",
    "manufacturer",
    "lot_code",
    "quantity",
    "date_code",
    "country_of_origin",
    "purchase_order",
    "serial",
    "revision",
    "bin_code",
)


def _bin_fixtures() -> list[Path]:
    return sorted(FIXTURES_DIR.glob("*.bin"))


def test_every_bin_fixture_has_a_matching_expected_json() -> None:
    bin_stems = {p.stem for p in FIXTURES_DIR.glob("*.bin")}
    json_stems = {p.name[: -len(".expected.json")] for p in FIXTURES_DIR.glob("*.expected.json")}
    assert bin_stems, "no fixtures found — is FIXTURES_DIR correct?"
    assert bin_stems == json_stems


@pytest.mark.parametrize("bin_path", _bin_fixtures(), ids=lambda p: p.stem)
def test_fixture_matches_expected(bin_path: Path) -> None:
    expected_path = bin_path.parent / f"{bin_path.stem}.expected.json"
    expected: dict[str, Any] = json.loads(expected_path.read_text())

    raw = bin_path.read_bytes()
    label = parse(raw)

    assert label.raw == raw

    actual_fields = {di: list(values) for di, values in label.fields.items()}
    assert actual_fields == expected["fields"]
    assert list(label.warnings) == expected["warnings"]
    assert label.confidence == pytest.approx(expected["confidence"])

    for prop_name in CONVENIENCE_PROPERTIES:
        assert getattr(label, prop_name) == expected[prop_name], (
            f"{bin_path.stem}: {prop_name} mismatch"
        )
