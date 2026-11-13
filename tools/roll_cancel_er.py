"""
roll_cancel_er.py - per-action cancel windows of roll animations taken from Elden Ring.

The first port of the ER roll timings gave every cancel window of a roll the same start time (the earliest
one, "right hand attack"). ER staggers them: for the heavy roll attack 0.767 s, guard 0.867 s, item 0.900 s,
next dodge 0.933 s, movement 1.000 s. With all of them at 0.767 s the heavy roll could be chained too fast
and the animation was cut early by movement.

For each DSR roll animation (a00.tae in the mod's c0000.anibnd.dcx) the start time of every cancel event
(JumpTable 4, 11, 16, 22, 26, 29, 31, 32) is set to the start time of the same JumpTable id in the matching
ER animation (ER c0000.anibnd.dcx, a00.tae). End times and all other events stay as they are.

ActivateJumpTableEarly events: each one names a JumpTable id (first int16 of its parameters) and lets that
cancel fire before its window opens. Vanilla puts them 0.1 s before the windows. The first port moved the
start of all of them to (earliest window - 0.1 s), so every cancel - movement included - really fired
about 0.1 s before the ATTACK window (log 2026-11-12: heavy roll 720 ended by movement 0.72-0.735 s after
its start in 19 of 19 rolls, with the movement window at 1.15 s). Here each such event is moved to
(start of its own window - --early-lead).

DSR -> ER: 700-703 -> 27100-27103 (light), 710-713 -> 27110-27113 (medium), 720-723 -> 27120-27123 (heavy).
Default: heavy only. Safe to run again (idempotent).

Usage: python tools/roll_cancel_er.py [--anims 720 721 722 723] [--dry-run]
"""
from __future__ import annotations

import argparse
import ntpath
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from sfbridge import load_soulsformats, read_binder, read_file, to_memory  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
MOD_ANI = ROOT / "dist" / "mods" / "c0000_er_engine" / "files" / "chr" / "c0000.anibnd.dcx"
ER_ANI = Path(r"C:\Users\nemos\workspace\nuxe\chr\c0000.anibnd.dcx")
CANCEL_JT = (4, 11, 16, 22, 26, 29, 31, 32)


def er_anim_id(dsr_id: int) -> int:
    weight, direction = (dsr_id - 700) // 10, dsr_id % 10
    if not (700 <= dsr_id <= 723 and direction <= 3):
        raise ValueError(f"no ER counterpart for DSR animation {dsr_id}")
    return 27100 + 10 * weight + direction


def jt_id(ev) -> int | None:
    p = bytes(ev.GetParameterBytes(False))
    return struct.unpack_from("<i", p)[0] if int(ev.Type) == 0 and len(p) >= 4 else None


def a00(bnd):
    return next(f for f in bnd.Files if ntpath.basename(f.Name).lower() == "a00.tae")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Roll cancel windows from Elden Ring.")
    ap.add_argument("--anims", type=int, nargs="+", default=[720, 721, 722, 723])
    ap.add_argument("--anibnd", type=Path, default=MOD_ANI)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--delay", type=float, default=0.0,
                    help="seconds added on top of the ER start time (tuning beyond ER) for the --delay-jt windows")
    ap.add_argument("--delay-jt", type=int, nargs="+", default=[26, 11],
                    help="JumpTable ids that get --delay (default: 26 next dodge, 11 movement)")
    ap.add_argument("--early-lead", type=float, default=0.1,
                    help="ActivateJumpTableEarly starts this many seconds before its cancel window (vanilla: 0.1)")
    ap.add_argument("--dodge-lead", type=float, default=None,
                    help="separate lead for JumpTable 26 (next dodge); log 2026-11-12: the next roll starts "
                         "about 0.02-0.06 s after the early event, so 0 makes roll chaining match the ER window")
    args = ap.parse_args(argv)

    from tae_compare import DSAS, template
    early_type = next(i for i, (name, _) in template(DSAS / "TAE.Template.DS1.xml").items() if name == "ActivateJumpTableEarly")

    load_soulsformats()
    from SoulsFormats import BND3, BND4, TAE

    er_bnd = read_binder(BND4, str(ER_ANI))
    er_tae = read_file(TAE, a00(er_bnd).Bytes)
    er_starts: dict[int, dict[int, float]] = {}
    for a in er_tae.Animations:
        starts: dict[int, float] = {}
        for e in a.Events:
            j = jt_id(e)
            if j in CANCEL_JT:
                starts[j] = min(starts.get(j, 1e9), float(e.StartTime))
        er_starts[int(a.ID)] = starts
    er_bnd.Dispose()

    bnd = read_binder(BND3, str(args.anibnd.resolve()))
    f = a00(bnd)
    tae = read_file(TAE, f.Bytes)
    total = 0
    for a in tae.Animations:
        if int(a.ID) not in args.anims:
            continue
        src = er_starts.get(er_anim_id(int(a.ID)))
        if not src:
            sys.exit(f"ERROR: ER animation {er_anim_id(int(a.ID))} has no cancel events")
        src = {j: round(t + (args.delay if j in args.delay_jt else 0.0), 3) for j, t in src.items()}
        events, notes = list(a.Events), []
        for i, e in enumerate(events):
            j = jt_id(e)
            if j not in CANCEL_JT:
                continue
            if j not in src:
                notes.append(f"JT{j} {e.StartTime:.3f} (not in ER, kept)")
                continue
            if abs(float(e.StartTime) - src[j]) > 0.001:
                notes.append(f"JT{j} {e.StartTime:.3f}->{src[j]:.3f}")
                events[i] = TAE.Event(src[j], max(float(e.EndTime), src[j]), e.Type, e.Unk04, e.GetParameterBytes(False), False)
                total += 1
        # ActivateJumpTableEarly: follow the window of the JumpTable it names
        windows = {jt_id(e): float(e.StartTime) for e in events if jt_id(e) in CANCEL_JT}
        for i, e in enumerate(events):
            if int(e.Type) != early_type:
                continue
            p = bytes(e.GetParameterBytes(False))
            j = struct.unpack_from("<h", p)[0] if len(p) >= 2 else None
            if j not in windows:
                continue
            lead = args.dodge_lead if (j == 26 and args.dodge_lead is not None) else args.early_lead
            start = round(max(0.0, windows[j] - lead), 3)
            if abs(float(e.StartTime) - start) > 0.001:
                notes.append(f"early JT{j} {e.StartTime:.3f}->{start:.3f}")
                events[i] = TAE.Event(start, max(float(e.EndTime), start + 0.1), e.Type, e.Unk04, e.GetParameterBytes(False), False)
                total += 1
        a.Events.Clear()
        for e in events:
            a.Events.Add(e)
        print(f"  {a.ID} <- ER {er_anim_id(int(a.ID))}: " + (", ".join(notes) or "no change"))
    if args.dry_run:
        print(f"dry run: {total} events would change")
        return 0
    f.Bytes = to_memory(tae.Write())
    tmp = args.anibnd.resolve().with_suffix(".tmp")
    bnd.Write(str(tmp))
    bnd.Dispose()
    tmp.replace(args.anibnd.resolve())
    print(f"OK: {total} events changed in {args.anibnd}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
