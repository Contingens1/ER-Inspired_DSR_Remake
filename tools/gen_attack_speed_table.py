"""
gen_attack_speed_table.py - tabela przyspieszania atakow DSR do czasow ER (dla er_engine.dll).

Animacja i TAE zostaja z DSR; DLL zmienia predkosc odtwarzania (ChrAnimData+0xA8) odcinkami tak,
zeby punkty kluczowe DSR wypadly w czasach ER:
    0 -> poczatek trafienia -> koniec trafienia -> okno kolejnego ataku (DSR JT4 <- ER JT115/JT4)
Po ostatnim punkcie predkosc wraca do 1.0. Pary z anim_map_attacks.json.

Uzycie (CMD): python tools\\gen_attack_speed_table.py   -> native/er_engine/attack_speed_table.h
"""
from __future__ import annotations

import json
import ntpath
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from sfbridge import load_soulsformats, read_binder, read_file  # noqa: E402
from tae_compare import DSAS, ER_ANI, template  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
MAP = ROOT / "tools" / "anim_map_attacks.json"
DSR_SRC = ROOT / "work" / "c0000.anibnd.before_attacks.dcx"  # TAE DSR bez zmian okien atakow
OUT = ROOT / "native" / "er_engine" / "attack_speed_table.h"
SPEED_MIN, SPEED_MAX = 1.0, 2.0  # bez zwalniania animacji DSR (wyglada zle) - tylko przyspieszenia
# Zamach i trafienie przyspieszone widac golym okiem (test: atak z przewrotu x2 wygladal niewiarygodnie)
SWING_MAX = 1.35
# Ciezkie bronie: przyspieszony powrot widac (test: Dragon Tooth R2 x1.95) - nizszy limit koncowki
HEAVY_GROUPS, HEAVY_RECOVERY_MAX = {32, 35}, 1.5


def type_id(tpl, name):
    return next(i for i, (n, _) in tpl.items() if n == name)


def jt_start(events, wanted):
    for w in wanted:
        s = [e.StartTime for e in events if int(e.Type) == 0
             and struct.unpack_from("<i", bytes(e.GetParameterBytes(False)))[0] == w]
        if s:
            return min(s)
    return None


def knots(events, atk, cancel_jts):
    hits = [e for e in events if int(e.Type) == atk]
    c = jt_start(events, cancel_jts)
    if not hits or c is None:
        return None
    return [0.0, min(e.StartTime for e in hits), max(e.EndTime for e in hits), c]


def main() -> int:
    cfg = json.loads(MAP.read_text(encoding="utf-8-sig"))
    mapping = {k: v for k, v in cfg.items() if not k.startswith("_")}
    for g in cfg.get("_grupy", []):
        mapping.setdefault(g, cfg["_wspolne_pary"])
    load_soulsformats()
    from SoulsFormats import BND3, BND4, TAE
    t1, te = template(DSAS / "TAE.Template.DS1.xml"), template(DSAS / "TAE.Template.ER.xml")
    a1, ae = type_id(t1, "InvokeAttackBehavior"), type_id(te, "InvokeAttackBehavior")
    dsr = {ntpath.basename(f.Name).lower(): f for f in read_binder(BND3, str(DSR_SRC)).Files}
    er = {ntpath.basename(f.Name).lower(): f for f in read_binder(BND4, str(ER_ANI)).Files}
    rows = []
    for g, pairs in mapping.items():
        if f"{g}.tae" not in dsr or f"{g}.tae" not in er:
            print(f"  {g}: brak TAE w DSR lub ER - pomijam")
            continue
        dt = {int(a.ID): list(a.Events) for a in read_file(TAE, dsr[f"{g}.tae"].Bytes).Animations}
        et = {int(a.ID): list(a.Events) for a in read_file(TAE, er[f"{g}.tae"].Bytes).Animations}
        gnum = int(g[1:])
        for d_id, e_id in pairs:
            kd = knots(dt.get(d_id, []), a1, (4,))
            ke = knots(et.get(e_id, []), ae, (115, 4))
            if not kd or not ke:
                pass  # brak animacji lub trafienia w jednej z gier
                continue
            speeds = [max(SPEED_MIN, min(SWING_MAX if i < 2 else (HEAVY_RECOVERY_MAX if gnum in HEAVY_GROUPS else SPEED_MAX), (kd[i + 1] - kd[i]) / max(1e-3, ke[i + 1] - ke[i])))
                      for i in range(3)]
            full = gnum * 10000 + d_id
            rows.append((full, kd, speeds))
            print(f"  {full}: DSR {['%.2f' % x for x in kd]} -> ER {['%.2f' % x for x in ke]}  "
                  f"predkosci {['%.2f' % s for s in speeds]}")
    lines = ["// Wygenerowane przez tools/gen_attack_speed_table.py - nie edytowac recznie.",
             "// anim, punkty DSR (s): 0, trafienie start, trafienie koniec, okno ataku; predkosc odcinkow.",
             "#pragma once",
             "struct AttackSpeedRow { int anim; float knot[4]; float speed[3]; };",
             "static const AttackSpeedRow kAttackSpeed[] = {"]
    for full, kd, sp in rows:
        lines.append(f"    {{{full}, {{{', '.join('%.4ff' % x for x in kd)}}}, {{{', '.join('%.4ff' % s for s in sp)}}}}},")
    lines.append("};")
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"OK -> {OUT} ({len(rows)} animacji)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
