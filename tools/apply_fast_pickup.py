"""
apply_fast_pickup.py - item pick-up that can be cancelled early, as in Elden Ring (TAE data only).

The ground pick-up 7412 (played on layers 10/25; a00.tae) holds JT8 / JT27 / JT7 / JT39 for its whole 2.30 s and has no
cancel window at all, so the player stands until the animation ends (the move flag ActionCtrl+0x1DC 0x100000 stays
down the whole time, see docs/RAPORT_NOCY_2026-11-14.md). The item is taken at 0.23-0.43 s (event 112 3100 / 128 8).
This tool adds the cancel windows of the Estus end 7587 (JT4 attack, JT11 movement, JT16 guard, JT26 dodge, ...,
parameter bytes copied from 7587) from --start seconds to the end of the animation.

Reads --src, writes --out (never in place on the dev package). Default output: the night test package.

Usage (CMD): python tools\\apply_fast_pickup.py [--start 0.5] [--anims 7412]
"""
from __future__ import annotations

import argparse
import ntpath
import shutil
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from sfbridge import load_soulsformats, read_binder, read_file, to_memory  # noqa: E402

TEMPLATE_ANIM = 7587                      # Estus end: full set of ER-timed cancel windows
CANCEL_JTS = (4, 11, 16, 22, 26, 29, 31, 32)
WALK_DROP = (7, 8, 27, 39)                # turning lock, i-frames, ignore gravity, JT39
JT_MOVE_POSSIBLE = 37                     # template: guard a13 1 (walking while blocking), as tools/apply_estus_walk.py
DEV = Path("dist/mods/c0000_er_engine/files/chr/c0000.anibnd.dcx").resolve()


def jt_id(ev) -> int | None:
    p = bytes(ev.GetParameterBytes(False))
    return struct.unpack_from("<i", p)[0] if ev.Type == 0 and len(p) >= 4 else None


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Early-cancellable item pick-up (TAE).")
    ap.add_argument("--src", type=Path, default=Path("dist/mods/c0000_er_engine/files/chr/c0000.anibnd.dcx"))
    ap.add_argument("--out", type=Path, default=Path("dist/mods/bossy_nightreign/files_c0000_night/chr/c0000.anibnd.dcx"))
    ap.add_argument("--start", type=float, default=0.5, help="cancel windows open at this time (s)")
    ap.add_argument("--anims", type=int, nargs="+", default=[7412])
    ap.add_argument("--walk-clone", type=int, default=0, metavar="N", help="add walkable copies ID+N (0 = none)")
    args = ap.parse_args(argv)
    src, out = args.src.resolve(), args.out.resolve()
    if out == DEV:
        sys.exit("ERROR: the main mod's anibnd is never patched (write to a test package)")
    out.parent.mkdir(parents=True, exist_ok=True)
    if src != out:
        shutil.copyfile(src, out)

    load_soulsformats()
    from SoulsFormats import BND3, TAE

    bnd = read_binder(BND3, str(out))
    files = {ntpath.basename(f.Name).lower(): f for f in bnd.Files}
    tae = read_file(TAE, files["a00.tae"].Bytes)
    anims = {int(a.ID): a for a in tae.Animations}
    templates = {jt_id(e): e for e in anims[TEMPLATE_ANIM].Events if jt_id(e) in CANCEL_JTS}
    guard = read_file(TAE, files["a13.tae"].Bytes)
    move_tpl = next(e for x in guard.Animations if int(x.ID) == 1 for e in x.Events if jt_id(e) == JT_MOVE_POSSIBLE)
    for aid in args.anims:
        a = anims[aid]
        events = list(a.Events)
        have = {jt_id(e) for e in events}
        end = max(e.EndTime for e in events)
        added = []
        for e in events:  # own cancel windows that open later (7410: 2.77 s) are moved to --start
            if jt_id(e) in CANCEL_JTS and e.StartTime > args.start:
                e.StartTime = args.start
                added.append(f"{jt_id(e)} moved")
        for jt, t in sorted(templates.items()):
            if jt in have:
                continue
            a.Events.Add(TAE.Event(args.start, end, t.Type, t.Unk04, t.GetParameterBytes(False), False))
            added.append(jt)
        print(f"  {aid}: + cancel JT {added} from {args.start:.2f} to {end:.2f} s")
        if args.walk_clone:
            nid = aid + args.walk_clone
            if nid in anims:
                tae.Animations.Remove(anims.pop(nid))
            # same HKX: an own file is imported by ID (flag 256 + source ID), an imported one keeps its source
            ref = int(a.Unknown2) if int(a.Unknown1) == 256 else aid
            clone = TAE.Animation(nid, False, 256, ref, f"a00_{nid}.HKXwin")
            for e in a.Events:
                if jt_id(e) in WALK_DROP:
                    continue
                clone.Events.Add(TAE.Event(e.StartTime, e.EndTime, e.Type, e.Unk04, e.GetParameterBytes(False), False))
            clone.Events.Add(TAE.Event(0.0, end, move_tpl.Type, move_tpl.Unk04, move_tpl.GetParameterBytes(False), False))
            tae.Animations.Add(clone)
            anims[nid] = clone
            print(f"  {nid}: walkable copy of {aid} (HKX of {ref}), JT37 0.00-{end:.2f} s, without JT {list(WALK_DROP)}")
    if args.walk_clone:
        srt = sorted(list(tae.Animations), key=lambda x: int(x.ID))
        tae.Animations.Clear()
        for x in srt:
            tae.Animations.Add(x)
    files["a00.tae"].Bytes = to_memory(tae.Write())
    tmp = out.with_suffix(".tmp")
    bnd.Write(str(tmp))
    bnd.Dispose()
    tmp.replace(out)
    print(f"OK: {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
