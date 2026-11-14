"""Length and root motion of Elden Ring / Nightreign enemy clips unpacked by tools/nr_inventory.py --unpack (read-only).

  python tools\\er_clip_summary.py c3070 3000 3001 ... [--set 0]

--set = animation set (a000 = 0, a001 = 1, ...). Root motion = how far the clip moves the character.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from boss_anim_port import BP  # noqa: E402
from havokbridge import load_havok  # noqa: E402


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("chr")
    ap.add_argument("anims", type=int, nargs="+")
    ap.add_argument("--set", type=int, default=0)
    args = ap.parse_args(argv)
    load_havok()
    from soulstruct.havok.core import HKX
    from soulstruct.havok.fromsoft import eldenring as e

    D = BP / f"nr_{args.chr}" / "anibnd"
    cmap = json.loads((D / "compendium_map.json").read_text(encoding="utf-8"))
    comps: dict[str, object] = {}
    for aid in args.anims:
        name = f"a{args.set:03d}_{aid:06d}.hkx"
        p = D / name
        if not p.exists():
            print(f"{aid}: no clip {name}")
            continue
        cname = cmap.get(name, "")
        if cname and cname not in comps:
            comps[cname] = HKX.from_path(D / cname)
        a = e.AnimationHKX.from_path(p, compendium=comps.get(cname)) if cname else e.AnimationHKX.from_path(p)
        c = a.animation_container
        dur = float(c.hkx_animation.duration)
        rm = "no root motion"
        if c.hkx_animation.extractedMotion:
            s = c.get_reference_frame_samples()
            peak = max(float((x[0] ** 2 + x[2] ** 2) ** 0.5) for x in s)
            rm = f"root motion fwd {-float(s[-1][2]):+5.2f} side {float(s[-1][0]):+5.2f} m (max {peak:4.1f} m)"
        print(f"{aid}: {dur:5.2f} s | {rm}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
