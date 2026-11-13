"""Ksztalt atakow z samych animacji (bez TAE): dlugosc, przesuniecie (root motion), moment i miejsce
najszybszego ruchu broni. Sluzy do dobrania par atakow DSR c2232 (Asylum Demon) <-> ER c4810 (te same numery != ten sam atak).

  python tools/boss_attack_shapes.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from boss_anim_port import BP, frames_to_arrays, parents_of, ref_arrays, to_model_space  # noqa: E402
from havokbridge import load_havok  # noqa: E402


def describe(anim, skel, weapon: str, hand: str, scale: float) -> str:
    c = anim.animation_container
    ci = c.to_interleaved_container() if c.is_spline else c
    names = [b.name for b in skel.bones]
    ref = ref_arrays(skel)
    T, Q = frames_to_arrays(ci.interleaved_data, list(c.hkx_binding.transformTrackToBoneIndices), len(names), ref)
    P, rots = to_model_space(parents_of(skel), T, Q)
    F = T.shape[0]
    try:
        rm = c.get_reference_frame_samples().astype(np.float64)
    except ValueError:  # animacja bez root motion
        rm = np.zeros((F, 4))
    n = min(F, rm.shape[0])
    w = names.index(weapon)
    # punkt 2 m (w skali DSR) wzdluz broni: kierunek = od dloni do kosci broni
    h = names.index(hand)
    axis = P[:, w] - P[:, h]
    axis /= np.linalg.norm(axis, axis=1)[:, None] + 1e-9
    tip = (P[:, w] + axis * (2.0 / scale))[:n]
    yaw = rm[:n, 3]
    cs, sn = np.cos(yaw), np.sin(yaw)
    world = np.stack([cs * tip[:, 0] + sn * tip[:, 2], tip[:, 1], -sn * tip[:, 0] + cs * tip[:, 2]], axis=1) + rm[:n, :3]
    world *= scale
    speed = np.linalg.norm(np.diff(world, axis=0), axis=1) * 30
    k = int(np.argmax(speed))
    low = int(np.argmin(world[:, 1]))
    return (f"{(F - 1) / 30:5.2f} s | przesuniecie koncowe x {rm[-1, 0] * scale:+5.2f} z {rm[-1, 2] * scale:+5.2f} obr {np.degrees(rm[-1, 3]):+6.1f} | "
            f"bron najszybciej {k / 30:4.2f} s ({speed[k]:4.1f} m/s) w {np.round(tip[k] * scale, 1)} | "
            f"najnizej {low / 30:4.2f} s (y {world[low, 1]:4.2f})")


def main() -> None:
    load_havok()
    from soulstruct.havok.core import HKX
    from soulstruct.havok.fromsoft import darksouls1r as d, eldenring as e
    dsk = d.SkeletonHKX.from_path(BP / "dsr_c2232/anibnd/Skeleton.HKX").skeleton
    comp = HKX.from_path(BP / "er_c4810/anibnd/c4810.compendium")
    esk = e.SkeletonHKX.from_path(BP / "er_c4810/anibnd/skeleton.hkx", compendium=comp).skeleton
    print("przod postaci = -Z. Pozycje broni w ukladzie postaci, w skali DSR.")
    for p in sorted((BP / "dsr_c2232/anibnd").glob("a00_3*.hkx")):
        print(f"DSR {p.stem[-4:]}: " + describe(d.AnimationHKX.from_path(p), dsk, "R_weapon", "R Hand", 1.0))
    for p in sorted((BP / "er_c4810/anibnd").glob("a000_0030*.hkx")):
        print(f"ER  {p.stem[-4:]}: " + describe(e.AnimationHKX.from_path(p, compendium=comp), esk, "R_Club", "R_Hand", 3.23 / 2.80))


if __name__ == "__main__":
    main()
