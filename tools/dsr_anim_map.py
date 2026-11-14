"""Raw animation map of a DSR enemy (read-only): per attack animation its length, hit windows with the attack names
from BehaviorParam row names (Smithbox; mostly the original Japanese), bullets, and root motion (how far the clip
moves the character). Output = Markdown rows to paste into docs/<boss>_anim_map.md and translate there.

  python tools\\dsr_anim_map.py --chr c2790 --variation 27900 --ranges 3000-3999 13000-13999

Needs work/boss_port/dsr_<chr>/anibnd (tools/boss_anim_inventory.py dsr <chr> work/boss_port/dsr_<chr>).
TAE: event type 1 (attack) / 2 (bullet), third int = behavior judge id -> BehaviorParam 2_<variation>_<judge>.
"""
from __future__ import annotations

import argparse
import json
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
from sfbridge import load_soulsformats, read_file, to_memory  # noqa: E402

SB = Path(r"C:\Users\nemos\workspace\toolsy\Smithbox_2_2_6_2026_09_20_b\Assets\PARAM\DS1R")


def row_names(js: str) -> dict[int, str]:
    p = SB / "Param Row Names" / "English" / f"{js}.json"
    if not p.exists():
        return {}
    return {e["ID"]: (e["Entries"][0] if e["Entries"] else "") for e in json.loads(p.read_text(encoding="utf-8"))["Entries"]}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--chr", required=True)
    ap.add_argument("--variation", type=int, required=True, help="NpcParam behaviorVariationId")
    ap.add_argument("--ranges", nargs="+", default=["3000-3999"])
    args = ap.parse_args(argv)
    sf = load_soulsformats()
    names = row_names("BehaviorParam")
    folder = ROOT / "work" / "boss_port" / f"dsr_{args.chr}" / "anibnd"
    tae = read_file(sf.TAE, to_memory(next(folder.glob("*.tae")).read_bytes()))
    ranges = [tuple(int(x) for x in r.split("-")) for r in args.ranges]

    from havokbridge import load_havok
    load_havok()
    from soulstruct.havok.fromsoft import darksouls1r as d

    print("| ID | długość | trafienia (start s: nazwa z BehaviorParam) | pociski | root motion |")
    print("|---|---|---|---|---|")
    for a in sorted(tae.Animations, key=lambda a: int(a.ID)):
        aid = int(a.ID)
        if not any(lo <= aid <= hi for lo, hi in ranges):
            continue
        evs = sorted(a.Events, key=lambda e: float(e.StartTime))
        end = max((float(e.EndTime) for e in evs), default=0.0)
        hits, buls = [], []
        for e in evs:
            raw = bytes(e.GetParameterBytes(False))
            ints = struct.unpack_from(f"<{len(raw) // 4}i", raw) if len(raw) >= 12 else ()
            if int(e.Type) in (1, 2) and len(ints) >= 3:
                bid = 200000000 + args.variation * 1000 + ints[2]
                (hits if int(e.Type) == 1 else buls).append(f"{float(e.StartTime):.2f}: {names.get(bid, f'beh {bid}')}")
        rm = "—"
        hkx = folder / f"a{aid // 10000:02d}_{aid % 10000:04d}.hkx"
        if hkx.exists():
            try:
                c = d.AnimationHKX.from_path(hkx).animation_container
                if c.hkx_animation.extractedMotion:
                    s = c.get_reference_frame_samples()
                    rm = f"{-float(s[-1][2]):+.1f} przód, {float(s[-1][0]):+.1f} bok, {float(s[-1][1]):+.1f} góra"
                else:
                    rm = "brak"
            except Exception as ex:  # noqa: BLE001
                rm = f"? ({type(ex).__name__})"
        print(f"| {aid} | {end:.2f} s | {'; '.join(hits) or '—'} | {'; '.join(buls) or '—'} | {rm} |")
    return 0


if __name__ == "__main__":
    sys.exit(main())
