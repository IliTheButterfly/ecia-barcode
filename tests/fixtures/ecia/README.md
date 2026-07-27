# Fixtures

Each pair is the ground truth for one adversarial case, since there is no
reference MH10.8.2 parser to diff against:

| Fixture | Exercises |
|---|---|
| `01_wellformed_digikey` | A clean, fully-standard label. Baseline: confidence 1.0, no warnings. |
| `02_malformed_header_mouser` | Mouser's stray leading `>` before `[)>06`. |
| `03_missing_envelope` | No `[)>`+RS+`06`+GS header at all. |
| `04_missing_terminator` | No RS+EOT — a cropped photo of the label. |
| `05_repeated_di` | The same DI (`1T`, lot code) twice, for a split-reel shipment. |
| `06_embedded_gs` | A real GS byte inside a value, splitting it in two; must be re-glued. |
| `07_longest_di_overlap` | `P`/`1P`/`2P`/`30P` and `K`/`4K` in one payload — every DI here shares its first character with at least one other DI in the table. |

`NAME.bin` is the raw envelope bytes. `NAME.expected.json` was written by
hand from the EIGP-114 / ANSI MH10.8.2 spec, independently of the parser —
see `tests/test_fixtures.py`, which is the only code that reads these
pairs. Do not regenerate the `.expected.json` files from the parser's own
output; that would make the test suite tautological.
