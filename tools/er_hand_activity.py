"""How much each hand of an Elden Ring / Nightreign enemy moves in its clips (read-only).
Tells a one-weapon move set from a dual-wield one: peak speed of L_Hand / R_Hand and how far each hand travels.

  python tools\\er_hand_activity.py c3070 3000 3001 ... [--sets 0 1 2]

Clips must be unpacked by tools/nr_inventory.py --unpack.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from boss_anim_port import BP, frames_to_arrays, parents_of, ref_arrays, to_model_space  # noqa: E402
from havokbridge import load_havok  # noqa: E402


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("chr")
    ap.add_argument("anims", type=int, nargs="+")
    ap.add_argument("--sets", type=int, nargs="+", default=[0])
    args = ap.parse_args(argv)
    load_havok()
    from soulstruct.havok.core import HKX
    from soulstruct.havok.fromsoft import eldenring as e

    D = BP / f"nr_{args.chr}" / "anibnd"
    skel = e.SkeletonHKX.from_path(D / "skeleton.hkx").skeleton
    names = [str(b.name) for b in skel.bones]
    par, ref = parents_of(skel), ref_arrays(skel)
    hands = [names.index(n) for n in ("L_Hand", "R_Hand") if n in names]
    cmap = json.loads((D / "compendium_map.json").read_text(encoding="utf-8"))
    comps: dict[str, object] = {}
    for s in args.sets:
        for aid in args.anims:
            name = f"a{s:03d}_{aid:06d}.hkx"
            p = D / name
            if not p.exists():
                continue
            cname = cmap.get(name, "")
            if cname and cname not in comps:
                comps[cname] = HKX.from_path(D / cname)
            a = e.AnimationHKX.from_path(p, compendium=comps.get(cname)) if cname else e.AnimationHKX.from_path(p)
            c = a.animation_container
            ic = c.to_interleaved_container() if c.is_spline else c
            tracks = list(c.hkx_binding.transformTrackToBoneIndices)
            T, Q = frames_to_arrays(ic.interleaved_data, tracks, len(par), ref)
            P, _ = to_model_space(par, T, Q)
            dur = float(c.hkx_animation.duration)
            fps = (len(P) - 1) / dur if dur > 0 else 30.0
            parts = []
            for h in hands:
                v = np.linalg.norm(np.diff(P[:, h], axis=0), axis=1) * fps
                path = float(np.linalg.norm(np.diff(P[:, h], axis=0), axis=1).sum())
                f = int(v.argmax())
                parts.append(f"{names[h]} peak {v[f]:5.1f} m/s at {f / fps:4.2f} s (height {P[f, h, 1]:+4.2f} fwd {-P[f, h, 2]:+4.2f} m) path {path:5.1f} m")
            print(f"a{s:03d} {aid}: {dur:4.2f} s | " + " | ".join(parts))
    return 0


if __name__ == "__main__":
    sys.exit(main())
