"""Parser for ECIA EIGP-114 / ANSI MH10.8.2 distributor barcode labels.

    from ecia_barcode import parse

    label = parse(raw)  # raw: bytes | str

See the project README for the Data Identifier table and the full
"degrades, never raises" contract.
"""

from ._di_table import DI_TABLE
from ._label import EciaLabel
from ._parser import parse
from ._penalties import PENALTIES

__all__ = [
    "DI_TABLE",
    "PENALTIES",
    "EciaLabel",
    "parse",
]

__version__ = "0.1.0"
