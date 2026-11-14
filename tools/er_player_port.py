"""Port Elden Ring player clips onto the DSR player skeleton (bones matched by name), for the jump attacks.

The Player Animations Repository has no usable katana jump attacks for DSR: its a029 files are bound to 42 ER
bone indices (the model falls apart). This takes the clips straight from Elden Ring (nuxe\\chr) and runs them
through tools/nr_boss_port.py (same maths as the bosses: rotations from ER, DSR bone lengths, pelvis-height
scale, ER root motion). Output: work/jump_port/a0GG_0NNNNN.hkx, which tools/add_jump_attacks.py takes before
the repository files.

Note: ER's axe (a30) has no R1 jump attack of its own - its TAE plays the hammer's a033_031030 / 033030 - so
the hammer clips the jump attack generator picks for the DSR axe are what Elden Ring does.

  python tools/er_player_port.py --group 29
"""
from __future__ import annotations

import argparse
import json
import ntpath
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from sfbridge import load_soulsformats, read_binder  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
BP = ROOT / "work" / "boss_port"
ER_CHR = Path(r"C:\Users\nemos\workspace\nuxe\chr")
GAME_CHR = Path(r"F:\SteamLibrary\steamapps\common\DARK SOULS REMASTERED\chr")
OUT = ROOT / "work" / "jump_port"
# ER jump attack clip -> DSR animation number used as the port template (swing / landing, R1 / R2, 1H / 2H)
CLIPS = {31030: 3700, 31070: 3701, 31230: 3710, 31270: 3711, 33030: 4700, 33070: 4701, 33230: 4710, 33270: 4711}


def bytes_of(f) -> bytes:
    return bytes(f.Bytes.ToArray())


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--group", required=True, help="weapon group, e.g. 29 (katana)")
    ap.add_argument("--container", default="", help="ER binder with the clips (default: c0000_a<first digit>x)")
    args = ap.parse_args(argv)
    g = int(args.group)
    sf = load_soulsformats()
    ed = BP / "nr_c0000er" / "anibnd"
    dd = BP / "dsr_c0000p" / "anibnd"
    for p in (ed, dd):
        p.mkdir(parents=True, exist_ok=True)

    # ER: skeleton (c0000.anibnd) + the clips and their compendium
    for f in read_binder(sf.BND4, str(ER_CHR / "c0000.anibnd.dcx")).Files:
        if ntpath.basename(str(f.Name)).lower() == "skeleton.hkx":
            (ed / "skeleton.hkx").write_bytes(bytes_of(f))
    cont = args.container or f"c0000_a{g // 10}x"
    want = {f"a{g:03d}_{cid:06d}.hkx" for cid in CLIPS}
    cmap = json.loads((ed / "compendium_map.json").read_text(encoding="utf-8")) if (ed / "compendium_map.json").exists() else {}
    files = list(read_binder(sf.BND4, str(ER_CHR / f"{cont}.anibnd.dcx")).Files)
    comp = next(f for f in files if str(f.Name).lower().endswith(".compendium"))
    cname = ntpath.basename(str(comp.Name))
    (ed / cname).write_bytes(bytes_of(comp))
    found = []
    for f in files:
        base = ntpath.basename(str(f.Name)).lower()
        if base in want:
            (ed / base).write_bytes(bytes_of(f))
            cmap[base] = cname
            found.append(base)
    (ed / "compendium_map.json").write_text(json.dumps(cmap, indent=0), encoding="utf-8")
    print(f"ER {cont}: {len(found)} of {len(want)} clips ({', '.join(sorted(found))})")

    # DSR: player skeleton + one template per new animation number (the group's own R1, a{g}_3000)
    for f in read_binder(sf.BND3, str(GAME_CHR / "c0000.anibnd.dcx")).Files:
        if ntpath.basename(str(f.Name)).lower() == "skeleton.hkx":
            (dd / "skeleton.hkx").write_bytes(bytes_of(f))
    tpl = next(f for f in read_binder(sf.BND3, str(GAME_CHR / f"c0000_a{g // 10}x.anibnd.dcx")).Files
               if ntpath.basename(str(f.Name)).lower() == f"a{g}_3000.hkx")
    for new in CLIPS.values():
        (dd / f"a00_{new:04d}.hkx").write_bytes(bytes_of(tpl))

    import nr_boss_port
    pairs = []
    for cid, new in CLIPS.items():
        if f"a{g:03d}_{cid:06d}.hkx" in found:
            pairs += ["--pair", f"{g * 1000000 + cid}:{new}"]
    tag = f"_a{g}"
    rc = nr_boss_port.main(["--nr", "c0000er", "--dsr", "c0000p", "--tag", tag] + pairs)
    OUT.mkdir(parents=True, exist_ok=True)
    for cid, new in CLIPS.items():
        src = BP / "nr_ported" / f"c0000p{tag}" / f"a00_{new:04d}.hkx"
        if src.exists():
            shutil.copyfile(src, OUT / f"a0{g}_{cid:06d}.hkx")
            print(f"  -> {OUT / f'a0{g}_{cid:06d}.hkx'}")
    return rc


if __name__ == "__main__":
    sys.exit(main())
