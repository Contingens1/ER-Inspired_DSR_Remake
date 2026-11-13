"""Czasy atakow przeciwnika z TAE: dlugosc (koniec ostatniego zdarzenia), okna trafien (InvokeAttackBehavior
i pokrewne), z nazwami zdarzen z szablonow DSAnimStudio. Pliki TAE z tools/boss_anim_inventory.py.

  python tools/boss_attack_timing.py dsr work/boss_port/dsr_c2230/anibnd/c2230.tae [3000 3999]
  python tools/boss_attack_timing.py er  work/boss_port/er_c4810/anibnd/c4810.tae  [3000 3999]
"""
from __future__ import annotations

import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from sfbridge import load_soulsformats, read_file  # noqa: E402
from tae_compare import DSAS, template  # noqa: E402


def main(game: str, tae_path: str, lo: str = "3000", hi: str = "3999") -> None:
    tae_path = str(Path(tae_path).resolve())
    load_soulsformats()
    from SoulsFormats import TAE
    tpl = template(DSAS / ("TAE.Template.DS1.xml" if game == "dsr" else "TAE.Template.ER.xml"))
    tae = read_file(TAE, tae_path)
    for a in tae.Animations:
        aid = int(a.ID)
        if not (int(lo) <= aid % 1000000 <= int(hi)):
            continue
        evs = list(a.Events)
        if not evs:
            print(f"{aid}: (brak zdarzen - odwolanie do innej animacji?)")
            continue
        dur = max([float(e.EndTime) for e in evs if float(e.EndTime) < 1000.0] or [0.0])  # ER: koniec "do konca" = FLT_MAX
        hits, others = [], {}
        for e in evs:
            name = tpl.get(int(e.Type), (f"typ{int(e.Type)}", {}))[0]
            if name.startswith("Invoke"):
                p = bytes(e.GetParameterBytes(False))
                arg = struct.unpack_from("<ii", p + b"\0" * 8)
                hits.append((float(e.StartTime), float(e.EndTime), name, arg))
            else:
                others.setdefault(name, []).append((float(e.StartTime), float(e.EndTime)))
        hits.sort()
        print(f"{aid}: dlugosc {dur:.2f} s, trafien {len(hits)}")
        for s, t, n, arg in hits:
            print(f"      {s:5.2f}-{t:5.2f}  {n} {arg}")
        for n in ("JumpTable", "SetTurnSpeed", "RotateToTarget", "SuperArmor", "SetMovementMultiplier"):
            for k, v in others.items():
                if n.lower() in k.lower():
                    print(f"      {k}: " + ", ".join(f"{s:.2f}-{t:.2f}" for s, t in sorted(v)[:8]))


if __name__ == "__main__":
    main(*sys.argv[1:])
