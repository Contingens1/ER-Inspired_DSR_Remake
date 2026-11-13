"""
open_air_attack.py - okno ataku prawa reka w locie w skokach 900/901/902 (dla atakow z wyskoku).

JT1 (Right Hand Attack Key Input) i JT4 (Right Hand Attack Anim Cancel) zaczynaja sie wczesniej
(JT_FROM). Gra sama wybiera atak broni (R1/R2, 1H/2H), a er_engine.dll podmienia go
w locie na atak z wyskoku z ER (tools/add_jump_attacks.py).

Uzycie (CMD): python tools\\open_air_attack.py
"""
from __future__ import annotations

import ntpath
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from sfbridge import load_soulsformats, read_binder, read_file, to_memory  # noqa: E402

ANIBND = Path(__file__).resolve().parent.parent / "dist/mods/c0000_er_engine/files/chr/c0000.anibnd.dcx"
# JT4 (przerwanie atakiem): 0.25 s - postac jest juz nad ziemia (root motion skoku przecina poziom
# startu ok. 0.23 s); w ER okno jest od 0.20 s. JT1 (przyjmowanie klawisza) od poczatku skoku, zeby
# klik zaraz po skoku czekal w kolejce i atak ruszal w 0.25 s.
JT_FROM = {1: 0.0, 4: 0.25}


def main() -> int:
    load_soulsformats()
    from SoulsFormats import BND3, TAE
    bnd = read_binder(BND3, str(ANIBND))
    f = next(f for f in bnd.Files if ntpath.basename(f.Name).lower() == "a00.tae")
    tae = read_file(TAE, f.Bytes)
    for a in tae.Animations:
        if int(a.ID) not in (900, 901, 902):
            continue
        for e in a.Events:
            p = bytes(e.GetParameterBytes(False))
            j = struct.unpack_from("<i", p)[0] if int(e.Type) == 0 and len(p) >= 4 else None
            if j in JT_FROM and e.StartTime > JT_FROM[j]:
                print(f"  {int(a.ID)}: JT{j} {e.StartTime:.3f} -> {JT_FROM[j]:.3f} (koniec {e.EndTime:.3f})")
                e.StartTime = JT_FROM[j]
    f.Bytes = to_memory(tae.Write())
    tmp = ANIBND.with_suffix(".tmp")
    bnd.Write(str(tmp))
    bnd.Dispose()
    tmp.replace(ANIBND)
    print("OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
