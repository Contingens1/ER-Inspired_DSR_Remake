"""
probe.py - Rozpoznaj format archiwum i wypisz zawartosc (bez modyfikacji).

Uzycie: python tools/probe.py <plik> [...]
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import bnd  # noqa: E402


def describe(path: Path) -> None:
    data = path.read_bytes()
    print(f"== {path.name} ({len(data)} bytes) ==")
    print("   magic:", data[:4])

    if bnd.is_dcx(data):
        print("   -> DCX")
        data = bnd.dcx_decompress(data)
        print("   po DCX:", len(data), "magic:", data[:4])

    if data[:4] == b"BND4":
        arc = bnd.read_bnd4(data)
        print(f"   -> BND4, {len(arc.files)} plikow")
        for f in arc.files[:40]:
            print(f"      {f.name}  ({f.size} B)")
        if len(arc.files) > 40:
            print(f"      ... i {len(arc.files) - 40} wiecej")
    elif data[:8] == b"PARAMPND":
        print("   -> PARAM")
    else:
        print("   -> nieznany format")


if __name__ == "__main__":
    for arg in sys.argv[1:]:
        describe(Path(arg))
