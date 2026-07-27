# ecia-barcode

A parser for **ECIA EIGP-114 / ANSI MH10.8.2** 2D barcode labels — the
ECC-200 DataMatrix codes printed on component reels, bags and boxes by
DigiKey, Mouser, Arrow, Newark/Farnell, Avnet, TTI and others.

Zero runtime dependencies. Pure standard library. Python 3.12+.

## Why this exists

Every distributor prints the same underlying format, and no maintained
parser for it exists on PyPI. Every project that needs one hand-rolls a
GS-splitter and a Data Identifier table, usually without handling the
real-world deviations distributors actually ship (see below) — and
usually without noticing the DI table has overlapping prefixes until it
silently mis-parses a label that has both `P` and `1P` on it.

This library exists so that work only has to happen once.

## Install

```bash
pip install ecia-barcode
```

## Usage

```python
from ecia_barcode import parse

label = parse(raw)  # raw: bytes | str — bytes is what a scanner emits

label.customer_part_number  # "TESTPART-001"
label.supplier_part_number  # "CAP-104-X7R"
label.manufacturer  # "KEMET"
label.lot_code  # "LOT20A5Z"
label.quantity  # 2500 (int, or None if absent/non-numeric)
label.date_code  # "2408" — raw string, see below
label.country_of_origin  # "PH"
label.purchase_order  # "PO998877"
label.serial  # None — not on this label
label.revision  # None — not on this label
label.bin_code  # None — not on this label

label.fields  # {"P": ("TESTPART-001",), "1P": ("CAP-104-X7R",), ...}
label.warnings  # () — no degradation on a clean label
label.confidence  # 1.0
label.raw  # the exact bytes passed in, untouched
```

`parse()` returns a frozen `EciaLabel` and does not raise on malformed
input — see [Degrades, never raises](#degrades-never-raises) below. The
only exception it raises is `TypeError`, and only if `raw` is neither
`bytes` nor `str`.

## The envelope

```
[)>  RS  06  GS  <DI><value>  GS  <DI><value>  GS ... RS  EOT
```

- `[)>` (3 literal ASCII characters) opens the envelope.
- `RS` (0x1E, Record Separator) separates the opener from the format
  version.
- `06` is the ANSI MH10.8.2 format version this parser understands.
- `GS` (0x1D, Group Separator) separates fields, including the one right
  after `06`.
- `RS EOT` (0x1E 0x04) closes the envelope.

## Data Identifiers

Matching is **longest-DI-first**: several of these codes share a leading
character with another code in the table (`1P`/`1T`/`10D`/`1V` all start
with `1`; `30P`/`33P` both start with `3`; `4L`/`4K` both start with `4`),
so a shortest-first or unordered match can resolve a token to the wrong
DI. This library sorts the table by length, descending, once, and always
checks longer candidates first.

| DI | Meaning | `EciaLabel` property |
|---|---|---|
| `P` | Customer part number | `customer_part_number` |
| `1P` | Supplier part number | `supplier_part_number` |
| `30P`, `2P` | Revision | `revision` |
| `1T` | Lot code | `lot_code` |
| `Q` | Quantity | `quantity` (parsed to `int`) |
| `9D`, `10D` | Date code | `date_code` (raw string — see below) |
| `4L` | Country of origin | `country_of_origin` |
| `K`, `4K` | Purchase order | `purchase_order` |
| `S` | Serial | `serial` |
| `1V` | Manufacturer | `manufacturer` |
| `33P` | Bin code | `bin_code` |

Where a field has two valid DIs, the convenience property checks them in
the order listed above (e.g. `revision` checks `30P` before `2P`) and
returns the first one present. Both are always available, individually,
via `fields["30P"]` / `fields["2P"]`.

The full table is also available as `ecia_barcode.DI_TABLE`.

### Why `date_code` is a raw string

Distributors do not agree on a date-code format — YYWW, YYMMDD and Julian
day all appear in the wild — and nothing on the label says which one was
used. Guessing would produce a wrong-but-confident date, which is worse
than an unparsed one. `date_code` (and every other field) is therefore
always the literal string from the label. `quantity` is the sole
exception, and only because "not an integer" is unambiguous to detect —
it returns `None` rather than guess if the raw value isn't parseable.

## Degrades, never raises

A barcode scanner produced this data from a physical, possibly damaged or
cropped label. There is no "reject and ask the user to fix it" — the
component already went back in the bin. So `parse()` never raises on
malformed input; it degrades, and tells you how:

| Real-world case | Behaviour |
|---|---|
| Mouser's malformed `>[)>06` header | The stray leading `>` is stripped and parsing continues normally. |
| No `[)>`...`GS` envelope at all | The payload is still split on `GS` and DI-matched field by field. |
| No `RS EOT` terminator (a cropped photo) | Whatever is present is parsed; there's just no confirmation the last field is complete. |
| A repeated DI (e.g. two `1T` lot codes on a split-reel label) | Both values are kept, in order, under the same key — `fields["1T"]` is a tuple. |
| A stray `GS` byte inside a value | If the field looks incomplete, the two halves are re-glued into one value. |

Each of these appends a stable, machine-greppable string to
`label.warnings` and a named penalty (see `ecia_barcode.PENALTIES`) to
`label.confidence`, which starts at `1.0` for a clean label. A more
degraded label never scores higher than a less degraded one.

`label.raw` always holds the exact, untouched input bytes, so a vendor
format this parser doesn't (yet) understand is never destroyed — just
unparsed, and available for later mining.

## Out of scope

**LCSC's label format is not ANSI MH10.8.2-compliant** and is not
supported here. Reverse-engineering it needs real-world samples this
project doesn't have; it belongs in a separate, dedicated handler.

## Development

```bash
uv sync --dev
uv run pytest -q
uv run ruff check . && uv run ruff format --check .
uv run mypy src
```

`tests/fixtures/ecia/` holds hand-verified `NAME.bin` / `NAME.expected.json`
pairs — there is no reference MH10.8.2 parser to diff against, so these
pairs are the ground truth. See `tests/fixtures/ecia/README.md`.
