"""Port animacji przeciwnika ER -> DSR (wlasna sciezka, bez DSAnimStudio): ruch Erdtree Avatara (c4810)
przenoszony na szkielet Asylum Demona (c2230) i zapisywany jako HKX Havok 2015 (spline), ktory czyta DSR.

Metoda: szkielety maja te sama poze spoczynkowa (Avatar = Demon * ~1/1.15), wiec dla kazdej kosci z mapy
  obrot_DSR(t) = obrot_ER(t) * obrot_ER_spocz^-1 * obrot_DSR_spocz          (w przestrzeni modelu)
  pozycja_DSR(t) = pozycja "rodzica logicznego" + jego obrot * odsuniecie z pozy DSR
                   + S * (odchylenie translacji ER od pozy spoczynkowej)
Rodzic logiczny = kosc DSR odpowiadajaca najblizszemu zmapowanemu przodkowi w ER (hierarchie sie roznia:
w DSR uda wisza na kosci Spine, w ER na Pelvis). Kosci bez mapy (koncowki "Nub") zostaja w pozie spoczynkowej.

  python tools/boss_anim_port.py --er-anim 3003 --out work/boss_port/ported/a00_3003.hkx

Wymaga toolsy/soulstruct-havok (+scipy). Kompresja spline: CompressAnim.exe z tego repozytorium.
Nic nie pisze do katalogu gry.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
from scipy.spatial.transform import Rotation as R

sys.path.insert(0, str(Path(__file__).resolve().parent))
from boss_bone_map import c2230_to_c4810  # noqa: E402
from havokbridge import load_havok  # noqa: E402

BP = Path(__file__).resolve().parent.parent / "work" / "boss_port"


def frames_to_arrays(frames, track_bones, bone_count, ref_local):
    """interleaved [klatka][sciezka] -> T[F,B,3], Q[F,B,4] (xyzw) w kolejnosci kosci; brakujace kosci = poza spocz."""
    F = len(frames)
    T = np.repeat(ref_local[0][None], F, axis=0).copy()
    Q = np.repeat(ref_local[1][None], F, axis=0).copy()
    for ti, bi in enumerate(track_bones):
        T[:, bi] = [tuple(fr[ti].translation) for fr in frames]
        Q[:, bi] = [tuple(fr[ti].rotation.data) for fr in frames]
    return T, Q


def ref_arrays(skel):
    poses = [b.get_reference_pose() for b in skel.bones]
    return (np.array([tuple(p.translation) for p in poses], dtype=np.float64),
            np.array([tuple(p.rotation.data) for p in poses], dtype=np.float64))


def to_model_space(parents, T, Q):
    """lokalne -> przestrzen modelu. T[F,B,3], Q[F,B,4] -> P[F,B,3], lista Rotation (po kosci)"""
    B = T.shape[1]
    P = np.zeros_like(T)
    rots: list[R] = [None] * B
    for b in range(B):
        loc = R.from_quat(Q[:, b])
        p = parents[b]
        if p < 0:
            P[:, b], rots[b] = T[:, b], loc
        else:
            assert p < b
            P[:, b] = P[:, p] + rots[p].apply(T[:, b])
            rots[b] = rots[p] * loc
    return P, rots


def parents_of(skel):
    return [b.parent.index if b.parent else -1 for b in skel.bones]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--er-anim", type=int, default=3003)
    ap.add_argument("--dsr-template", type=int, default=3003, help="animacja DSR brana jako wzor (sciezka Master)")
    ap.add_argument("--dsr-chr", default="c2232", help="c2232 = Asylum Demon, c2230 = Stray Demon (ten sam szkielet)")
    ap.add_argument("--out", type=Path)
    ap.add_argument("--interleaved", action="store_true", help="zapisz bez kompresji spline (tylko do diagnostyki)")
    args = ap.parse_args(argv)
    out = args.out.resolve() if args.out else None

    load_havok()
    from soulstruct.havok.core import HKX
    from soulstruct.havok.fromsoft import darksouls1r as d, eldenring as e
    from soulstruct.havok.utilities.maths import Quaternion, TRSTransform, Vector3

    DD = BP / f"dsr_{args.dsr_chr}" / "anibnd"
    dskx = d.SkeletonHKX.from_path(DD / "Skeleton.HKX")
    dsk = dskx.skeleton
    comp = HKX.from_path(BP / "er_c4810/anibnd/c4810.compendium")
    esk = e.SkeletonHKX.from_path(BP / "er_c4810/anibnd/skeleton.hkx", compendium=comp).skeleton
    ean = e.AnimationHKX.from_path(BP / f"er_c4810/anibnd/a000_{args.er_anim:06d}.hkx", compendium=comp)
    dtpl = d.AnimationHKX.from_path(DD / f"a00_{args.dsr_template:04d}.hkx")

    dnames = [b.name for b in dsk.bones]
    enames = [b.name for b in esk.bones]
    dpar, epar = parents_of(dsk), parents_of(esk)
    bmap = c2230_to_c4810()
    d2e = {dnames.index(k): enames.index(v) for k, v in bmap.items()}
    e2d = {v: k for k, v in d2e.items()}
    S = 3.23 / 2.80  # stosunek wysokosci miednicy w pozie spoczynkowej

    # --- ER: klatki w przestrzeni modelu
    ec = ean.animation_container
    eint = ec.to_interleaved_container() if ec.is_spline else ec
    eref = ref_arrays(esk)
    eT, eQ = frames_to_arrays(eint.interleaved_data, list(ec.hkx_binding.transformTrackToBoneIndices), len(enames), eref)
    F = eT.shape[0]
    eP, eRot = to_model_space(epar, eT, eQ)
    ePr, eRr = to_model_space(epar, eref[0][None], eref[1][None])  # poza spoczynkowa (1 klatka)
    escale = np.array([[tuple(t.scale) for t in fr] for fr in eint.interleaved_data])
    print(f"ER a{args.er_anim}: {F} klatek ({(F - 1) / 30:.2f} s), sciezek {eT.shape[1]}, "
          f"skala kosci {escale.min():.3f}..{escale.max():.3f}")

    # --- DSR: poza spoczynkowa i wzor
    dref = ref_arrays(dsk)
    dPr, dRr = to_model_space(dpar, dref[0][None], dref[1][None])
    dc = dtpl.animation_container
    dint = dc.to_interleaved_container()
    dtT, dtQ = frames_to_arrays(dint.interleaved_data, list(dc.hkx_binding.transformTrackToBoneIndices), len(dnames), dref)
    dtP, dtRot = to_model_space(dpar, dtT, dtQ)
    m_move = float(np.abs(dtT[:, 0] - dtT[0, 0]).max())
    print(f"DSR wzor a{args.dsr_template}: {dtT.shape[0]} klatek; Master lokalnie {np.round(dtT[0, 0], 3)} "
          f"(ruch w animacji {m_move:.4f}), Pelvis lokalnie max {np.abs(dtT[:, 1]).max():.4f}, "
          f"obrot Master zmienia sie o {np.degrees((dtRot[0][0].inv() * dtRot[0]).magnitude()).max():.2f} st.")

    # --- przeniesienie
    B = len(dnames)
    P = np.zeros((F, B, 3))
    Rm: list[R] = [None] * B
    T = np.zeros((F, B, 3))
    Q = np.zeros((F, B, 4))
    for b in range(B):
        p = dpar[b]
        if b == 0:  # Master: jak w oryginale DSR niesie pozycje i obrot miednicy (Pelvis lokalnie = poza spoczynkowa)
            pel = dnames.index("Pelvis")
            T[:, 0] = dPr[0, pel] + S * (eP[:, d2e[pel]] - ePr[0, d2e[pel]])
            Rm[0] = eRot[d2e[pel]] * (eRr[d2e[pel]].inv() * dRr[pel]) * (dRr[pel].inv() * dRr[0])
            Q[:, 0] = Rm[0].as_quat()
            P[:, 0] = T[:, 0]
            continue
        if b in d2e:
            x = d2e[b]
            Rm[b] = eRot[x] * (eRr[x].inv() * dRr[b])
            a = epar[x]
            while a >= 0 and (a not in e2d or a == 0):  # Master ER nie jest rodzicem logicznym (rozne polozenie)
                a = epar[a]
            if a < 0:  # brak zmapowanego przodka: odchylenie w przestrzeni modelu
                P[:, b] = dPr[0, b] + S * (eP[:, x] - ePr[0, x])
            else:
                lp = e2d[a]
                off = dRr[lp].inv().apply(dPr[0, b] - dPr[0, lp])[0]
                rel = eRot[a].inv().apply(eP[:, x] - eP[:, a])
                rel0 = eRr[a].inv().apply(ePr[0, x] - ePr[0, a])[0]
                P[:, b] = P[:, lp] + Rm[lp].apply(off) + S * eRot[a].apply(rel - rel0)
            T[:, b] = Rm[p].inv().apply(P[:, b] - P[:, p])
            Q[:, b] = (Rm[p].inv() * Rm[b]).as_quat()
        else:
            T[:, b], Q[:, b] = dref[0][b], dref[1][b]
            P[:, b] = P[:, p] + Rm[p].apply(T[:, b])
            Rm[b] = Rm[p] * R.from_quat(Q[:, b])
    # ciaglosc znaku kwaternionow
    for b in range(B):
        for f in range(1, F):
            if np.dot(Q[f, b], Q[f - 1, b]) < 0:
                Q[f, b] = -Q[f, b]

    # --- kontrole
    drift = np.abs(np.linalg.norm(T, axis=2) - np.linalg.norm(dref[0], axis=1)[None]).max(axis=0)
    worst = np.argsort(drift)[-6:][::-1]
    print("najwieksza zmiana dlugosci kosci wzgledem pozy DSR [m]:",
          ", ".join(f"{dnames[i]} {drift[i]:.3f}" for i in worst))
    for nm in ("L Foot", "R Foot", "Pelvis", "R Hand", "R_weapon", "Head"):
        i, x = dnames.index(nm), enames.index(bmap[nm])
        err = np.linalg.norm(P[:, i] - S * eP[:, x], axis=1)
        print(f"   {nm:9s}: odleglosc od pozycji ER*S srednio {err.mean():.3f} m, max {err.max():.3f} m; "
              f"wysokosc min {P[:, i, 1].min():.2f} (ER*S {S * eP[:, x, 1].min():.2f})")
    for label, f_new, f_old in (("pierwsza klatka", 0, 0), ("ostatnia klatka", F - 1, dtT.shape[0] - 1)):
        ang = [np.degrees((Rm[i][f_new].inv() * dtRot[i][f_old]).magnitude()) for i in d2e if i]
        print(f"   {label}: roznica obrotow wzgledem oryginalu DSR a{args.dsr_template}: srednio {np.mean(ang):.1f} st., "
              f"max {np.max(ang):.1f} st. ({dnames[list(k for k in d2e if k)[int(np.argmax(ang))]]})")

    erm = ec.get_reference_frame_samples().astype(np.float64).copy()
    erm[:, :3] *= S
    has_drm = bool(dc.hkx_animation.extractedMotion)
    drm_txt = str(np.round(dc.get_reference_frame_samples()[-1], 3)) if has_drm else "brak (animacja w miejscu)"
    er_range = float(np.abs(erm).max())
    print(f"root motion: ER*S koniec {np.round(erm[-1], 3)} ({erm.shape[0]} probek, zakres {er_range:.3f}); DSR oryginal: {drm_txt}")
    if not has_drm and er_range < 1e-3:  # wzor DSR nie ma root motion, ER ma same zera -> zapis bez root motion
        erm = None

    if not out:
        print("(bez --out: nic nie zapisano)")
        return 0

    frames = [[TRSTransform(Vector3(T[f, b]), Quaternion(Q[f, b]), Vector3.one()) for b in range(B)] for f in range(F)]
    anim = d.AnimationHKX.from_minimal_data_interleaved(
        frames, list(range(B)), root_motion_array=None if erm is None else erm.astype(np.float32),
        original_skeleton_name=dc.hkx_binding.originalSkeletonName, track_names=dnames)
    if not args.interleaved:
        anim = anim.to_spline_hkx()
    out.parent.mkdir(parents=True, exist_ok=True)
    anim.write(out)

    # --- odczyt kontrolny zapisanego pliku
    chk = d.AnimationHKX.from_path(out)
    cc = chk.animation_container
    ci = cc.to_interleaved_container() if cc.is_spline else cc
    cT, cQ = frames_to_arrays(ci.interleaved_data, list(cc.hkx_binding.transformTrackToBoneIndices), B, dref)
    cP, cRot = to_model_space(dpar, cT, cQ)
    perr = np.linalg.norm(cP - P, axis=2)
    rerr = np.array([np.degrees((cRot[b].inv() * Rm[b]).magnitude()) for b in range(B)])
    a, ta = cc.hkx_animation, dc.hkx_animation
    print(f"zapisano {out} ({out.stat().st_size} B, oryginal DSR {(DD / f'a00_{args.dsr_template:04d}.hkx').stat().st_size} B)")
    print(f"   typ {type(a).__name__}, klatek {cc.frame_count}, czas {float(a.duration):.3f} s, sciezek {cc.track_count}; "
          f"blad po kompresji: pozycja max {perr.max() * 1000:.1f} mm, obrot max {rerr.max():.2f} st.")
    for fld in ("type", "numberOfFloatTracks", "maxFramesPerBlock", "maskAndQuantizationSize", "blockDuration",
                "blockInverseDuration", "frameDuration", "endian", "numBlocks"):
        if hasattr(a, fld):
            print(f"   {fld}: nowy {getattr(a, fld)!r} | oryginal {getattr(ta, fld)!r}")
    print(f"   binding: nowy ({cc.hkx_binding.originalSkeletonName!r}, blendHint {cc.hkx_binding.blendHint}, "
          f"sciezek {len(cc.hkx_binding.transformTrackToBoneIndices)}) | oryginal ({dc.hkx_binding.originalSkeletonName!r}, "
          f"blendHint {dc.hkx_binding.blendHint}, sciezek {len(dc.hkx_binding.transformTrackToBoneIndices)})")
    def em(x):
        return "brak" if not x.extractedMotion else f"{type(x.extractedMotion).__name__} {x.extractedMotion.referenceFrameSamples.shape}"
    print(f"   extractedMotion: nowy {em(a)} | oryginal {em(ta)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
