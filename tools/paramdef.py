"""
paramdef.py - Czytnik definicji kolumn PARAM z Paramdex (XML) i z plikow .xml.

Format "Def" w Paramdex:
    "s32 behaviorVariationId"        -> typ + nazwa
    "u8 disableParam_NT:1"           -> pole bitowe (nazwa:liczba_bitow)
    "dummy8 disableParamReserve2[3]" -> tablica
    "f32 poiseHealthBar"             -> zwykla wartosc
    "f32 dummy4[4]"                  -> tablica floatow
    "RefType a:4"                    -> referencja
"""
from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from typing import Any

from fsparam import ALIAS, KIND_BIT, KIND_PAD, KIND_REF, KIND_VALUE, Column


@dataclass
class ParamDef:
    param_type: str = ""
    columns: list[Column] = field(default_factory=list)
    raw_defs: list[str] = field(default_factory=list)
    bit_order: list[tuple[str, int]] = field(default_factory=list)


_TYPE_RE = re.compile(r"^(?P<type>[a-zA-Z0-9]+)\s+(?P<name>[^\[:]+?)(?P<array>\[\d+\])?(?P<bit>:\d+)?$")


def _norm_type(t: str) -> str:
    t = t.strip().lower()
    t = ALIAS.get(t, t)
    if t in ("sbyte", "byte", "short", "ushort", "int", "uint", "long", "ulong", "float", "double"):
        return t
    if t in ("dummy8", "dummy"):
        return "byte"
    if t in ("s8", "u8", "i16", "u16", "i32", "u32", "i64", "u64", "f32", "f64"):
        return ALIAS[t]
    if t.startswith("dummy"):
        return "byte"
    return t


def parse_def_line(line: str) -> Column | None:
    """Zamien linie 'Def' na obiekt Column."""
    line = line.strip()
    if not line:
        return None
    m = _TYPE_RE.match(line)
    if not m:
        return None
    tname = _norm_type(m.group("type"))
    name = m.group("name").strip()
    arr = m.group("array")
    bit = m.group("bit")

    col = Column(name=name, type=tname)
    if arr:
        col.array_size = int(arr.strip("[]"))
    if bit:
        # pole bitowe: "nazwa:liczba_bitow" - liczba bitow to szerokosc pola
        col.kind = KIND_BIT
        col.bit_count = int(bit[1:])
        col.bit_offset = 0
    if tname.startswith("dummy"):
        col.kind = KIND_PAD
    return col


def load_paramdef_xml(path: str) -> ParamDef:
    """Wczytaj definicje z pliku Paramdex *.xml."""
    tree = ET.parse(path)
    root = tree.getroot()
    pd = ParamDef()
    pt = root.find("ParamType")
    if pt is not None and pt.text:
        pd.param_type = pt.text.strip()
    fields_el = root.find("Fields")
    if fields_el is None:
        return pd
    for fel in fields_el.findall("Field"):
        d = fel.get("Def")
        if not d:
            continue
        pd.raw_defs.append(d)
        col = parse_def_line(d)
        if col is None:
            continue
        if col.kind == KIND_BIT:
            pd.bit_order.append((col.name, col.bit_count))
        pd.columns.append(col)
    return pd


def assign_bit_offsets(pd: ParamDef) -> None:
    """Nadaj offsety bitow polom bitowym.

    W FSParam bity w kolumnie sa uporzadkowane od najmniej znaczacego bitu
    w gore. Kolumny bitowe wystepuja w ciaglym bloku i zjadaja kolejne bity.
    """
    offset = 0
    for col in pd.columns:
        if col.kind == KIND_BIT:
            col.bit_offset = offset
            offset += col.bit_count
        else:
            offset = 0  # bitfield nie moze byc rozerwany przez inne pola


def load_paramdef_dir(path: str, name: str) -> ParamDef | None:
    import os

    p = os.path.join(path, name + ".xml")
    if not os.path.exists(p):
        return None
    pd = load_paramdef_xml(p)
    assign_bit_offsets(pd)
    return pd
