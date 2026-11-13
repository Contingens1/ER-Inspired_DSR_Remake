"""
set_jump_gravity.py - okno "Ignore Gravity" (JumpTable 27) w skokach 900/901/902 na czas animacji ER.

Animacje skoku z ER maja wysokosc w ruchu postaci (root motion y, szczyt ~1.15 m), ale DSR stosuje
ja tylko, gdy w TAE trwa JT27 "Ignore Gravity" (wanilia: 0-0.1 s; mod Realistic Jump wydluza do 0.33 s).
Ustawiamy koniec JT27 na czas animacji ER wybicia; potem grawitacja i ladowanie DSR.

Uzycie (CMD): python tools\\set_jump_gravity.py   (dziala na files/chr/c0000.anibnd.dcx moda)
"""
from __future__ import annotations

import ntpath
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from sfbridge import load_soulsformats, read_binder, read_file, to_memory  # noqa: E402

ANIBND = Path(__file__).resolve().parent.parent / "dist/mods/c0000_er_engine/files/chr/c0000.anibnd.dcx"
# anim DSR -> koniec JT27 (s) = (probki root motion ER - 1) / 30: 202030 24, 202000 27, 202020 26
GRAVITY_END = {900: 23 / 30, 901: 26 / 30, 902: 25 / 30}
CANCELS = {4, 11, 16, 22, 26, 29, 31, 32}  # okna przerwan: atak, ruch, blok, przewrot, czar, przedmiot, ogolne


def main() -> int:
    load_soulsformats()
    from SoulsFormats import BND3, TAE
    bnd = read_binder(BND3, str(ANIBND))
    f = next(f for f in bnd.Files if ntpath.basename(f.Name).lower() == "a00.tae")
    tae = read_file(TAE, f.Bytes)
    for a in tae.Animations:
        aid = int(a.ID)
        if aid not in GRAVITY_END:
            continue
        for e in [e for e in a.Events if int(e.Type) == 0 and struct.unpack_from("<i", bytes(e.GetParameterBytes(False)))[0] == 7]:
            a.Events.Remove(e)  # JT7 Disable Turning - w locie obrot (sterowanie jak w ER, DLL dosuwa)
            print(f"  {aid}: usuniete JT7 {e.StartTime:.3f}-{e.EndTime:.3f}")
        for e in a.Events:
            p = bytes(e.GetParameterBytes(False))
            if aid in (901, 902) and int(e.Type) == 0 and len(p) >= 4 and struct.unpack_from("<i", p)[0] in CANCELS and e.StartTime < GRAVITY_END[aid]:
                # okna przerwan (add_jump_anims: od 0.70 s) - z trzymanym kierunkiem JT11 przerywal skok w locie
                print(f"  {aid}: JT{struct.unpack_from('<i', p)[0]} start {e.StartTime:.3f} -> {GRAVITY_END[aid]:.3f}")
                e.StartTime = GRAVITY_END[aid]
            if int(e.Type) == 0 and len(p) >= 4 and struct.unpack_from("<i", p)[0] == 66 and e.StartTime < 1.0:
                # JT66 Special Transition (wanilia 0.567-0.6 s): tu gra przechodzi w spadanie, gdy postac jest w powietrzu
                # (log: przerwanie skoku po ~0.7 s) - przesuwamy na koniec wybicia ER.
                s = GRAVITY_END[aid] - 0.033
                print(f"  {aid}: JT66 {e.StartTime:.3f}-{e.EndTime:.3f} -> {s:.3f}-{GRAVITY_END[aid]:.3f}")
                e.StartTime, e.EndTime = s, GRAVITY_END[aid]
            if int(e.Type) == 0 and len(p) >= 4 and struct.unpack_from("<i", p)[0] == 51:
                # JT51 Disable Fall Motion (wanilia do 0.567 s): po nim gra przerywa skok spadaniem pionowym.
                print(f"  {aid}: JT51 {e.StartTime:.3f}-{e.EndTime:.3f} -> 0.000-{GRAVITY_END[aid]:.3f}")
                e.StartTime, e.EndTime = 0.0, GRAVITY_END[aid]
            if int(e.Type) == 0 and len(p) >= 4 and struct.unpack_from("<i", p)[0] == 27:
                print(f"  {aid}: JT27 {e.StartTime:.3f}-{e.EndTime:.3f} -> 0.000-{GRAVITY_END[aid]:.3f}")
                e.StartTime, e.EndTime = 0.0, GRAVITY_END[aid]
    f.Bytes = to_memory(tae.Write())
    tmp = ANIBND.with_suffix(".tmp")
    bnd.Write(str(tmp))
    bnd.Dispose()
    tmp.replace(ANIBND)
    print(f"OK -> {ANIBND}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
