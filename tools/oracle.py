"""
oracle.py - Wyznaczenie kolejnosci kolumn w ER .param za pomoca wartosci referencyjnych.

Oracle: pole `sortId` ma byc rosnace w kolejnych wierszach, a `behaviorVariationId`
ma byc -1/0 dla wiekszosci broni. Sprawdzamy, przy jakim ukladzie kolumn
wartosci wygladaja sensownie.
"""
from __future__ import annotations

import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import paramdef  # noqa: E402
from fsparam import KIND_BIT, KIND_PAD, PRIM  # noqa: E402
import xml.etree.ElementTree as ET  # noqa: E402

PARAMDEX = Path(r"C:\Users\nemos\workspace\toolsy\WitchyBND-3.0.1.0-win-x64\Assets\Paramdex\ER\Defs")


def load_fields(param_name: str):
    r = ET.parse(str(PARAMDEX / (param_name + ".xml"))).getroot()
    out = []
    for f in r.find("Fields").findall("Field"):
        if "RemovedVersion" in f.attrib:
            continue
        d = f.get("Def")
        c = paramdef.parse_def_line(d)
        if c:
            out.append((d, c))
    return out


def offsets(fields, skip_pad: bool, pack_bits: bool):
    """Zwraca listę (nazwa, offset, rozmiar) i łączny rozmiar wiersza."""
    res = []
    pos = 8
    pending = 0
    for d, c in fields:
        if c.kind == KIND_BIT:
            pending += c.bit_count
            continue
        if pack_bits and pending:
            nb = (pending + 7) // 8
            res.append((f"<bits:{pending}>", pos, nb))
            pos += nb
            pending = 0
        elif pending:
            res.append((f"<bits:{pending}>", pos, pending))
            pos += pending
            pending = 0
        if skip_pad and d.lower().startswith("dummy"):
            continue
        n = PRIM.get(c.type, (4, "i"))[0]
        sz = n * max(1, c.array_size) if c.kind != KIND_PAD else n
        res.append((c.name, pos, sz))
        pos += sz
    if pending:
        nb = (pending + 7) // 8 if pack_bits else pending
        res.append((f"<bits:{pending}>", pos, nb))
        pos += nb
    return res, pos


def main(param_name: str, path: str, stride: int) -> None:
    data = Path(path).read_bytes()
    fields = load_fields(param_name)
    print(f"{param_name}: {len(fields)} pol (bez RemovedVersion)")
    for skip_pad in (True, False):
        res, size = offsets(fields, skip_pad, True)
        print(f"  skip_pad={skip_pad}: rozmiar wiersza z definicji = {size} (plik: {stride})")

    res, size = offsets(fields, True, True)
    # zbadamy kilka pol na 5 pierwszych wierszach
    probe_names = ["sortId", "behaviorVariationId", "weaponId", "residentSpEffectId", "poiseDamage", "guardAngle"]
    for pname in probe_names:
        hit = [(n, o, s) for n, o, s in res if n.lower() == pname.lower()]
        if not hit:
            continue
        n, o, s = hit[0]
        vals = []
        for r in range(6):
            base = 0x10000 + r * stride
            if s == 4:
                vals.append(struct.unpack_from("<i", data, base + o)[0])
            elif s == 2:
                vals.append(struct.unpack_from("<h", data, base + o)[0])
            else:
                vals.append(data[base + o])
        print(f"  {pname:22s} off={o:4d} size={s} -> {vals}")

    # identyfikatory wierszy
    ids = [struct.unpack_from("<i", data, 0x10000 + r * stride)[0] for r in range(8)]
    print("  id pierwszych wierszy:", ids)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], int(sys.argv[3]))
