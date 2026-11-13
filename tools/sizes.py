"""
sizes.py - Szukanie ukladu wiersza FSParam dla ER (dopasowanie rozmiaru).

Zlicza bajty wg definicji Paramdex, z roznych wariantow interpretacji:
  - pakiowanie pol bitowych do wspolnych bajtow
  - pomijanie kolumn padding (dummy*)
  - rozmiar kolumn bitowych
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import paramdef  # noqa: E402
from fsparam import KIND_BIT, KIND_PAD, PRIM  # noqa: E402

PARAMDEX = Path(r"C:\Users\nemos\workspace\toolsy\WitchyBND-3.0.1.0-win-x64\Assets\Paramdex\ER\Defs")


def is_padding(def_line: str) -> bool:
    return def_line.strip().lower().startswith("dummy")


def calc(pd, skip_pad: bool, pack_bits: bool, bit_base: str) -> int:
    total = 8
    pending_bits = 0
    pending_type = None

    def flush() -> int:
        nonlocal pending_bits, pending_type
        if not pending_bits:
            return 0
        if not pack_bits:
            n = pending_bits
        else:
            width = PRIM.get(pending_type, (1, "B"))[0]
            if bit_base == "byte":
                width = 1
            n = math.ceil(pending_bits / (8 * width))
        pending_bits = 0
        pending_type = None
        return n

    for col, d in zip(pd.columns, pd.raw_defs):
        if col.kind == KIND_BIT:
            if pending_type is None:
                pending_type = col.type
            pending_bits += col.bit_count
            continue
        total += flush()
        if skip_pad and is_padding(d):
            continue
        if col.kind == KIND_PAD:
            total += PRIM.get(col.type, (1, "B"))[0]
            continue
        total += PRIM.get(col.type, (4, "i"))[0] * max(1, col.array_size)
    total += flush()
    return total


def main(param_name: str, target: int) -> None:
    pd = paramdef.load_paramdef_xml(str(PARAMDEX / (param_name + ".xml")))
    print(f"{param_name}: {len(pd.columns)} kolumn, target wiersza = {target} B")
    best = []
    for skip_pad in (False, True):
        for pack_bits in (False, True):
            for bit_base in ("byte", "type"):
                n = calc(pd, skip_pad, pack_bits, bit_base)
                best.append((abs(n - target), n, skip_pad, pack_bits, bit_base))
    best.sort()
    for d, n, sp, pb, bb in best[:6]:
        print(f"  size={n} (delta {d:+d})  skip_pad={sp} pack_bits={pb} bit_base={bb}")


if __name__ == "__main__":
    main(sys.argv[1], int(sys.argv[2]))
