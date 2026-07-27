# ecia-barcode

Parser for **ECIA EIGP-114 / ANSI MH10.8.2** 2D barcode labels — the ECC-200
DataMatrix codes printed on component reels and bags by DigiKey, Mouser, Arrow,
Newark/Farnell, Avnet, TTI and others.

**Status: not yet implemented.** Extracted from
[almagest](https://github.com/IliTheButterfly/almagest).

## Why this exists

No maintained parser for this format exists on PyPI. Every project that needs it
hand-rolls a splitter and a Data Identifier table.

## Scope

- The `[)>`+RS+`06`+GS envelope, GS-delimited `<DI><value>` fields, RS+EOT terminator
- Longest-match DI resolution — identifiers overlap as prefixes (`1P` vs `P`)
- Real-world deviations, all non-fatal: Mouser's malformed `>[)>06` header,
  missing envelopes, missing terminators, repeated DIs, cropped payloads

LCSC labels are *not* standard-compliant and are out of scope.
