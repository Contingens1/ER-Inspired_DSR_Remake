"""
fix_er_jump_height.py - wysokosc skoku z ER w DSR: bez przysiadu w ruchu postaci + opcjonalna skala.

Root motion y w animacjach wybicia ER najpierw spada (przysiad, do ~-0.32 m), potem rosnie (~1.16 m).
DSR nie pozwala zejsc pod ziemie, wiec spadek przepada, a kazdy przyrost od dolka juz unosi postac:
start za wczesnie i skok o ~0.3 m za wysoki. Ustawiamy y = max(0, y - prog) / (szczyt - prog) * szczyt * skala (prog: ER podnosi root przed oderwaniem stop).
UWAGA: uruchamiac na kopii sprzed poprawki (work/c0000_a00_lo.before_jump_height.dcx).
Dziala na a00_0900/0901/0902.hkx w files/chr/c0000_a00_lo.anibnd.dcx (po port_er_anims.py --groups jump).

Uzycie (CMD): python tools\\fix_er_jump_height.py [--scale 1.0]
"""
from __future__ import annotations

import argparse
import ntpath
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from sfbridge import load_soulsformats, read_binder, to_memory  # noqa: E402

LO = Path(__file__).resolve().parent.parent / "dist/mods/c0000_er_engine/files/chr/c0000_a00_lo.anibnd.dcx"
NAMES = ("a00_0900.hkx", "a00_0901.hkx", "a00_0902.hkx")


def motion_run(d: bytes) -> tuple[int, int]:
    """Ostatni ciag float4 (x, y, z, 0) z wyraznym ruchem w pionie = probki ruchu postaci."""
    found = []
    for m in range(0, 16, 4):
        o, st, n = m, None, 0
        while o + 16 <= len(d):
            x, y, z, w = struct.unpack_from("<4f", d, o)
            if w == 0.0 and abs(x) < 5 and -1 < y < 5 and -50 < z < 5:
                st = o if st is None else st
                n += 1
            else:
                if st is not None and 8 < n < 80:
                    ys = [struct.unpack_from("<4f", d, st + 16 * i)[1] for i in range(n)]
                    if max(ys) > 0.5:
                        found.append((st, n))
                st, n = None, 0
            o += 16
    if not found:
        raise SystemExit("BLAD: nie znaleziono probek ruchu postaci")
    return max(found)  # najdalej w pliku (wczesniejszy dlugi ciag to inna sciezka)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--scale", type=float, default=1.0, help="skala wysokosci skoku")
    ap.add_argument("--lift", type=float, default=0.3, help="prog y (m): ponizej postac stoi; szczyt bez zmian")
    ap.add_argument("--end-only", action="store_true", help="bez zmian przysiadu/szczytu; tylko opadanie po szczycie konczy sie na ziemi (y=0)")
    args = ap.parse_args()
    load_soulsformats()
    from SoulsFormats import BND3
    from System import Array, Byte
    bnd = read_binder(BND3, str(LO))
    for f in bnd.Files:
        n = ntpath.basename(f.Name).lower()
        if n not in NAMES:
            continue
        d = bytearray(bytes(f.Bytes.ToArray()))
        st, cnt = motion_run(bytes(d))
        peak = max(struct.unpack_from("<4f", d, st + 16 * i)[1] for i in range(cnt))
        ys_all = [struct.unpack_from("<4f", d, st + 16 * i)[1] for i in range(cnt)]
        pk = ys_all.index(peak)
        ys_old, ys_new = [], []
        for i in range(cnt):
            o = st + 16 * i
            x, y, z, w = struct.unpack_from("<4f", d, o)
            if args.end_only:  # opadanie: odejmujemy rampe, zeby ostatnia probka = 0 (inaczej gra odpala spadanie 1550)
                ny = y if i <= pk else y - ys_all[-1] * (i - pk) / (cnt - 1 - pk)
            else:
                ny = max(0.0, y - args.lift) / (peak - args.lift) * peak * args.scale
            struct.pack_into("<4f", d, o, x, ny, z, w)
            ys_old.append(y)
            ys_new.append(ny)
        lift = next((i for i, y in enumerate(ys_new) if y > 0.01), -1)
        print(f"  {n}: {cnt} probek, y {min(ys_old):.2f}..{max(ys_old):.2f} (koniec {ys_old[-1]:.2f}) -> {min(ys_new):.2f}..{max(ys_new):.2f} (koniec {ys_new[-1]:.2f}), "
              f"oderwanie od probki {lift} (~{lift / 30:.2f} s)")
        f.Bytes = to_memory(Array[Byte](list(d)))
    tmp = LO.with_suffix(".tmp")
    bnd.Write(str(tmp))
    bnd.Dispose()
    tmp.replace(LO)
    print(f"OK -> {LO}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
