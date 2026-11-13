"""
add_land_anims.py - ladowania po skoku z ER jako nowe animacje DSR (903-905) + okna ER w 1790.

  903 <- a000_202100 Jump_Land_N_NormalHeight  (ladowanie w miejscu)
  904 <- a000_202115 Jump_Land_To_Run          (ladowanie w bieg)
  905 <- a000_202125 Jump_Land_To_Dash_Light   (ladowanie w sprint)
Zdarzenia TAE: klon 1790 (ladowanie po skoku DSR) bez nietykalnosci przewrotu (JT8) i blokady obrotu
(JT7), okna przerwan od czasow ER (JT4 0.03, JT16/22/26/29/31 0.13, JT11 0.17, JT32 0.03).
1790 (HKX juz z ER 202100) dostaje te same okna. Odtwarza je er_engine.dll po wykrytym ladowaniu.
Dziala na plikach moda (files/chr), nie na plikach gry.

Uzycie (CMD): python tools\\add_land_anims.py
"""
from __future__ import annotations

import ntpath
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from sfbridge import load_soulsformats, read_binder, read_file, to_memory  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
CHR = ROOT / "dist/mods/c0000_er_engine/files/chr"
REPO = Path(r"C:\Users\nemos\workspace\toolsy\Player Animations Repository"
            r"\(ER) c0000 Tarnished_c0000 Chosen Undead-748-ER-1-001-1723291686"
            r"\Base Game\2016 (DSR)\a000 - Base Movement")
NEW = {903: "a000_202100.hkx", 904: "a000_202115.hkx", 905: "a000_202125.hkx", 906: "a000_202040.hkx"}
LOOP = {906: 1580}  # petla lotu ER na calym ciele (DLL przy skoku na nizszy poziom): zdarzenia z 1580 bez zmian
SOURCE = 1790
ER_CANCEL = {4: 0.03, 16: 0.13, 22: 0.13, 26: 0.13, 29: 0.13, 31: 0.13, 11: 0.17, 32: 0.03}
DROP = {7, 8}  # blokada obrotu, nietykalnosc przewrotu


def jt(e):
    p = bytes(e.GetParameterBytes(False))
    return struct.unpack_from("<i", p)[0] if int(e.Type) == 0 and len(p) >= 4 else None


def er_events(src, TAE):
    out = []
    for e in src.Events:
        j = jt(e)
        if j in DROP:
            continue
        start = ER_CANCEL.get(j, e.StartTime)
        out.append(TAE.Event(start, e.EndTime, e.Type, e.Unk04, e.GetParameterBytes(False), False))
    return out


def main() -> int:
    load_soulsformats()
    from SoulsFormats import BND3, TAE, BinderFile
    from System import Array, Byte

    ani_path = CHR / "c0000.anibnd.dcx"
    ani = read_binder(BND3, str(ani_path))
    tf = next(f for f in ani.Files if ntpath.basename(f.Name).lower() == "a00.tae")
    tae = read_file(TAE, tf.Bytes)
    src = next(a for a in tae.Animations if int(a.ID) == SOURCE)
    events = er_events(src, TAE)
    for a in [a for a in tae.Animations if int(a.ID) in NEW]:
        tae.Animations.Remove(a)  # ponowne uruchomienie - nadpisujemy
    for new_id in NEW:
        clone = TAE.Animation(new_id, src.AnimFileReference, src.Unknown1, src.Unknown2, f"a00_{new_id:04d}.HKXwin")
        if new_id in LOOP:
            loop_src = next(a for a in tae.Animations if int(a.ID) == LOOP[new_id])
            evs = [TAE.Event(e.StartTime, e.EndTime, e.Type, e.Unk04, e.GetParameterBytes(False), False) for e in loop_src.Events]
        else:
            evs = er_events(src, TAE)
        for e in evs:
            clone.Events.Add(e)
        tae.Animations.Add(clone)
    src.Events.Clear()
    for e in events:
        src.Events.Add(e)
    print(f"  TAE: 903-905 = klon {SOURCE} ({len(events)} zdarzen, okna ER), {SOURCE} przerobione tak samo")
    anims = sorted(list(tae.Animations), key=lambda a: a.ID)
    tae.Animations.Clear()
    for a in anims:
        tae.Animations.Add(a)
    tf.Bytes = to_memory(tae.Write())
    tmp = ani_path.with_suffix(".tmp")
    ani.Write(str(tmp))
    ani.Dispose()
    tmp.replace(ani_path)

    lo_path = CHR / "c0000_a00_lo.anibnd.dcx"
    lo = read_binder(BND3, str(lo_path))
    ref = next(f for f in lo.Files if ntpath.basename(f.Name).lower() == "a00_0900.hkx")
    id_base = int(ref.ID) - 900  # ID wpisu = ID animacji (inaczej T-poza)
    for f in [f for f in lo.Files if int(f.ID) - id_base in NEW]:
        lo.Files.Remove(f)
    for new_id, hkx in NEW.items():
        data = (REPO / hkx).read_bytes()
        name = ntpath.join(ntpath.dirname(ref.Name), f"a00_{new_id:04d}.hkx")
        lo.Files.Add(BinderFile(ref.Flags, id_base + new_id, name, to_memory(Array[Byte](list(data)))))
        print(f"  {new_id} <- {hkx} ({len(data)} B)")
    files = sorted(list(lo.Files), key=lambda f: int(f.ID))
    lo.Files.Clear()
    for f in files:
        lo.Files.Add(f)
    tmp = lo_path.with_suffix(".tmp")
    lo.Write(str(tmp))
    lo.Dispose()
    tmp.replace(lo_path)
    print(f"OK -> {CHR}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
