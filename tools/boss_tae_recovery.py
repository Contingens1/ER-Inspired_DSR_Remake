"""Tempo atakow bossa w stylu ER samymi danymi TAE: przesuwa okna "AI moze dzialac dalej"
(JumpTable 78 ruch, 79 krok, 86 kolejny atak; opcjonalnie dodaje 23 kontynuacje combo) na wczesniejszy czas.

Przyklad (Asylum Demon c2230, atak 3003 - drugi zamach combo; wartosci z ER c4810 a3003:
trafienie konczy sie 1.33 s, okna AI od 3.13 s, czyli +1.80 s po trafieniu):

  python tools/boss_tae_recovery.py c2230 3003 --after-hit 1.80 --out dist/mods/boss_asylum_test/files_attack

Nic nie pisze do katalogu gry. Bez --out tylko wypisuje, co by zmienil.
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
AI_JTS = {78: "ruch", 79: "krok", 86: "atak"}
STEP_LEAD = 0.20  # okno kroku (79) otwiera sie w DSR ~0.2 s przed oknem ataku/ruchu


def jt_id(e) -> int:
    return struct.unpack_from("<i", bytes(e.GetParameterBytes(False)))[0]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("chr")
    ap.add_argument("anim", type=int)
    ap.add_argument("--after-hit", type=float, required=True, help="okna AI otwieraja sie tyle sekund po koncu trafienia")
    ap.add_argument("--out", type=Path, help="katalog moda (powstanie <out>/chr/<chr>.anibnd.dcx)")
    args = ap.parse_args(argv)
    out = args.out.resolve() if args.out else None  # przed SoulsFormats (zmienia katalog roboczy)

    load_soulsformats()
    from SoulsFormats import BND3, TAE
    src = DSR_CHR / f"{args.chr}.anibnd.dcx"
    bnd = read_binder(BND3, str(src))
    entry = next(f for f in bnd.Files if ntpath.basename(str(f.Name)).lower() == f"{args.chr}.tae")
    tae = read_file(TAE, entry.Bytes)
    anim = next(a for a in tae.Animations if int(a.ID) == args.anim)
    evs = list(anim.Events)
    # typ 1 = InvokeAttackBehavior, typ 2 = InvokeBulletBehavior (TAE.Template.DS1.xml)
    hit_end = max(float(e.EndTime) for e in evs if int(e.Type) in (1, 2))
    target = round((hit_end + args.after_hit) * 30) / 30.0
    print(f"{args.chr} a{args.anim}: koniec trafienia {hit_end:.2f} s -> okna AI od {target:.2f} s")
    changed = 0
    for e in evs:
        if int(e.Type) != 0 or jt_id(e) not in AI_JTS:
            continue
        j = jt_id(e)
        new = target - (STEP_LEAD if j == 79 else 0.0)
        old = float(e.StartTime)
        if new < old:
            print(f"   JT{j} ({AI_JTS[j]}): {old:.2f}-{float(e.EndTime):.2f} -> {new:.2f}-{float(e.EndTime):.2f}")
            e.StartTime = new
            changed += 1
        else:
            print(f"   JT{j} ({AI_JTS[j]}): {old:.2f} juz wczesniej niz {new:.2f} - bez zmian")
    if not out:
        print("(bez --out: nic nie zapisano)")
        return 0
    entry.Bytes = to_memory(tae.Write())
    dst = out / "chr" / src.name
    dst.parent.mkdir(parents=True, exist_ok=True)
    bnd.Write(str(dst))
    # kontrola: odczyt z zapisanego pliku
    chk = read_file(TAE, next(f for f in read_binder(BND3, str(dst)).Files
                             if ntpath.basename(str(f.Name)).lower() == f"{args.chr}.tae").Bytes)
    a2 = next(a for a in chk.Animations if int(a.ID) == args.anim)
    got = sorted((jt_id(e), round(float(e.StartTime), 2)) for e in a2.Events if int(e.Type) == 0 and jt_id(e) in AI_JTS)
    print(f"zmieniono {changed} zdarzen; zapisano {dst} ({dst.stat().st_size} B); po odczycie: {got}; "
          f"animacji w TAE {chk.Animations.Count} (bylo {tae.Animations.Count})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
