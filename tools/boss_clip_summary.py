"""Short motion summary of a DSR boss's clips (read-only): length, root travel (forward / side), highest root rise,
and the moment and height of the fastest hand / weapon-chain movement. Helps to describe attacks in words.

  python tools\\boss_clip_summary.py --dsr c2230 --anims 3000 3001 ...
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from boss_anim_port import BP, parents_of, ref_arrays  # noqa: E402
from boss_clip_compare import load_clip  # noqa: E402
from havokbridge import load_havok  # noqa: E402


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dsr", required=True)
    ap.add_argument("--anims", type=int, nargs="+", required=True)
    args = ap.parse_args(argv)
    load_havok()
    from soulstruct.havok.fromsoft import darksouls1r as d

    DD = BP / f"dsr_{args.dsr}" / "anibnd"
    skel = d.SkeletonHKX.from_path(next(p for p in DD.iterdir() if p.name.lower() == "skeleton.hkx")).skeleton
    names = [str(b.name) for b in skel.bones]
    par, ref = parents_of(skel), ref_arrays(skel)
    hands = [i for i, n in enumerate(names) if n in ("R Hand", "L Hand", "R_weapon", "L_weapon")]
    pel = names.index("Pelvis") if "Pelvis" in names else 1
    for aid in args.anims:
        path = DD / f"a00_{aid:04d}.hkx"
        if not path.exists():
            print(f"{aid}: no clip {path.name}")
            continue
        P, dur = load_clip(d, path, par, ref)
        F = len(P)
        fps = (F - 1) / dur if dur > 0 else 30.0
        rise = float(P[:, pel, 1].max() - P[0, pel, 1])
        rm = ""
        a = d.AnimationHKX.from_path(path)
        if a.animation_container.hkx_animation.extractedMotion:  # root motion (moves the character in the world)
            s = a.animation_container.get_reference_frame_samples()
            end, yaw = s[-1], float(s[-1][3]) if len(s[-1]) > 3 else 0.0
            peak = max(float((x[0] ** 2 + x[2] ** 2) ** 0.5) for x in s)
            rm = f" | root motion fwd {-end[2]:+5.2f} side {end[0]:+5.2f} up {end[1]:+5.2f} m (max dist {peak:4.1f} m, yaw {np.degrees(yaw):+4.0f} deg)"
        line = f"{aid}: {dur:5.2f} s{rm} | pelvis rise {rise:+5.2f} m"
        if hands:
            v = np.linalg.norm(np.diff(P[:, hands], axis=0), axis=2) * fps  # [F-1, H]
            f, h = np.unravel_index(int(v.argmax()), v.shape)
            line += (f" | fastest {names[hands[h]]} at {f / fps:4.2f} s ({v[f, h]:4.1f} m/s,"
                     f" height {P[f, hands[h], 1]:+4.2f} m, fwd {-P[f, hands[h], 2]:+4.2f} m)")
        print(line)
    return 0


if __name__ == "__main__":
    sys.exit(main())
