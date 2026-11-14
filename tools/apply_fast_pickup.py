"""
apply_fast_pickup.py - item pick-up as in Elden Ring (TAE data only).

CORRECTION 2026-11-14: the first version treated 7410-7412 as pick-ups. They are the fog wall: 7411 / 7412 turn the
player 90 deg to face it (imports 602 / 603, 0.67 s, root motion yaw only) and 7410 walks through it (2.19 m root
motion, 98 map events play it on the player). Early cancel windows there let the player stop half way through a
fog wall. The ground pick-up is 7520 (key E, layers 10/25, 1.83 s, no root motion, its own cancel windows from
1.27 s); 7521 / 7522 are its variants.

  --anims IDS        animations to change: cancel windows of the Estus end 7587 (JT4 attack, JT11 movement, JT16
                     guard, JT26 dodge, ...) from --start to the end; --no-cancel leaves them as they are
  --walk-clone N     walkable copy ID+N per animation (JT37 movement possible, no JT 7/8/27/39, same HKX), played
                     on the upper body by er_engine.dll ([Items] PickupWhileMoving); an existing ID that is not an
                     earlier copy of the same animation stops the tool
  --restore IDS      put these entries back as in the main mod's anibnd; --drop IDS removes entries

Reads --src, writes --out (never the main mod's anibnd). Default output: the night test package.

  python tools\\apply_fast_pickup.py --src <night anibnd> --restore 7410 7411 7412 --drop 7440 7441 7442 \\
         --anims 7520 7521 7522 --no-cancel --walk-clone 5
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
    ap.add_argument("--no-cancel", action="store_true", help="leave the cancel windows of --anims as they are")
    ap.add_argument("--restore", type=int, nargs="*", default=[], metavar="ID",
                    help="put these animations back as in the main mod's anibnd (vanilla TAE entries)")
    ap.add_argument("--drop", type=int, nargs="*", default=[], metavar="ID", help="remove these (old walk copies)")
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
    # 2026-11-14: the first version patched 7410-7412, which are NOT pick-ups: 7410 is the walk through a fog wall
    # (98 map events play it on the player, root motion 2.19 m forward) and 7411 / 7412 are the 90 deg turns
    # (602 / 603) the fog events use to face the wall. The ground pick-up is 7520 (E pressed, 1.83 s, no root
    # motion). --restore / --drop undo the first version.
    if args.restore:
        dev_bnd = read_binder(BND3, str(DEV))
        dev_tae = read_file(TAE, next(f for f in dev_bnd.Files if ntpath.basename(f.Name).lower() == "a00.tae").Bytes)
        dev_anims = {int(a.ID): a for a in dev_tae.Animations}
        for rid in args.restore:
            if rid in anims:
                tae.Animations.Remove(anims.pop(rid))
            tae.Animations.Add(dev_anims[rid])
            anims[rid] = dev_anims[rid]
            print(f"  {rid}: restored from {DEV.name} ({len(list(dev_anims[rid].Events))} events)")
        dev_bnd.Dispose()
    for did in args.drop:
        if did in anims:
            tae.Animations.Remove(anims.pop(did))
            print(f"  {did}: removed")
    for aid in args.anims:
        a = anims[aid]
        events = list(a.Events)
        have = {jt_id(e) for e in events}
        end = max(e.EndTime for e in events)
        added = []
        for e in events if not args.no_cancel else []:  # own cancel windows opening later are moved to --start
            if jt_id(e) in CANCEL_JTS and e.StartTime > args.start:
                e.StartTime = args.start
                added.append(f"{jt_id(e)} moved")
        for jt, t in sorted(templates.items()) if not args.no_cancel else []:
            if jt in have:
                continue
            a.Events.Add(TAE.Event(args.start, end, t.Type, t.Unk04, t.GetParameterBytes(False), False))
            added.append(jt)
        if not args.no_cancel:
            print(f"  {aid}: + cancel JT {added} from {args.start:.2f} to {end:.2f} s")
        if args.walk_clone:
            nid = aid + args.walk_clone
            if nid in anims:
                old = anims[nid]
                # only an earlier walk copy of the same animation may be replaced (7550 is a vanilla animation)
                src_id = int(old.Unknown2) if int(old.Unknown1) == 256 else -1
                want_src = int(a.Unknown2) if int(a.Unknown1) == 256 else aid
                if src_id != want_src:
                    sys.exit(f"ERROR: {nid} already exists and is not a walk copy of {aid}; pick another --walk-clone")
                tae.Animations.Remove(anims.pop(nid))
            # same HKX: an own file is imported by ID (flag 256 + source ID), an imported one keeps its source
            ref = int(a.Unknown2) if int(a.Unknown1) == 256 else aid
            # the file name must be the source's (vanilla 7411 imports 602 as "a00_0602.hkxwin"); the first version
            # named a non-existent "a00_7440.HKXwin" - suspected cause of the crash in the pick-up test 2026-11-14
            src_name = str(a.AnimFileName) or f"a00_{ref:04d}.HKXwin"
            clone = TAE.Animation(nid, False, 256, ref, src_name)
            for e in a.Events:
                if jt_id(e) in WALK_DROP:
                    continue
                clone.Events.Add(TAE.Event(e.StartTime, e.EndTime, e.Type, e.Unk04, e.GetParameterBytes(False), False))
            clone.Events.Add(TAE.Event(0.0, end, move_tpl.Type, move_tpl.Unk04, move_tpl.GetParameterBytes(False), False))
            tae.Animations.Add(clone)
            anims[nid] = clone
            print(f"  {nid}: walkable copy of {aid} (HKX of {ref}), JT37 0.00-{end:.2f} s, without JT {list(WALK_DROP)}")
    if args.walk_clone or args.restore:
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
