"""
apply_estus_walk.py - picie estusa w ruchu (dane TAE).

Blok tarcza pozwala chodzic, bo jego animacje (a13: 1, 100) maja przez caly czas zdarzenie
JumpTable 37 "Left/Right Movement Possible"; animacje picia (a00: 7585 start, 7586 picie,
7587 koniec) go nie maja, za to maja JT7 "Disable Turning". Narzedzie w animacjach picia:
  - dodaje JT37 na caly czas trwania (parametry skopiowane z animacji bloku a13:1),
  - usuwa JT7.
Animacje picia na gornej czesci ciala (warstwy 5/17) przelacza er_engine.dll.
Dziala na pliku moda (files/chr/c0000.anibnd.dcx) - uruchamiac PO tools/add_jump_anims.py.

Uzycie (CMD): python tools\\apply_estus_walk.py
"""
from __future__ import annotations

import argparse
import ntpath
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from sfbridge import load_soulsformats, read_binder, read_file, to_memory  # noqa: E402

# 7588 (empty flask) and 7589 (shrug) added 2026-11-12: the patched ESD plays them on the upper body too,
# so with JT7 left in place the character could walk only straight ahead.
# 7500 (crushed soul) and 7501 (humanity) added 2026-11-13: same patched ESD states (1 and 15), same problem.
DRINK_ANIMS = (7500, 7501, 7585, 7586, 7587, 7588, 7589)
JT_MOVE_POSSIBLE, JT_DISABLE_TURNING = 37, 7

# Cancel windows moved to Elden Ring timings (ER 50111 / 50112; the animations have the same length
# in both games). {anim: {jumptable id: new start time in seconds}}. Only ever moves a window earlier.
ER_CANCEL_START = {
    7586: {31: 0.600},                                      # next sip (DSR 0.667)
    7587: {4: 0.200, 16: 0.200, 22: 0.200, 26: 0.200, 31: 0.200,   # attack / guard / dodge / item (DSR 0.433)
           11: 0.300, 29: 0.300, 32: 0.300},                # movement / magic / generic (DSR 0.533)
}


def retime_cancels(anim) -> int:
    """Rebuild the cancel-window events of a drink animation with ER start times. Returns the count changed."""
    from SoulsFormats import TAE

    wanted = ER_CANCEL_START.get(int(anim.ID), {})
    events, changed = list(anim.Events), 0
    for i, e in enumerate(events):
        start = wanted.get(jt_id(e))
        if start is not None and e.StartTime > start + 0.001:
            events[i] = TAE.Event(start, e.EndTime, e.Type, e.Unk04, e.GetParameterBytes(False), False)
            changed += 1
    if changed:
        anim.Events.Clear()
        for e in events:
            anim.Events.Add(e)
    return changed


def jt_id(ev) -> int | None:
    p = bytes(ev.GetParameterBytes(False))
    return struct.unpack_from("<i", p)[0] if ev.Type == 0 and len(p) >= 4 else None


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Picie estusa w ruchu (TAE).")
    ap.add_argument("--anibnd", type=Path, default=Path("dist/mods/c0000_er_engine/files/chr/c0000.anibnd.dcx"))
    args = ap.parse_args(argv)
    args.anibnd = args.anibnd.resolve()
    if not args.anibnd.exists():
        sys.exit(f"BLAD: brak {args.anibnd} - najpierw tools/add_jump_anims.py")

    load_soulsformats()
    from SoulsFormats import BND3, TAE

    bnd = read_binder(BND3, str(args.anibnd))
    files = {ntpath.basename(f.Name).lower(): f for f in bnd.Files}
    guard = read_file(TAE, files["a13.tae"].Bytes)
    template = next(e for a in guard.Animations if int(a.ID) == 1 for e in a.Events if jt_id(e) == JT_MOVE_POSSIBLE)
    tpl_params = template.GetParameterBytes(False)

    tae = read_file(TAE, files["a00.tae"].Bytes)
    for a in tae.Animations:
        if int(a.ID) not in DRINK_ANIMS:
            continue
        n = retime_cancels(a)
        if n:
            print(f"  {a.ID}: {n} cancel windows moved to ER start times")
        events = list(a.Events)
        if any(jt_id(e) == JT_MOVE_POSSIBLE for e in events):
            print(f"  {a.ID}: juz ma JT37 - pomijam")
            continue
        end = max(e.EndTime for e in events)
        kept = [e for e in events if jt_id(e) != JT_DISABLE_TURNING]
        a.Events.Clear()
        for e in kept:
            a.Events.Add(e)
        a.Events.Add(TAE.Event(0.0, end, template.Type, template.Unk04, tpl_params, False))
        print(f"  {a.ID}: +JT37 (0-{end:.2f} s), usunieto JT7: {len(events) - len(kept)}")
    files["a00.tae"].Bytes = to_memory(tae.Write())
    tmp = args.anibnd.with_suffix(".tmp")
    bnd.Write(str(tmp))
    bnd.Dispose()
    tmp.replace(args.anibnd)
    print(f"OK: {args.anibnd}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
