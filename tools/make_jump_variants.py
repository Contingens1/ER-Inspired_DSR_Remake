"""
make_jump_variants.py - warianty skoku DSR przez edycje ruchu postaci (root motion) w a00_0900.hkx.

Ruch postaci animacji (hkaDefaultAnimatedReferenceFrame) to tablica float4 (x, y, z, w) na klatke:
y = wysokosc, z = przesuniecie do przodu (ujemne), x = w bok. Ustalone porownaniem z modem
Realistic Jump (zmienia tylko y). Narzedzie znajduje te tablice i zapisuje kopie HKX
z przeskalowanym ruchem poziomym:
    901 - skok z miejsca (poziomo x0)      902 - skok w ruchu (poziomo xFACTOR)
Wynik: c0000_a00_lo.anibnd.dcx w katalogu podmiany ModEngine2. Animacje 901/902 w a00.tae
dodaje tools/add_jump_anims.py (klon zdarzen 900) - wystarczy uruchomic go raz wczesniej.

Uzycie (CMD):
    python tools\\make_jump_variants.py [--base <a00_lo.anibnd.dcx z innym skokiem>] [--moving 0.5] [--height 1.0]
"""
from __future__ import annotations

import argparse
import ntpath
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from sfbridge import load_soulsformats, read_binder, to_memory  # noqa: E402

DSR_CHR = Path(r"F:\SteamLibrary\steamapps\common\DARK SOULS REMASTERED\chr")


def find_reference_frame(data: bytes) -> tuple[int, int]:
    """Najdluzszy ciag float4 (x, y, z, w) z w == 0 i z nierosnacym = probki ruchu postaci."""
    best = (0, 0)
    for start_mod in range(0, 16, 4):
        o, run_start, prev_z = start_mod, None, None
        while o + 16 <= len(data):
            x, y, z, w = struct.unpack_from("<4f", data, o)
            ok = w == 0.0 and abs(x) < 5 and -1 < y < 10 and -50 < z <= 0.001 and (prev_z is None or z <= prev_z + 1e-4)
            if ok:
                if run_start is None:
                    run_start = o
                prev_z = z
            else:
                # Ciag musi faktycznie przesuwac postac (bloki zer to inne struktury HKX).
                if run_start is not None and (o - run_start) // 16 > best[1] and prev_z < -0.5:
                    best = (run_start, (o - run_start) // 16)
                run_start, prev_z = None, None
            o += 16
    # Przed probkami leza: wektor "w gore" (0,1,0,0), "do przodu" (0,0,1,0) i wiersz z czasem
    # trwania (float + int). Heurystyka lapie ten ostatni - kotwiczymy start za nimi.
    start, count = best
    fwd = struct.pack("<4f", 0.0, 0.0, 1.0, 0.0)
    anchor = data.rfind(fwd, max(0, start - 64), start + 16)
    if anchor >= 0 and anchor + 32 > start:
        skip = (anchor + 32 - start) // 16
        start, count = anchor + 32, count - skip
    return start, count


def scaled(data: bytes, start: int, count: int, horiz: float, height: float) -> bytes:
    out = bytearray(data)
    for i in range(count):
        o = start + 16 * i
        x, y, z, w = struct.unpack_from("<4f", out, o)
        struct.pack_into("<4f", out, o, x * horiz, y * height, z * horiz, w)
    return bytes(out)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Warianty skoku DSR (root motion).")
    ap.add_argument("--base", type=Path, default=DSR_CHR / "c0000_a00_lo.anibnd.dcx",
                    help="kontener z bazowym a00_0900.hkx (np. z modu Realistic Jump)")
    ap.add_argument("--moving", type=float, default=0.5, help="skala ruchu poziomego skoku w ruchu (902)")
    ap.add_argument("--height", type=float, default=1.0, help="skala wysokosci obu wariantow")
    ap.add_argument("--out", type=Path, default=Path("dist/mods/c0000_er_engine/files"))
    args = ap.parse_args(argv)
    args.base, args.out = args.base.resolve(), args.out.resolve()

    load_soulsformats()
    from SoulsFormats import BND3, BinderFile
    from System import Array, Byte

    lo_path = args.out / "chr" / "c0000_a00_lo.anibnd.dcx"
    if not lo_path.exists():
        sys.exit("BLAD: najpierw uruchom tools/add_jump_anims.py (tworzy wpisy 901/902).")
    base = read_binder(BND3, str(args.base))
    src = next(f for f in base.Files if ntpath.basename(f.Name).lower() == "a00_0900.hkx")
    data = bytes(src.Bytes.ToArray())
    start, count = find_reference_frame(data)
    if count < 10:
        sys.exit(f"BLAD: nie znaleziono probek ruchu postaci (najdluzszy ciag {count}).")
    first, last = struct.unpack_from("<4f", data, start), struct.unpack_from("<4f", data, start + 16 * (count - 1))
    print(f"probki ruchu: offset {start:#x}, {count} klatek, start {tuple(round(v, 3) for v in first)}"
          f" -> koniec {tuple(round(v, 3) for v in last)}")

    variants = {901: scaled(data, start, count, 0.0, args.height),
                902: scaled(data, start, count, args.moving, args.height)}
    lo = read_binder(BND3, str(lo_path))
    for new_id, blob in variants.items():
        name = f"a00_{new_id:04d}.hkx"
        entry = next((f for f in lo.Files if ntpath.basename(f.Name).lower() == name), None)
        if entry is None:
            sys.exit(f"BLAD: brak {name} w {lo_path} - uruchom tools/add_jump_anims.py.")
        entry.Bytes = to_memory(Array[Byte](list(blob)))
        end = struct.unpack_from("<4f", blob, start + 16 * (count - 1))
        print(f"  {name}: koniec ruchu {tuple(round(v, 3) for v in end)}")
    tmp = lo_path.with_suffix(".tmp")
    lo.Write(str(tmp))
    lo.Dispose()
    tmp.replace(lo_path)
    print(f"OK: {lo_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
