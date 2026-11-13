"""Dump the events of chosen animations from a DSR anibnd TAE (type, JumpTable id, times, raw params).

  python tools/tae_dump_anim.py work/c0000.anibnd.before_attacks.dcx a38 3500 4500
  python tools/tae_dump_anim.py --bnd4 nuxe_nr/chr/c7720.anibnd.dcx c7720 3000
"""
from __future__ import annotations

import ntpath
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from sfbridge import load_soulsformats, read_binder, read_file  # noqa: E402


def main(argv: list[str]) -> int:
    bnd4 = "--bnd4" in argv
    argv = [a for a in argv if a != "--bnd4"]
    path, group, ids = Path(argv[0]).resolve(), argv[1].lower(), {int(x) for x in argv[2:]}
    sf = load_soulsformats()
    files = {ntpath.basename(str(f.Name)).lower(): f for f in read_binder(sf.BND4 if bnd4 else sf.BND3, str(path)).Files}
    tae = read_file(sf.TAE, files[f"{group}.tae"].Bytes)
    for a in tae.Animations:
        if ids and int(a.ID) not in ids:
            continue
        print(f"== {group} {int(a.ID)}: {a.Events.Count} events")
        for e in sorted(a.Events, key=lambda x: (x.StartTime, x.Type)):
            p = bytes(e.GetParameterBytes(False))
            jt = f" JT{struct.unpack_from('<i', p)[0]}" if int(e.Type) == 0 and len(p) >= 4 else ""
            ints = struct.unpack_from(f"<{min(4, len(p) // 4)}i", p) if len(p) >= 4 else ()
            print(f"   {e.StartTime:6.3f}-{e.EndTime:6.3f}  type {int(e.Type):3d}{jt:6s} {ints}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
