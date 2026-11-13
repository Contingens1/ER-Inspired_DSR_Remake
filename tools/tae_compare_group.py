"""
tae_compare_group.py - jak tae_compare.py, ale w konkretnych grupach TAE (np. ataki broni).

Uzycie (CMD): python tools\\tae_compare_group.py <grupa DSR, np. a26> <grupa ER, np. a026> <dsr_id> <er_id> [...]
Pokazuje tylko zdarzenia istotne dla czasu: JumpTable (okna przerwan), trafienia (typ 1/2), niesmiertelnosc,
blokade obrotu; pomija dzwieki/efekty.
"""
from __future__ import annotations

import ntpath
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from sfbridge import load_soulsformats, read_binder, read_file  # noqa: E402
from tae_compare import DSAS, DSR_ANI, ER_ANI, events, template  # noqa: E402


def main() -> int:
    dg, eg, *ids = sys.argv[1:]
    ids = [int(x) for x in ids]
    load_soulsformats()
    from SoulsFormats import BND3, BND4, TAE
    t_ds1, t_er = template(DSAS / "TAE.Template.DS1.xml"), template(DSAS / "TAE.Template.ER.xml")
    dsr = next(f for f in read_binder(BND3, str(DSR_ANI)).Files if ntpath.basename(f.Name).lower() == f"{dg}.tae")
    er = next(f for f in read_binder(BND4, str(ER_ANI)).Files if ntpath.basename(f.Name).lower() == f"{eg}.tae")
    dsr_tae, er_tae = read_file(TAE, dsr.Bytes), read_file(TAE, er.Bytes)
    for d, e in zip(ids[::2], ids[1::2]):
        dr, er_ = events(dsr_tae, d, t_ds1), events(er_tae, e, t_er)
        print(f"===== DSR {dg}:{d} ({dr[1] if dr else 0:.2f} s)  vs  ER {eg}:{e} ({er_[1] if er_ else 0:.2f} s)")
        for label, r in (("DSR", dr), ("ER ", er_)):
            for s, en, n in (r[0] if r else []):
                if any(k in n for k in ("JT ", "Attack", "Invincib", "Turn")):
                    print(f"  {label} {s:5.2f}-{en:5.2f}  {n}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
