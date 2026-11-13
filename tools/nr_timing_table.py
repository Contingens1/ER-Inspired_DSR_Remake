"""Attack timing table of a boss: DSR vs its Nightreign version (markdown).

Columns per game: first hit start, last hit end, combo window (JT23), next attack (JT86), movement (JT78).
Both games use the same JumpTable IDs for enemies.

  python tools/nr_timing_table.py c4100 c7720 > analysis/nr_timing_c4100.md
"""
from __future__ import annotations

import ntpath
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from sfbridge import load_soulsformats, read_binder, read_file  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
DSR_CHR = Path(r"F:\SteamLibrary\steamapps\common\DARK SOULS REMASTERED\chr")


def row(anim):
    if anim is None:
        return None
    hits, jt = [], {}
    for e in anim.Events:
        p = bytes(e.GetParameterBytes(False))
        s, t = float(e.StartTime), float(e.EndTime)
        if int(e.Type) == 1 and s > 0.01:
            hits.append((s, t))
        elif int(e.Type) == 2 and s > 0.01:
            hits.append((s, t))
        elif int(e.Type) == 0 and len(p) >= 4:
            j = struct.unpack_from("<i", p)[0]
            if j in (23, 78, 86):
                jt[j] = min(jt.get(j, 1e9), s)
    return {"h0": min(h[0] for h in hits) if hits else None, "h1": max(h[1] for h in hits) if hits else None,
            "n": len(hits), 23: jt.get(23), 86: jt.get(86), 78: jt.get(78)}


def f(v):
    return "–" if v is None else f"{v:.2f}"


def main(dsr: str, nr: str) -> int:
    sf = load_soulsformats()
    dfiles = {ntpath.basename(str(x.Name)).lower(): x for x in read_binder(sf.BND3, str(DSR_CHR / f"{dsr}.anibnd.dcx")).Files}
    dt = {int(a.ID): a for a in read_file(sf.TAE, dfiles[f"{dsr}.tae"].Bytes).Animations}
    nt = {int(a.ID): a for a in read_file(sf.TAE, str(ROOT / "work" / "boss_port" / f"nr_{nr}" / "anibnd" / f"{nr}.tae")).Animations}
    ids = sorted({i for i in dt if 3000 <= i <= 3099} | {i % 1000000 for i in nt if 3000 <= i % 1000000 <= 3099})
    print(f"| atak | DSR trafienie | DSR combo / atak / ruch | NR trafienie | NR combo / atak / ruch | NR a001 trafienie | NR a001 combo / atak / ruch |")
    print("|---|---|---|---|---|---|---|")
    for i in ids:
        cells = []
        for r in (row(dt.get(i)), row(nt.get(i)), row(nt.get(1000000 + i))):
            if r is None:
                cells += ["brak", "brak"]
            else:
                cells += [f"{f(r['h0'])}–{f(r['h1'])} ({r['n']})", f"{f(r[23])} / {f(r[86])} / {f(r[78])}"]
        print(f"| {i} | " + " | ".join(cells) + " |")
    return 0


if __name__ == "__main__":
    sys.exit(main(*sys.argv[1:3]))
