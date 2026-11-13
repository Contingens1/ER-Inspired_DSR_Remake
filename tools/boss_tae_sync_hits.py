"""Zrownuje start "fali" z trafieniem glownym w atakach przeciwnika (TAE, InvokeAttackBehavior).
W DSR ataki z uderzeniem w ziemie maja dwa zdarzenia trafienia: N (bron/cialo) i N+1 (fala), przy czym fala
zaczyna sie dopiero po koncu pierwszego - w sumie okno jest za dlugie na jeden unik. Tu fala startuje razem
z trafieniem glownym i zachowuje swoja dlugosc. Obrazenia bez zmian (blisko nadal trafiaja oba).

  python tools/boss_tae_sync_hits.py c2232 --base dist/mods/boss_asylum_test/files_c2232_er/chr/c2232.anibnd.dcx \
      --out dist/mods/boss_asylum_test/files_c2232_er [--only 3008 3010]

Bez --out tylko wypisuje, co by zmienil.
"""
from __future__ import annotations

import argparse
import ntpath
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from sfbridge import load_soulsformats, read_binder, read_file, to_memory  # noqa: E402

DSR_CHR = Path(r"F:\SteamLibrary\steamapps\common\DARK SOULS REMASTERED\chr")


def beh(e) -> int:
    return struct.unpack_from("<iii", bytes(e.GetParameterBytes(False)) + b"\0" * 12)[2]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("chr")
    ap.add_argument("--base", type=Path)
    ap.add_argument("--out", type=Path)
    ap.add_argument("--only", type=int, nargs="*")
    args = ap.parse_args(argv)
    base = args.base.resolve() if args.base else DSR_CHR / f"{args.chr}.anibnd.dcx"
    out = args.out.resolve() if args.out else None

    load_soulsformats()
    from SoulsFormats import BND3, TAE
    bnd = read_binder(BND3, str(base))
    entry = next(f for f in bnd.Files if ntpath.basename(str(f.Name)).lower() == f"{args.chr}.tae")
    tae = read_file(TAE, entry.Bytes)
    n = 0
    for a in tae.Animations:
        aid = int(a.ID)
        if args.only and aid not in args.only:
            continue
        hits = sorted((e for e in a.Events if int(e.Type) == 1), key=lambda e: float(e.StartTime))
        by_id = {beh(e): e for e in hits}
        for b, main_ev in by_id.items():
            wave = by_id.get(b + 1)
            if b % 10 or wave is None:
                continue
            ms, ws, we = float(main_ev.StartTime), float(wave.StartTime), float(wave.EndTime)
            if ws <= ms + 1e-4:
                continue
            new_end = ms + (we - ws)
            print(f"a{aid}: trafienie {b} {ms:.2f}-{float(main_ev.EndTime):.2f}; fala {b + 1} {ws:.2f}-{we:.2f} -> {ms:.2f}-{new_end:.2f}")
            wave.StartTime, wave.EndTime = ms, new_end
            n += 1
    if not out:
        print(f"(bez --out: nic nie zapisano; zmian byloby {n})")
        return 0
    entry.Bytes = to_memory(tae.Write())
    dst = out / "chr" / f"{args.chr}.anibnd.dcx"
    dst.parent.mkdir(parents=True, exist_ok=True)
    bnd.Write(str(dst))
    print(f"zmieniono {n} zdarzen; zapisano {dst} ({dst.stat().st_size} B)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
