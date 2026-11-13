"""
add_jump_anims.py - dodaje animacje skoku z ER (repozytorium animacji, format DSR) do moda.

Dla kazdego wpisu mapy NOWE_ID -> plik HKX z repozytorium:
  - w c0000.anibnd.dcx (a00.tae) klonuje animacje 900 (skok DSR) pod NOWE_ID, ze zdarzeniami TAE
    skoku DSR (logika skoku zostaje DSR-owa, zmienia sie ruch postaci);
  - do c0000_a00_lo.anibnd.dcx dodaje plik HKX z ER jako a00_NNNN.hkx.
Wynik trafia do katalogu podmiany plikow ModEngine2 (--out, domyslnie dist/mods/c0000_er_engine/files),
pliki gry nie sa modyfikowane. Wybor wariantu w grze robi er_engine.dll (podmiana ID 900).

Uzycie (CMD, z katalogu ds1-elden-port):
    python tools\\add_jump_anims.py --map 901=a000_202000.hkx 902=a000_202010.hkx
"""
from __future__ import annotations

import argparse
import ntpath
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from sfbridge import load_soulsformats, read_binder, read_file, to_memory  # noqa: E402

DSR_CHR = Path(r"F:\SteamLibrary\steamapps\common\DARK SOULS REMASTERED\chr")
REPO = Path(r"C:\Users\nemos\workspace\toolsy\Player Animations Repository"
            r"\(ER) c0000 Tarnished_c0000 Chosen Undead-748-ER-1-001-1723291686"
            r"\Base Game\2016 (DSR)\a000 - Base Movement")
SOURCE_ANIM = 900  # skok DSR - zrodlo zdarzen TAE

# Ladowanie w animacji 900 to ~0.63 s; potem nastepuje przewrot (0.67-1.2 s). Skok w stylu ER
# nie ma przewrotu: okna przerwan zaczynaja sie od ladowania (nazwy wg DSAS TAE.Template.DS1.xml).
LANDING_TIME = 0.70
CANCEL_JUMPTABLES = {4, 11, 16, 22, 26, 29, 31, 32}  # przerwania: atak, ruch, blok, przewrot, czar, przedmiot, ogolne
ROLL_ONLY_JUMPTABLES = {8}  # 8: Invincible - nietykalnosc przewrotu przy ladowaniu
EVENT_JUMPTABLE, EVENT_BEHAVIOR_WINDOW, EVENT_ROLL_DISTANCE = 0, 300, 236


def er_style_events(src_events, TAE):
    """Zdarzenia skoku 900 bez przewrotu po ladowaniu (lista nowych TAE.Event)."""
    import struct
    out = []
    behavior = [e for e in src_events if e.Type == EVENT_BEHAVIOR_WINDOW and e.StartTime > LANDING_TIME]
    shift = (min(e.StartTime for e in behavior) - LANDING_TIME) if behavior else 0.0
    for ev in src_events:
        params = bytes(ev.GetParameterBytes(False))
        jt = struct.unpack_from("<i", params)[0] if ev.Type == EVENT_JUMPTABLE and len(params) >= 4 else None
        start, end = ev.StartTime, ev.EndTime
        if ev.StartTime >= LANDING_TIME - 0.05 and (jt in ROLL_ONLY_JUMPTABLES or ev.Type == EVENT_ROLL_DISTANCE):
            continue
        if jt in CANCEL_JUMPTABLES and start > LANDING_TIME:
            start = LANDING_TIME
        elif ev.Type == EVENT_BEHAVIOR_WINDOW and ev.StartTime > LANDING_TIME:
            start, end = ev.StartTime - shift, ev.EndTime - shift
        out.append(TAE.Event(start, end, ev.Type, ev.Unk04, ev.GetParameterBytes(False), False))
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Dodaje animacje skoku z ER do moda DSR.")
    ap.add_argument("--map", nargs="+", default=["901=a000_202000.hkx", "902=a000_202010.hkx"],
                    help="pary NOWE_ID=plik_hkx_z_repozytorium")
    ap.add_argument("--dsr-chr", type=Path, default=DSR_CHR)
    ap.add_argument("--repo", type=Path, default=REPO)
    ap.add_argument("--out", type=Path, default=Path("dist/mods/c0000_er_engine/files"))
    args = ap.parse_args(argv)
    # sfbridge zmienia katalog roboczy procesu (Oodle) - sciezki absolutne.
    args.dsr_chr, args.repo, args.out = (p.resolve() for p in (args.dsr_chr, args.repo, args.out))
    mapping = {int(k): v for k, v in (pair.split("=", 1) for pair in args.map)}
    for new_id, hkx in mapping.items():
        if not 900 < new_id < 10000:
            sys.exit(f"BLAD: ID {new_id} poza zakresem 901-9999 (nazwy HKX w DSR maja 4 cyfry).")
        if not (args.repo / hkx).is_file():
            sys.exit(f"BLAD: brak {hkx} w {args.repo}")

    load_soulsformats()
    from SoulsFormats import BND3, TAE, BinderFile
    from System import Array, Byte

    out_chr = args.out / "chr"
    out_chr.mkdir(parents=True, exist_ok=True)

    # 1. TAE: klony animacji 900.
    ani = read_binder(BND3, str(args.dsr_chr / "c0000.anibnd.dcx"))
    tae_file = next(f for f in ani.Files if ntpath.basename(f.Name).lower() == "a00.tae")
    tae = read_file(TAE, tae_file.Bytes)
    src = next(a for a in tae.Animations if int(a.ID) == SOURCE_ANIM)
    existing = {int(a.ID) for a in tae.Animations}
    for new_id in mapping:
        if new_id in existing:
            sys.exit(f"BLAD: animacja {new_id} juz istnieje w a00.tae.")
        clone = TAE.Animation(new_id, src.AnimFileReference, src.Unknown1, src.Unknown2, f"a00_{new_id:04d}.HKXwin")
        events = er_style_events(list(src.Events), TAE)
        for ev in events:
            clone.Events.Add(ev)
        if src.EventGroups.Count:
            print(f"  UWAGA: animacja {SOURCE_ANIM} ma grupy zdarzen - pominiete (indeksy po filtrowaniu nieaktualne)")
        print(f"  {new_id}: {src.Events.Count} -> {len(events)} zdarzen TAE (bez przewrotu, przerwania od {LANDING_TIME} s)")
        tae.Animations.Add(clone)
    anims = sorted(list(tae.Animations), key=lambda a: a.ID)
    tae.Animations.Clear()
    for a in anims:
        tae.Animations.Add(a)
    tae_file.Bytes = to_memory(tae.Write())
    ani.Write(str(out_chr / "c0000.anibnd.dcx"))

    # 2. HKX z ER do c0000_a00_lo.anibnd.dcx.
    lo = read_binder(BND3, str(args.dsr_chr / "c0000_a00_lo.anibnd.dcx"))
    ref = next(f for f in lo.Files if ntpath.basename(f.Name).lower() == "a00_0900.hkx")
    # Gra szuka HKX po ID wpisu = ID animacji (a00_0900.hkx ma ID 900). Inne ID -> T-poza.
    id_base = int(ref.ID) - SOURCE_ANIM
    for new_id, hkx in mapping.items():
        data = (args.repo / hkx).read_bytes()
        name = ntpath.join(ntpath.dirname(ref.Name), f"a00_{new_id:04d}.hkx")
        lo.Files.Add(BinderFile(ref.Flags, id_base + new_id, name, to_memory(Array[Byte](data))))
        print(f"  {new_id}: {hkx} ({len(data)} B) -> {ntpath.basename(name)} (ID wpisu {id_base + new_id})")
    files = sorted(list(lo.Files), key=lambda f: int(f.ID))
    lo.Files.Clear()
    for f in files:
        lo.Files.Add(f)
    lo.Write(str(out_chr / "c0000_a00_lo.anibnd.dcx"))

    # 3. Kontrola: ponowny odczyt.
    check = read_file(TAE, next(f for f in read_binder(BND3, str(out_chr / "c0000.anibnd.dcx")).Files
                                if ntpath.basename(f.Name).lower() == "a00.tae").Bytes)
    found = sorted(int(a.ID) for a in check.Animations if int(a.ID) in mapping)
    print(f"OK: animacje {found} w a00.tae, pliki w {out_chr}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
