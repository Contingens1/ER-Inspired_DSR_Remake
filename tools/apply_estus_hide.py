"""Estus without the weapon in the hand: install the drink clips ported by tools/er_player_port.py --hide-weapon.

Takes the main mod's chr/c0000_a00_md.anibnd.dcx (its 7585-7589 are ER 050110-050114 from the Player Animations
Repository, weapon visible), replaces those five entries with work/estus_port/a00_758N.hkx (same ER motion,
R_Weapon scaled to 0 in the ER TAE 710 HideEquippedWeapon windows, as DS1's own item animations do) and writes the
binder to a test package folder. Nothing in the main mod or the game directory is changed.

  python tools/er_player_port.py --group 0 --clips 50110:7585 50111:7586 50112:7587 50113:7588 50114:7589 \\
         --hide-weapon --out work/estus_port --dsr-names
  python tools/apply_estus_hide.py [--out dist/mods/bossy_nightreign/files_c0000_estus/chr]
"""
from __future__ import annotations

import argparse
import ntpath
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from sfbridge import load_soulsformats, read_binder, to_memory  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "dist" / "mods" / "c0000_er_engine" / "files" / "chr" / "c0000_a00_md.anibnd.dcx"
CLIPS = ROOT / "work" / "estus_port"
IDS = (7585, 7586, 7587, 7588, 7589)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=ROOT / "dist" / "mods" / "bossy_nightreign" / "files_c0000_estus" / "chr")
    args = ap.parse_args(argv)
    out_dir = args.out.resolve()
    sf = load_soulsformats()
    from System import Array, Byte
    b = read_binder(sf.BND3, str(SRC))
    done = 0
    for f in b.Files:
        base = ntpath.basename(str(f.Name)).lower()
        for aid in IDS:
            if base == f"a00_{aid}.hkx":
                data = (CLIPS / f"a00_{aid}.hkx").read_bytes()
                f.Bytes = to_memory(Array[Byte](list(data)))
                print(f"  {base}: {len(data)} B from {CLIPS / f'a00_{aid}.hkx'}")
                done += 1
    if done != len(IDS):
        raise RuntimeError(f"replaced {done} of {len(IDS)} entries")
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / SRC.name
    tmp = out.with_suffix(".tmp")
    b.Write(str(tmp))
    b.Dispose()
    tmp.replace(out)
    print(f"written {out} ({out.stat().st_size} B)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
