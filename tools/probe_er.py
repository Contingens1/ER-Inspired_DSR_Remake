"""
probe_er.py - Empiryczne rozpoznanie ukladu wierszy w ER .param.

Porownuje dlugosc wiersza wyliczona z definicji Paramdex z danymi w pliku,
szukajac dopasowania (kolejnosc kolumn, wskazniki stringow itp.).
"""
from __future__ import annotations

import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import paramdef  # noqa: E402
from fsparam import KIND_BIT, KIND_REF, PRIM  # noqa: E402

PARAMDEX = Path(r"C:\Users\nemos\workspace\toolsy\WitchyBND-3.0.1.0-win-x64\Assets\Paramdex\ER\Defs")


def main(param_name: str, sample: str) -> None:
    data = Path(sample).read_bytes()
    names_off, data_off, packed, zero, names2 = struct.unpack_from("<5I", data, 0)
    n_cols = packed & 0xFFFF
    n_rows = (packed >> 16) & 0xFFFF
    print(f"{param_name}: size={len(data)} names_off={names_off:#x} data_off={data_off:#x} "
          f"packed={packed:#x} n_cols={n_cols} n_rows={n_rows}")

    pd = paramdef.load_paramdef_xml(str(PARAMDEX / (param_name + ".xml")))
    print(f"  definicji: {len(pd.columns)} kolumn, typ={pd.param_type}")

    # rozmiary kolumn wg definicji
    total = 8  # id + rezerwa
    sizes = []
    for c in pd.columns:
        if c.kind == KIND_BIT:
            s = PRIM.get(c.type, (4, "i"))[0]
        elif c.kind == KIND_REF:
            s = PRIM.get(c.type, (4, "i"))[0] + (2 if c.wide else 4)
        elif c.kind == 3:
            s = PRIM.get(c.type, (4, "i"))[0]
        else:
            s = PRIM.get(c.type, (4, "i"))[0] * max(1, c.array_size)
        sizes.append(s)
        total += s
    print(f"  suma rozmiarow kolumn (bez id): {total - 8}")

    # szerokosc danych: names_off - data_off
    span = names_off - data_off
    print(f"  rozpietosc danych: {span} -> {span / max(1, n_rows):.2f} B/wiersz")

    # pierwsze 32 bajty wiersza
    print("  pierwszy wiersz (hex):", data[data_off : data_off + 32].hex(" "))
    # ostatnie bajty obszaru danych
    print("  koniec danych (hex):", data[names_off - 32 : names_off].hex(" "))
    # obszar nazw
    print("  obszar nazw:", repr(data[names_off : names_off + 120]))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
