"""
fsparam.py - Czytnik binarnych plikow PARAM (FSParam) z FromSoftware.

Obsluguje dwa warianty naglowka:
  * DS1/DSR  - detype (nazwy kolumn) jest WBUDOWANY w plik, wiekszosc pol to
                wartosci proste; wariant "wide" (RefType) trzyma 2-bajtowy
                wskaznik do stringu w tabeli stringow.
  * ER       - detype jest ZEWNATRZNY (pliki Names1/Names2 w regulation.bin),
                dlatego naglowek jest inny: dwa offsety (dane, nazwy) + para
                (liczba kolumn, liczba wierszy).

Ponadto: dcx.py w tym samym katalogu obsluguje kompresje DCX, a bnd.py -
archiwa BND3/BND4.
"""
from __future__ import annotations

import struct
from dataclasses import dataclass, field
from typing import Any

# Typy podstawowe -> (kod rozmiaru, struct format)
PRIM = {
    "sbyte": (1, "b"), "byte": (1, "B"),
    "short": (2, "h"), "ushort": (2, "H"),
    "int": (4, "i"), "uint": (4, "I"),
    "long": (8, "q"), "ulong": (8, "Q"),
    "float": (4, "f"), "double": (8, "d"),
}
ALIAS = {
    "s8": "sbyte", "u8": "byte", "i16": "short", "u16": "ushort",
    "i32": "int", "u32": "uint", "i64": "long", "u64": "ulong",
    "f32": "float", "f64": "double", "bool": "byte",
}
# Rodzaje kolumn w FSParam
KIND_VALUE = 0     # zwykla wartosc
KIND_REF = 1       # referencja do innej tabeli (RefType)
KIND_BIT = 2       # bitfield (wskaznik + maska bitowa)
KIND_PAD = 3       # wypelnienie


@dataclass
class Column:
    name: str
    type: str = "int"
    kind: int = KIND_VALUE
    array_size: int = 0
    bit_count: int = 0
    bit_offset: int = 0
    ref_type: str | None = None
    wide: bool = False          # pole RefType z 2-bajtowym wskaznikiem
    default: Any = None

    @property
    def size(self) -> int:
        n = PRIM.get(self.type, (4, "i"))[0]
        if self.kind == KIND_REF:
            # referencja: wartosc (4B) + wskaznik (4B lub 2B) [+ wartosc domyslna]
            return n + (2 if self.wide else 4)
        if self.kind == KIND_BIT:
            return PRIM.get(self.type, (4, "i"))[0]
        if self.kind == KIND_PAD:
            return n
        return n * max(1, self.array_size)


@dataclass
class Row:
    id: int
    values: dict[str, Any] = field(default_factory=dict)
    strings: dict[str, str] = field(default_factory=dict)

    def get(self, key: str, default: Any = None) -> Any:
        if key in self.values:
            return self.values[key]
        if key in self.strings:
            return self.strings[key]
        return default


@dataclass
class ParamFile:
    rows: list[Row] = field(default_factory=list)
    columns: list[Column] = field(default_factory=list)
    row_size: int = 0
    detype: str = ""
    param_type: str = ""
    variant: str = "ds1"

    def col(self, name: str) -> Column | None:
        low = name.lower()
        for c in self.columns:
            if c.name.lower() == low:
                return c
        return None


# ---------------------------------------------------------------------------
# DS1 / DSR: detype wewnetrzny
# ---------------------------------------------------------------------------

def _cstr(data: bytes, pos: int) -> tuple[str, int]:
    end = data.find(b"\x00", pos)
    if end == -1:
        end = len(data)
    return data[pos:end].decode("utf-8", errors="replace"), end + 1


def parse_ds1_param(data: bytes) -> ParamFile:
    """Parsuj PARAM w formacie DS1/DSR (detype wewnetrzny)."""
    if len(data) < 0x10:
        raise ValueError("za krotki plik PARAM")
    unused, row_size, row_count, string_size = struct.unpack_from("<IHHI", data, 0)
    detype_size = struct.unpack_from("<I", data, 0x0C)[0]
    detype_raw = data[0x10 : 0x10 + detype_size]
    detype = detype_raw.rstrip(b"\x00").decode("utf-8", errors="replace")

    columns = _parse_detype_ds1(detype)

    rows_start = 0x10 + detype_size
    # tabela stringow: po wierszach
    str_start = rows_start + row_size * row_count
    string_area = data[str_start : str_start + string_size]

    rows: list[Row] = []
    for i in range(row_count):
        off = rows_start + i * row_size
        rows.append(_parse_row_ds1(data, off, columns, string_area))
    return ParamFile(rows=rows, columns=columns, row_size=row_size, detype=detype,
                     param_type=detype.split(":")[0] if ":" in detype else detype, variant="ds1")


def _parse_detype_ds1(detype: str) -> list[Column]:
    """Nazwy kolumn z detype DS1: 'EquipParamWeapon:fieldA,fieldB,...'"""
    body = detype.split(":", 1)[1] if ":" in detype else detype
    cols: list[Column] = []
    for name in body.split(","):
        name = name.strip()
        if name:
            cols.append(Column(name=name, type="int"))
    return cols


# ---------------------------------------------------------------------------
# ER: detype zewnetrzny (definicja z Paramdex)
# ---------------------------------------------------------------------------

def parse_er_param(data: bytes, columns: list[Column]) -> ParamFile:
    """Parsuj PARAM w formacie ER, korzystajac z definicji kolumn.

    Naglowek ER (po rozpakowaniu z regulation.bin):
      0x00 u32  offset tablicy nazw (koniec danych wierszy)
      0x04 u32  offset danych wierszy
      0x08 u32  (liczba kolumn | liczba wierszy << 16) - do weryfikacji
      0x0C u32  0
      0x10 u32  offset tablicy nazw (powtorzony)
    """
    names_offset, data_offset, packed, _zero, _names2 = struct.unpack_from("<5I", data, 0)
    n_cols = packed & 0xFFFF
    n_rows = (packed >> 16) & 0xFFFF

    rows: list[Row] = []
    off = data_offset
    for _ in range(n_rows):
        if off + 8 > len(data):
            break
        row = _parse_row_er(data, off, columns)
        rows.append(row)
        off += row.width
    return ParamFile(rows=rows, columns=columns, row_size=0, detype="", param_type="", variant="er")


@dataclass
class ErRow(Row):
    width: int = 0


def _parse_row_er(data: bytes, off: int, columns: list[Column]) -> Row:
    row = ErRow(id=struct.unpack_from("<i", data, off)[0], width=0)
    pos = off + 8  # id (4) + 4 bajty rezerwy
    for col in columns:
        if col.kind == KIND_PAD:
            pos += PRIM.get(col.type, (4, "i"))[0]
            continue
        n, code = PRIM.get(col.type, (4, "i"))
        if col.kind == KIND_BIT:
            raw = struct.unpack_from("<" + code, data, pos)[0]
            pos += n
            row.values[col.name] = (raw >> col.bit_offset) & ((1 << col.bit_count) - 1)
        elif col.kind == KIND_REF:
            raw = struct.unpack_from("<" + code, data, pos)[0]
            pos += n
            row.values[col.name] = raw
            if col.wide:
                slen = struct.unpack_from("<H", data, pos)[0]
                pos += 2
                row.strings[col.name] = data[pos : pos + slen].decode("utf-8", errors="replace")
                pos += slen
            else:
                soff = struct.unpack_from("<I", data, pos)[0]
                pos += 4
        else:
            if col.array_size:
                arr = [struct.unpack_from("<" + code, data, pos + i * n)[0] for i in range(col.array_size)]
                pos += n * col.array_size
                row.values[col.name] = arr
            else:
                row.values[col.name] = struct.unpack_from("<" + code, data, pos)[0]
                pos += n
    row.width = pos - off
    return row


def _parse_row_ds1(data: bytes, off: int, columns: list[Column], string_area: bytes) -> Row:
    row = Row(id=struct.unpack_from("<i", data, off)[0])
    pos = off + 8
    for col in columns:
        n, code = PRIM.get(col.type, (4, "i"))
        if col.kind == KIND_REF:
            raw = struct.unpack_from("<" + code, data, pos)[0]
            pos += n
            row.values[col.name] = raw
            if col.wide:
                slen = struct.unpack_from("<H", data, pos)[0]
                pos += 2
                row.strings[col.name] = data[pos : pos + slen].decode("utf-8", errors="replace")
                pos += slen
            else:
                soff = struct.unpack_from("<I", data, pos)[0]
                pos += 4
                if soff < len(string_area):
                    end = string_area.find(b"\x00", soff)
                    end = len(string_area) if end == -1 else end
                    row.strings[col.name] = string_area[soff:end].decode("utf-8", errors="replace")
        else:
            if col.array_size:
                arr = [struct.unpack_from("<" + code, data, pos + i * n)[0] for i in range(col.array_size)]
                pos += n * col.array_size
                row.values[col.name] = arr
            else:
                row.values[col.name] = struct.unpack_from("<" + code, data, pos)[0]
                pos += n
    return row
