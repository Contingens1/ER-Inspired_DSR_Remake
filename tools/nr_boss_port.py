"""Batch port of Nightreign boss animations onto the DSR skeleton of the same boss (name-matched bones).

Generalisation of tools/boss_anim_port.py (ER c4810 -> DSR c2232): same maths, but the bone map is built from
identical bone names (NR remasters keep the DS1 names), the scale comes from the rest-pose pelvis height and the
Master convention (Master carries the pelvis motion or not) is detected from a DSR template animation.

  python tools/nr_boss_port.py --nr c7720 --dsr c4100                 # port every ID present in both games
  python tools/nr_boss_port.py --nr c7720 --dsr c4100 --anims 3000 3001 --install

Input:  work/boss_port/nr_<nr>/anibnd (tools/nr_inventory.py --unpack), work/boss_port/dsr_<dsr>/anibnd
        (tools/boss_anim_inventory.py dsr).
Output: work/boss_port/nr_ported/<dsr>/a00_XXXX.hkx, analysis/nr_port_<dsr>.txt and, with --install,
        dist/mods/bossy_nightreign/files_<dsr>/chr/<dsr>.anibnd.dcx (TAE events of each replaced animation
        moved with anchors taken from the hit windows of both games). Nothing is written to a game directory.
"""
from __future__ import annotations

import argparse
import ntpath
import re
import struct
import sys
from pathlib import Path

import numpy as np
from scipy.spatial.transform import Rotation as R

sys.path.insert(0, str(Path(__file__).resolve().parent))
from boss_anim_port import frames_to_arrays, parents_of, ref_arrays, to_model_space  # noqa: E402
from havokbridge import load_havok  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
BP = ROOT / "work" / "boss_port"
DSR_CHR = Path(r"F:\SteamLibrary\steamapps\common\DARK SOULS REMASTERED\chr")
LOG: list[str] = []


def say(s: str = "") -> None:
    print(s, flush=True)
    LOG.append(s)


def norm(n: str) -> str:
    return re.sub(r"[^a-z0-9]", "", n.lower())


def find_ci(folder: Path, name: str) -> Path:
    return next(p for p in folder.iterdir() if p.name.lower() == name.lower())


def load_anim(cls, path, comp=None):
    a = cls.from_path(path, compendium=comp) if comp is not None else cls.from_path(path)
    c = a.animation_container
    return c, (c.to_interleaved_container() if c.is_spline else c)


def port_one(ctx, nr_id: int, dsr_id: int, out: Path) -> dict:
    d, e, TRS, V3, Qt = ctx["d"], ctx["e"], ctx["TRS"], ctx["V3"], ctx["Qt"]
    dnames, dpar, epar, d2e, e2d, S = ctx["dnames"], ctx["dpar"], ctx["epar"], ctx["d2e"], ctx["e2d"], ctx["S"]
    dref, dPr, dRr, eref, ePr, eRr = ctx["dref"], ctx["dPr"], ctx["dRr"], ctx["eref"], ctx["ePr"], ctx["eRr"]
    ename = f"a{nr_id // 1000000:03d}_{nr_id % 1000000:06d}.hkx"  # 1003028 = a001_003028 (variant set)
    ec, eint = load_anim(e.AnimationHKX, ctx["ED"] / ename, ctx["comp_for"](ename))
    dc, dint = load_anim(d.AnimationHKX, find_ci(ctx["DD"], f"a00_{dsr_id:04d}.hkx"))
    eT, eQ = frames_to_arrays(eint.interleaved_data, list(ec.hkx_binding.transformTrackToBoneIndices),
                              len(epar), eref)
    F = eT.shape[0]
    eP, eRot = to_model_space(epar, eT, eQ)
    B = len(dnames)
    P, T, Q = np.zeros((F, B, 3)), np.zeros((F, B, 3)), np.zeros((F, B, 4))
    Rm: list = [None] * B
    pel = ctx["pelvis"]
    for b in range(B):
        p = dpar[b]
        if p < 0:
            if ctx["master_carries"] and pel in d2e:
                x = d2e[pel]
                T[:, b] = dPr[0, pel] + S * (eP[:, x] - ePr[0, x])
                Rm[b] = eRot[x] * (eRr[x].inv() * dRr[pel]) * (dRr[pel].inv() * dRr[b])
            elif b in d2e:
                x = d2e[b]
                T[:, b] = dPr[0, b] + S * (eP[:, x] - ePr[0, x])
                Rm[b] = eRot[x] * (eRr[x].inv() * dRr[b])
            else:
                T[:, b] = dref[0][b]
                Rm[b] = R.from_quat(np.repeat(dref[1][b][None], F, axis=0))
            Q[:, b], P[:, b] = Rm[b].as_quat(), T[:, b]
            continue
        if b in d2e and not (ctx["master_carries"] and b == pel):
            x = d2e[b]
            Rm[b] = eRot[x] * (eRr[x].inv() * dRr[b])
            a = epar[x]
            while a >= 0 and (a not in e2d or epar[a] < 0):  # the root is never a logical parent
                a = epar[a]
            if a < 0:
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
    for b in range(B):
        flip = np.cumsum(np.einsum("ij,ij->i", Q[1:, b], Q[:-1, b]) < 0) % 2 == 1
        # sign continuity must follow the already-flipped previous frame
        sign = np.ones(F)
        for f in range(1, F):
            if np.dot(Q[f, b] * 1.0, Q[f - 1, b] * sign[f - 1]) < 0:
                sign[f] = -1.0
        Q[:, b] *= sign[:, None]
        del flip

    erm = ec.get_reference_frame_samples().astype(np.float64).copy() if ec.hkx_animation.extractedMotion else None
    if erm is not None:
        erm[:, :3] *= S
    has_drm = bool(dc.hkx_animation.extractedMotion)
    drm_end = dc.get_reference_frame_samples()[-1] if has_drm else np.zeros(4)
    if erm is not None and not has_drm and float(np.abs(erm).max()) < 1e-3:
        erm = None
    frames = [[TRS(V3(T[f, b]), Qt(Q[f, b]), V3.one()) for b in range(B)] for f in range(F)]
    anim = d.AnimationHKX.from_minimal_data_interleaved(
        frames, list(range(B)), root_motion_array=None if erm is None else erm.astype(np.float32),
        original_skeleton_name=dc.hkx_binding.originalSkeletonName, track_names=dnames).to_spline_hkx()
    out.parent.mkdir(parents=True, exist_ok=True)
    anim.write(out)
    drift = np.abs(np.linalg.norm(T[:, 1:], axis=2) - np.linalg.norm(dref[0][1:], axis=1)[None]).max()
    # Similarity to the DSR original (model-space joint positions, time-normalised): tells a re-exported
    # DS1 animation (a few cm) from a new one.
    oT, oQ = frames_to_arrays(dint.interleaved_data, list(dc.hkx_binding.transformTrackToBoneIndices), B, dref)
    oP, _ = to_model_space(dpar, oT, oQ)
    idx = np.clip(np.round(np.linspace(0, oP.shape[0] - 1, F)).astype(int), 0, oP.shape[0] - 1)
    diff = float(np.linalg.norm(P - oP[idx], axis=2).mean())
    return {"diff": diff,"nr_dur": (F - 1) / 30.0, "dsr_dur": float(dc.hkx_animation.duration),
            "nr_rm": None if erm is None else erm[-1], "dsr_rm": drm_end if has_drm else None,
            "size": out.stat().st_size, "drift": float(drift)}


def hit_windows(tae, anim_id: int, atk_types: set[int], bullet_types: set[int] = frozenset()):
    a = next((x for x in tae.Animations if int(x.ID) == anim_id), None)
    if a is None:  # Nightreign keeps the events of some attacks under the a001 variant
        a = next((x for x in tae.Animations if int(x.ID) == 1000000 + anim_id), None)
    if a is None:
        return None, 0.0
    ev = list(a.Events)
    dur = max([float(x.EndTime) for x in ev if float(x.EndTime) < 1000.0] or [0.0])
    # events starting at 0.0 are whole-animation body behaviours in NR (InvokeAttackBehavior (0, 7)), not swings
    hits = sorted((float(x.StartTime), float(x.EndTime)) for x in ev
                  if int(x.Type) in atk_types and float(x.StartTime) > 0.01)
    if not hits:
        hits = sorted((float(x.StartTime), float(x.EndTime)) for x in ev
                      if int(x.Type) in bullet_types and float(x.StartTime) > 0.01)
    merged: list[list[float]] = []
    for s, t in hits:  # overlapping or back-to-back hitboxes of one swing count as one window
        if merged and s <= merged[-1][1] + 0.02:
            merged[-1][1] = max(merged[-1][1], t)
        else:
            merged.append([s, t])
    return merged, dur


def install(args, results: dict) -> None:
    from boss_anim_install import warp
    from sfbridge import load_soulsformats, net_bytes, read_binder, read_file, to_memory
    from tae_compare import DSAS, template
    sf = load_soulsformats()
    t1, te = template(DSAS / "TAE.Template.DS1.xml"), template(DSAS / "TAE.Template.ER.xml")
    atk1 = {i for i, (n, _) in t1.items() if n == "InvokeAttackBehavior"}
    atke = {i for i, (n, _) in te.items() if n == "InvokeAttackBehavior"}
    bul1 = {i for i, (n, _) in t1.items() if n == "InvokeBulletBehavior"}
    bule = {i for i, (n, _) in te.items() if n == "InvokeBulletBehavior"}
    bnd = read_binder(sf.BND3, str(DSR_CHR / f"{args.dsr}.anibnd.dcx"))
    files = {ntpath.basename(str(f.Name)).lower(): f for f in bnd.Files}
    tentry = files[f"{args.dsr}.tae"]
    tae = read_file(sf.TAE, tentry.Bytes)
    ntae = read_file(sf.TAE, str(find_ci(BP / f"nr_{args.nr}" / "anibnd", f"{args.nr}.tae")))
    say()
    say("TAE retime (anchors old:new from hit windows; 'scale' = only the length ratio was available)")
    for (nr_id, dsr_id), res in sorted(results.items(), key=lambda kv: kv[0][1]):
        files[f"a00_{dsr_id:04d}.hkx"].Bytes = to_memory(net_bytes(res["path"].read_bytes()))
        dh, _ = hit_windows(tae, dsr_id, atk1, bul1)
        nh, ndur = hit_windows(ntae, nr_id, atke, bule)
        anchors = [(0.0, 0.0)]
        mode = "scale"
        if dh and nh and len(dh) == len(nh):
            mode = f"{len(dh)} hit(s)"
            for (ds, dt), (ns, nt) in zip(dh, nh):
                anchors += [(ds, ns), (dt, nt)]
        elif dh and nh:  # different number of windows: each window of the shorter list takes the nearest
            # unused one of the longer list (by start time, order kept); the rest have no partner
            short, long_, swap = (dh, nh, False) if len(dh) < len(nh) else (nh, dh, True)
            j0, n_pairs = 0, 0
            for w in short:
                if j0 >= len(long_):
                    break
                j = min(range(j0, len(long_)), key=lambda k: abs(long_[k][0] - w[0]))
                dwin, nwin = (long_[j], w) if swap else (w, long_[j])
                anchors += [(dwin[0], nwin[0]), (dwin[1], nwin[1])]
                j0, n_pairs = j + 1, n_pairs + 1
            mode = f"nearest {n_pairs} of {len(dh)} vs {len(nh)} hits"
        # NR clips can run far past the last event (a001 Artorias: 9.3 s clip, events end at 4.4 s)
        new_end = min(res["nr_dur"], ndur) if ndur > anchors[-1][1] + 0.3 else res["nr_dur"]
        anchors.append((max(res["dsr_dur"], anchors[-1][0] + 0.01), max(new_end, anchors[-1][1] + 0.01)))
        anchors = sorted(set(anchors))
        mono = all(b1 > b0 and a1 > a0 for (a0, b0), (a1, b1) in zip(anchors, anchors[1:]))
        if not mono:
            anchors, mode = [(0.0, 0.0), (res["dsr_dur"], res["nr_dur"])], "scale (hit order mismatch)"
        anim = next((a for a in tae.Animations if int(a.ID) == dsr_id), None)
        n_ev = 0
        if anim is not None:
            for ev in anim.Events:
                s1 = round(warp(float(ev.StartTime), anchors) * 30) / 30.0
                e1 = max(round(warp(float(ev.EndTime), anchors) * 30) / 30.0, s1 + 1 / 30.0)
                ev.StartTime, ev.EndTime = s1, e1
                n_ev += 1
        say(f"  {dsr_id}: {mode:28s} DSR hits {['%.2f-%.2f' % tuple(h) for h in dh or []]} -> "
            f"NR {['%.2f-%.2f' % tuple(h) for h in nh or []]}; {n_ev} events moved")
    tentry.Bytes = to_memory(tae.Write())
    dst = (ROOT / "dist" / "mods" / "bossy_nightreign" / f"files_{args.dsr}{args.tag}" / "chr"
           / f"{args.dsr}.anibnd.dcx")
    dst.parent.mkdir(parents=True, exist_ok=True)
    bnd.Write(str(dst))
    chk = read_binder(sf.BND3, str(dst))
    say(f"installed -> {dst} ({dst.stat().st_size} B, {chk.Files.Count} entries, "
        f"original {(DSR_CHR / f'{args.dsr}.anibnd.dcx').stat().st_size} B)")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--nr", required=True)
    ap.add_argument("--dsr", required=True)
    ap.add_argument("--anims", type=int, nargs="*", help="IDs (same in both games); default: all shared")
    ap.add_argument("--pair", action="append", default=[], metavar="NR:DSR", help="explicit ID pair")
    ap.add_argument("--lo", type=int, default=3000)
    ap.add_argument("--hi", type=int, default=3999)
    ap.add_argument("--install", action="store_true")
    ap.add_argument("--reuse", action="store_true", help="keep already ported HKX, redo only the install")
    ap.add_argument("--tag", default="", help="suffix of the files_<dsr> folder and of the report (variants)")
    args = ap.parse_args(argv)

    load_havok()
    from soulstruct.havok.core import HKX
    from soulstruct.havok.fromsoft import darksouls1r as d, eldenring as e
    from soulstruct.havok.utilities.maths import Quaternion, TRSTransform, Vector3

    DD, ED = BP / f"dsr_{args.dsr}" / "anibnd", BP / f"nr_{args.nr}" / "anibnd"
    dsk = d.SkeletonHKX.from_path(find_ci(DD, "skeleton.hkx")).skeleton
    import json
    cmap = json.loads((ED / "compendium_map.json").read_text(encoding="utf-8"))
    comps: dict[str, object] = {}

    def comp_for(hkx_name: str):
        cname = cmap.get(hkx_name) or next(iter(sorted(set(v for v in cmap.values() if v))), "")
        if cname and cname not in comps:
            comps[cname] = HKX.from_path(ED / cname)
        return comps.get(cname)

    try:
        esk = e.SkeletonHKX.from_path(ED / "skeleton.hkx", compendium=comp_for("skeleton.hkx")).skeleton
    except Exception:
        esk = e.SkeletonHKX.from_path(ED / "skeleton.hkx").skeleton
    dnames, enames = [b.name for b in dsk.bones], [b.name for b in esk.bones]
    dpar, epar = parents_of(dsk), parents_of(esk)
    en = {norm(n): i for i, n in reversed(list(enumerate(enames)))}
    d2e = {i: (enames.index(n) if n in enames else en[norm(n)]) for i, n in enumerate(dnames)
           if n in enames or norm(n) in en}
    e2d = {}
    for k, v in d2e.items():
        e2d.setdefault(v, k)
    dref, eref = ref_arrays(dsk), ref_arrays(esk)
    dPr, dRr = to_model_space(dpar, dref[0][None], dref[1][None])
    ePr, eRr = to_model_space(epar, eref[0][None], eref[1][None])
    pelvis = next((i for i, n in enumerate(dnames) if norm(n) == "pelvis"), None)
    S = 1.0
    if pelvis is not None and pelvis in d2e and abs(ePr[0, d2e[pelvis], 1]) > 1e-3:
        S = float(dPr[0, pelvis, 1] / ePr[0, d2e[pelvis], 1])
    say(f"{args.nr} -> {args.dsr}: DSR bones {len(dnames)}, NR bones {len(enames)}, mapped {len(d2e)}; "
        f"scale {S:.3f} (pelvis height DSR {dPr[0, pelvis, 1]:.3f} / NR {ePr[0, d2e[pelvis], 1]:.3f})")
    say("unmapped DSR bones (stay in rest pose): " + ", ".join(n for i, n in enumerate(dnames) if i not in d2e)[:600])
    say("unmapped NR bones: " + ", ".join(n for i, n in enumerate(enames) if i not in e2d)[:600])

    d_ids = {int(m.group(1)) for p in DD.iterdir() if (m := re.match(r"a00_(\d{4})\.hkx$", p.name.lower()))}
    e_ids = {int(m.group(1)) for p in ED.iterdir() if (m := re.match(r"a000_(\d{6})\.hkx$", p.name.lower()))}
    pairs = [tuple(int(x) for x in s.split(":")) for s in args.pair]
    if not pairs:
        ids = args.anims if args.anims else sorted(i for i in d_ids & e_ids if args.lo <= i <= args.hi)
        pairs = [(i, i) for i in ids]
    say(f"DSR-only IDs in range: {sorted(i for i in d_ids - e_ids if args.lo <= i <= args.hi)}")
    say(f"NR-only IDs in range: {sorted(i for i in e_ids - d_ids if args.lo <= i <= args.hi)}")

    # Master convention from the first template: does the root track move while Pelvis stays put?
    tc, ti = load_anim(d.AnimationHKX, find_ci(DD, f"a00_{pairs[0][1]:04d}.hkx"))
    tT, _ = frames_to_arrays(ti.interleaved_data, list(tc.hkx_binding.transformTrackToBoneIndices), len(dnames), dref)
    root = dpar.index(-1)
    root_move = float(np.abs(tT[:, root] - tT[0, root]).max())
    pel_move = float(np.abs(tT[:, pelvis] - tT[0, pelvis]).max()) if pelvis is not None else 0.0
    master_carries = pelvis is not None and dpar[pelvis] == root and root_move > 0.02 and pel_move < 0.005
    say(f"root '{dnames[root]}' moves {root_move:.3f} m, Pelvis local moves {pel_move:.3f} m in a{pairs[0][1]} "
        f"-> master carries pelvis: {master_carries}")

    ctx = dict(d=d, e=e, TRS=TRSTransform, V3=Vector3, Qt=Quaternion, dnames=dnames, dpar=dpar, epar=epar,
               d2e=d2e, e2d=e2d, S=S, dref=dref, dPr=dPr, dRr=dRr, eref=eref, ePr=ePr, eRr=eRr, DD=DD, ED=ED,
               comp_for=comp_for, pelvis=pelvis, master_carries=master_carries)
    say()
    say(f"{'DSR':>5} {'NR':>6} {'DSR s':>6} {'NR s':>6}  {'root motion end DSR -> NR*S (x,y,z)':52s} {'B':>8} drift")
    results = {}
    for nr_id, dsr_id in pairs:
        out = BP / "nr_ported" / args.dsr / f"a00_{dsr_id:04d}.hkx"
        try:
            if args.reuse and out.exists():  # ported earlier: only the lengths are needed for the install
                ename = f"a{nr_id // 1000000:03d}_{nr_id % 1000000:06d}.hkx"
                ec, _ = load_anim(e.AnimationHKX, ED / ename, comp_for(ename))
                dc, _ = load_anim(d.AnimationHKX, find_ci(DD, f"a00_{dsr_id:04d}.hkx"))
                results[(nr_id, dsr_id)] = {"nr_dur": float(ec.hkx_animation.duration),
                                            "dsr_dur": float(dc.hkx_animation.duration), "path": out}
                say(f"{dsr_id:5d} {nr_id:6d} reused {out.name}")
                continue
            r = port_one(ctx, nr_id, dsr_id, out)
        except Exception as ex:
            say(f"{dsr_id:5d} {nr_id:6d} FAILED: {type(ex).__name__}: {str(ex)[:200]}")
            continue
        r["path"] = out
        results[(nr_id, dsr_id)] = r
        f3 = lambda v: "none" if v is None else "(" + ", ".join(f"{x:.2f}" for x in v[:3]) + ")"  # noqa: E731
        say(f"{dsr_id:5d} {nr_id:6d} {r['dsr_dur']:6.2f} {r['nr_dur']:6.2f}  "
            f"{(f3(r['dsr_rm']) + ' -> ' + f3(r['nr_rm'])):52s} {r['size']:8d} {r['drift']:.3f} "
            f"pose diff {r['diff'] * 100:.1f} cm")
    if args.install and results:
        install(args, results)
    (ROOT / "analysis").mkdir(exist_ok=True)
    (ROOT / "analysis" / f"nr_port_{args.dsr}{args.tag}.txt").write_text("\n".join(LOG), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
