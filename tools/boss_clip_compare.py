"""Compare a boss's original DSR clip with its ported NR clip on the same DSR skeleton (read-only).

Per clip: frames, the lowest point of the body (min model-space Y over all bones, relative to the rest pose),
the root / pelvis height range, and the bones that differ most from the DSR clip (max distance over the clip)
grouped by name prefix. Used for the Centipede "model under the lava" and "tentacles cannot be hit" reports.

  python tools\\boss_clip_compare.py --dsr c5200 --ported c5200 --anims 3000 3001 ... [--top 8]
"""
from __future__ import annotations

import argparse
import re
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from boss_anim_port import BP, frames_to_arrays, parents_of, ref_arrays, to_model_space  # noqa: E402
from havokbridge import load_havok  # noqa: E402


def load_clip(d, path: Path, par, ref):
    a = d.AnimationHKX.from_path(path)
    c = a.animation_container
    c = c.to_interleaved_container() if c.is_spline else c
    ac = a.animation_container
    tracks = list(ac.hkx_binding.transformTrackToBoneIndices)
    bad = [(ti, bi) for ti, bi in enumerate(tracks) if not 0 <= bi < len(par)]
    if bad:  # a track bound to a bone the skeleton does not have: the game reads past the bone array
        print(f"   !! {path.name}: {len(bad)} of {len(tracks)} tracks bound to bones outside the skeleton "
              f"({len(par)} bones): {bad[:6]}")
        frames = [[fr[ti] for ti, bi in enumerate(tracks) if 0 <= bi < len(par)] for fr in c.interleaved_data]
        tracks = [bi for bi in tracks if 0 <= bi < len(par)]
    else:
        frames = c.interleaved_data
    T, Q = frames_to_arrays(frames, tracks, len(par), ref)
    P, _ = to_model_space(par, T, Q)
    dur = float(ac.hkx_animation.duration)
    return P, dur


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dsr", required=True, help="e.g. c5200 (work/boss_port/dsr_<x>/anibnd)")
    ap.add_argument("--ported", required=True, help="e.g. c5200 (work/boss_port/nr_ported/<x>)")
    ap.add_argument("--anims", type=int, nargs="+", required=True)
    ap.add_argument("--top", type=int, default=6)
    args = ap.parse_args(argv)
    load_havok()
    from soulstruct.havok.fromsoft import darksouls1r as d

    DD = BP / f"dsr_{args.dsr}" / "anibnd"
    PD = BP / "nr_ported" / args.ported
    skel = d.SkeletonHKX.from_path(next(p for p in DD.iterdir() if p.name.lower() == "skeleton.hkx")).skeleton
    names = [str(b.name) for b in skel.bones]
    par = parents_of(skel)
    ref = ref_arrays(skel)
    Pref, _ = to_model_space(par, ref[0][None], ref[1][None])
    rest_min_y = float(Pref[0, :, 1].min())
    for aid in args.anims:
        fn = f"a00_{aid:04d}.hkx"
        Pd, dd = load_clip(d, DD / fn, par, ref)
        Pn, dn = load_clip(d, PD / fn, par, ref)
        F = min(len(Pd), len(Pn))
        # compare on a common normalised time axis (clips may have different lengths)
        idx_d = np.linspace(0, len(Pd) - 1, F).round().astype(int)
        idx_n = np.linspace(0, len(Pn) - 1, F).round().astype(int)
        diff = np.linalg.norm(Pd[idx_d] - Pn[idx_n], axis=2)  # [F, B]
        groups: dict[str, float] = defaultdict(float)
        for b, n in enumerate(names):
            g = re.sub(r"[_ ]?\d+$", "", n)
            groups[g] = max(groups[g], float(diff[:, b].max()))
        top = sorted(groups.items(), key=lambda kv: -kv[1])[: args.top]
        low_d = float(Pd[:, :, 1].min()) - rest_min_y
        low_n = float(Pn[:, :, 1].min()) - rest_min_y
        root = 0
        print(f"== {aid}: DSR {dd:.2f} s / NR {dn:.2f} s | lowest body point vs rest: DSR {low_d:+.2f} m, NR {low_n:+.2f} m"
              f" | root Y DSR {Pd[:, root, 1].min():+.2f}..{Pd[:, root, 1].max():+.2f}, NR {Pn[:, root, 1].min():+.2f}..{Pn[:, root, 1].max():+.2f}")
        print("   largest bone differences (m): " + ", ".join(f"{g} {v:.2f}" for g, v in top))
    return 0


if __name__ == "__main__":
    sys.exit(main())
