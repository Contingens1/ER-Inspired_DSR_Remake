"""When do the feet settle in an Elden Ring jump attack landing (read-only, ER files in nuxe\\chr)?

ER landing clips (swing ID + 40, e.g. a035_031070) go: touchdown (left foot forward) -> wide lunge (right foot ~0.8 m
forward) -> a quick step back into the stance (left foot forward, the same stance as the DSR idle a00_0000). The
TAE "BlendToIdleOrMovementAnim" time used before as the end of a landing without input falls in the middle of that
step for some clips (a35 R1: 1.62 s, the feet still 0.14 m apart from the stance), so ending there snapped the legs
(player test 2026-11-14: "nogi zamieniaja sie miejscami"). settle_ms() gives the first time after which both feet
stay within TOL of their final position.

  python tools/er_land_settle.py 35 31070 29 31070 ...     # prints the settle times
"""
from __future__ import annotations

import ntpath
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from boss_anim_port import frames_to_arrays, parents_of, ref_arrays, to_model_space  # noqa: E402

ER_CHR = Path(r"C:\Users\nemos\workspace\nuxe\chr")
TOL = 0.03
_cache: dict = {}


def _ctx():
    if "skel" in _cache:
        return _cache
    from havokbridge import load_havok
    from sfbridge import load_soulsformats, read_binder
    load_havok()
    sf = load_soulsformats()
    from soulstruct.havok.core import HKX
    from soulstruct.havok.fromsoft import eldenring as e
    _cache.update(sf=sf, read_binder=read_binder, HKX=HKX, e=e, binders={})
    for f in read_binder(sf.BND4, str(ER_CHR / "c0000.anibnd.dcx")).Files:
        if ntpath.basename(str(f.Name)).lower() == "skeleton.hkx":
            sk = e.SkeletonHKX.from_bytes(bytes(f.Bytes.ToArray())).skeleton
            _cache["skel"] = sk
    return _cache


def _entries(container: str):
    c = _ctx()
    if container not in c["binders"]:
        files = list(c["read_binder"](c["sf"].BND4, str(ER_CHR / f"{container}.anibnd.dcx")).Files)
        ents = {ntpath.basename(str(f.Name)).lower(): bytes(f.Bytes.ToArray()) for f in files}
        comp_name = next((n for n in ents if n.endswith(".compendium")), None)
        comp = c["HKX"].from_bytes(ents[comp_name]) if comp_name else None
        c["binders"][container] = (ents, comp)
    return c["binders"][container]


def settle_ms(group: int, anim: int) -> int | None:
    """Settle time [ms] of ER clip a0GG_0NNNNN, or None when the clip is not in the ER files."""
    c = _ctx()
    container = f"c0000_a{group // 10}x" if group >= 10 else "c0000_a00_md"
    ents, comp = _entries(container)
    data = ents.get(f"a{group:03d}_{anim:06d}.hkx")
    if data is None:
        return None
    a = c["e"].AnimationHKX.from_bytes(data, compendium=comp)
    ac = a.animation_container
    ci = ac.to_interleaved_container() if ac.is_spline else ac
    sk = c["skel"]
    names = [b.name for b in sk.bones]
    par, ref = parents_of(sk), ref_arrays(sk)
    T, Q = frames_to_arrays(ci.interleaved_data, list(ac.hkx_binding.transformTrackToBoneIndices), len(names), ref)
    P, _ = to_model_space(par, T, Q)
    feet = P[:, [names.index("L_Foot"), names.index("R_Foot")]][:, :, [0, 2]]
    dev = np.linalg.norm(feet - feet[-1][None], axis=2).max(axis=1)
    moving = np.nonzero(dev > TOL)[0]
    dur = float(ac.hkx_animation.duration)
    k = int(moving[-1]) + 1 if len(moving) else 0
    return int(round(dur * k / max(len(P) - 1, 1) * 1000))


if __name__ == "__main__":
    args = [int(x) for x in sys.argv[1:]]
    for g, aid in zip(args[::2], args[1::2]):
        print(f"a{g:03d}_{aid:06d}: feet settle at {settle_ms(g, aid)} ms")
