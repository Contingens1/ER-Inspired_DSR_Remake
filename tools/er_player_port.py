"""Port Elden Ring player clips onto the DSR player skeleton (bones matched by name).

Runs the clips through tools/nr_boss_port.py (same maths as the bosses: rotations from ER, DSR bone lengths,
pelvis-height scale, ER root motion), taken straight from Elden Ring (nuxe\\chr).

Jump attacks (default clips): the Player Animations Repository has no usable katana jump attacks for DSR (its a029
files are bound to 42 ER bone indices, the model falls apart). Output work/jump_port/a0GG_0NNNNN.hkx, which
tools/add_jump_attacks.py takes before the repository files.
  python tools/er_player_port.py --group 29

Estus (2026-11-14): the mod's drink animations 7585-7589 are ER 050110-050114 from the repository. ER hides the
weapon with TAE 710 HideEquippedWeapon, which DS1 does not have (DS1 scales the R_Weapon bone to 0 in the clip),
so the weapon stayed in the hand. --hide-weapon reads the 710 windows from the ER TAE and scales R_Weapon to 0
there. Output work/estus_port/a00_NNNN.hkx (DSR names), installed by tools/apply_estus_hide.py.
  python tools/er_player_port.py --group 0 --clips 50110:7585 50111:7586 50112:7587 50113:7588 50114:7589
         --hide-weapon --out work/estus_port --dsr-names

Note: ER's axe (a30) has no R1 jump attack of its own - its TAE plays the hammer's a033_031030 / 033030 - so
the hammer clips the jump attack generator picks for the DSR axe are what Elden Ring does.
"""
from __future__ import annotations

import argparse
import json
import ntpath
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from sfbridge import load_soulsformats, read_binder, read_file  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
BP = ROOT / "work" / "boss_port"
ER_CHR = Path(r"C:\Users\nemos\workspace\nuxe\chr")
GAME_CHR = Path(r"F:\SteamLibrary\steamapps\common\DARK SOULS REMASTERED\chr")
# ER jump attack clip -> DSR animation number used as the port template (swing / landing, R1 / R2, 1H / 2H)
JUMP_CLIPS = {31030: 3700, 31070: 3701, 31230: 3710, 31270: 3711, 33030: 4700, 33070: 4701, 33230: 4710, 33270: 4711}
HIDE_WEAPON = 710  # ER TAE HideEquippedWeapon


def bytes_of(f) -> bytes:
    return bytes(f.Bytes.ToArray())


def containers(g: int, er: bool) -> list[str]:
    if g == 0:
        return ["c0000_a00_lo", "c0000_a00_md", "c0000_a00_hi"]
    return [f"c0000_a{g // 10}x"]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--group", required=True, type=int, help="animation group: 29 = katana, 0 = base (a00 / a000)")
    ap.add_argument("--clips", nargs="*", default=[], metavar="ER:DSR", help="default: the jump attack clips")
    ap.add_argument("--hide-weapon", action="store_true", help="R_Weapon scale 0 in the ER TAE 710 windows")
    ap.add_argument("--out", type=Path, default=ROOT / "work" / "jump_port")
    ap.add_argument("--dsr-names", action="store_true", help="name outputs aGG_NNNN.hkx (DSR) instead of a0GG_0NNNNN.hkx")
    args = ap.parse_args(argv)
    g = args.group
    args.out = args.out.resolve()  # load_soulsformats() changes the working directory
    clips = {int(s.split(":")[0]): int(s.split(":")[1]) for s in args.clips} if args.clips else dict(JUMP_CLIPS)
    sf = load_soulsformats()
    ed = BP / "nr_c0000er" / "anibnd"
    dd = BP / "dsr_c0000p" / "anibnd"
    for p in (ed, dd):
        p.mkdir(parents=True, exist_ok=True)

    # ER: skeleton + TAE (c0000.anibnd), the clips and their compendium
    er_tae = None
    for f in read_binder(sf.BND4, str(ER_CHR / "c0000.anibnd.dcx")).Files:
        base = ntpath.basename(str(f.Name)).lower()
        if base == "skeleton.hkx":
            (ed / "skeleton.hkx").write_bytes(bytes_of(f))
        if base == f"a{g:02d}.tae":
            er_tae = read_file(sf.TAE, f.Bytes)
    want = {f"a{g:03d}_{cid:06d}.hkx" for cid in clips}
    cmap = json.loads((ed / "compendium_map.json").read_text(encoding="utf-8")) if (ed / "compendium_map.json").exists() else {}
    found = []
    for cont in containers(g, True):
        files = list(read_binder(sf.BND4, str(ER_CHR / f"{cont}.anibnd.dcx")).Files)
        comp = next((f for f in files if str(f.Name).lower().endswith(".compendium")), None)
        cname = ntpath.basename(str(comp.Name)) if comp is not None else ""
        if comp is not None:
            (ed / cname).write_bytes(bytes_of(comp))
        for f in files:
            base = ntpath.basename(str(f.Name)).lower()
            if base in want and base not in found:
                (ed / base).write_bytes(bytes_of(f))
                cmap[base] = cname
                found.append(base)
    (ed / "compendium_map.json").write_text(json.dumps(cmap, indent=0), encoding="utf-8")
    print(f"ER: {len(found)} of {len(want)} clips ({', '.join(sorted(found))})")

    # DSR: player skeleton + one template per new animation number (the same DSR animation if it exists,
    # otherwise the group's own R1)
    for f in read_binder(sf.BND3, str(GAME_CHR / "c0000.anibnd.dcx")).Files:
        if ntpath.basename(str(f.Name)).lower() == "skeleton.hkx":
            (dd / "skeleton.hkx").write_bytes(bytes_of(f))
    dsr_files = {}
    for cont in containers(g, False):
        for f in read_binder(sf.BND3, str(GAME_CHR / f"{cont}.anibnd.dcx")).Files:
            dsr_files[ntpath.basename(str(f.Name)).lower()] = f
    for new in clips.values():
        tpl = dsr_files.get(f"a{g:02d}_{new:04d}.hkx") or dsr_files[f"a{g:02d}_3000.hkx"]
        (dd / f"a00_{new:04d}.hkx").write_bytes(bytes_of(tpl))

    import nr_boss_port
    extra = []
    for cid, new in clips.items():
        if f"a{g:03d}_{cid:06d}.hkx" not in found:
            continue
        nid = g * 1000000 + cid
        extra += ["--pair", f"{nid}:{new}"]
        if args.hide_weapon and er_tae is not None:
            a = next((x for x in er_tae.Animations if int(x.ID) == cid), None)
            for e in (a.Events if a is not None else []):
                if int(e.Type) == HIDE_WEAPON:
                    t1 = min(float(e.EndTime), 1000.0)
                    extra += ["--scale-zero", f"{nid}:R_Weapon:{float(e.StartTime):.3f}:{t1:.3f}"]
                    print(f"  {cid} -> {new}: R_Weapon hidden {float(e.StartTime):.2f}-{min(t1, 99):.2f} s (ER TAE 710)")
    tag = f"_a{g}"
    rc = nr_boss_port.main(["--nr", "c0000er", "--dsr", "c0000p", "--tag", tag] + extra)
    args.out.mkdir(parents=True, exist_ok=True)
    for cid, new in clips.items():
        src = BP / "nr_ported" / f"c0000p{tag}" / f"a00_{new:04d}.hkx"
        if src.exists():
            name = f"a{g:02d}_{new:04d}.hkx" if args.dsr_names else f"a0{g:02d}_{cid:06d}.hkx"
            shutil.copyfile(src, args.out / name)
            print(f"  -> {args.out / name}")
    return rc


if __name__ == "__main__":
    sys.exit(main())
