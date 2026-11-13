"""
port_er_attack_timing.py - okna po trafieniu z ER dla atakow DSR (animacja i trafienie zostaja DSR).

Dla pary (grupa, dsr_id, er_id): koniec trafienia = koniec ostatniego zdarzenia InvokeAttackBehavior.
Kazde okno przerwania DSR (JumpTable) dostaje start = koniec_trafienia_DSR + (start_w_ER - koniec_trafienia_ER),
nie wczesniej niz koniec trafienia DSR. Odpowiedniki okien ER -> DSR (numeracja JT wspolna z DS1, poza
kombinacja R1, ktora w ER ma osobne okno 115 "InvokeAnimCancelEnd_R1_LightKick"):
    DSR JT4 (kolejny atak prawa reka)  <- ER JT115 (fallback ER JT4)
    JT26 przewrot, JT16 atak lewa, JT22 blok, JT29 magia, JT31 przedmiot, JT11 ruch, JT32 ogolne <- ten sam JT w ER
Pary: anim_map_attacks.json  {"a26": [[3000, 30000], ...], ...}. Dziala na files/chr/c0000.anibnd.dcx.

Uzycie (CMD): python tools\\port_er_attack_timing.py [--groups a26] [--dry-run]
"""
from __future__ import annotations

import argparse
import json
import ntpath
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from sfbridge import load_soulsformats, read_binder, read_file, to_memory  # noqa: E402
from tae_compare import DSAS, ER_ANI, template  # noqa: E402

MAP = Path(__file__).resolve().parent / "anim_map_attacks.json"
JT_PAIRS = {4: (115, 4), 26: (26,), 16: (16,), 22: (22,), 29: (29,), 31: (31,), 11: (11,), 32: (32,)}


def type_id(tpl, name: str) -> int:
    return next(i for i, (n, _) in tpl.items() if n == name)


def jt(e):
    p = bytes(e.GetParameterBytes(False))
    return struct.unpack_from("<i", p)[0] if int(e.Type) == 0 and len(p) >= 4 else None


def hit_end(events, attack_type: int):
    ends = [e.EndTime for e in events if int(e.Type) == attack_type]
    return max(ends) if ends else None


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--groups", nargs="*", help="grupy z anim_map_attacks.json (domyslnie wszystkie)")
    ap.add_argument("--anibnd", type=Path, default=Path("dist/mods/c0000_er_engine/files/chr/c0000.anibnd.dcx"))
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(argv)
    args.anibnd = args.anibnd.resolve()
    mapping = {k: v for k, v in json.loads(MAP.read_text(encoding="utf-8")).items() if not k.startswith("_")}
    groups = args.groups or list(mapping)

    load_soulsformats()
    from SoulsFormats import BND3, BND4, TAE
    t_ds1, t_er = template(DSAS / "TAE.Template.DS1.xml"), template(DSAS / "TAE.Template.ER.xml")
    atk_ds1, atk_er = type_id(t_ds1, "InvokeAttackBehavior"), type_id(t_er, "InvokeAttackBehavior")
    early_ds1 = type_id(t_ds1, "ActivateJumpTableEarly")

    er_files = {ntpath.basename(f.Name).lower(): f for f in read_binder(BND4, str(ER_ANI)).Files}
    bnd = read_binder(BND3, str(args.anibnd))
    dsr_files = {ntpath.basename(f.Name).lower(): f for f in bnd.Files}
    for g in groups:
        tae_name = f"{g}.tae"
        dsr_file = dsr_files[tae_name]
        dsr_tae = read_file(TAE, dsr_file.Bytes)
        er_tae = read_file(TAE, er_files[tae_name].Bytes)
        dsr_anims = {int(a.ID): a for a in dsr_tae.Animations}
        er_anims = {int(a.ID): list(a.Events) for a in er_tae.Animations}
        for dsr_id, er_id in mapping[g]:
            a, er_ev = dsr_anims.get(dsr_id), er_anims.get(er_id)
            if a is None or er_ev is None:
                print(f"  {g}:{dsr_id} <- {er_id}: brak animacji - pomijam")
                continue
            d_hit, e_hit = hit_end(list(a.Events), atk_ds1), hit_end(er_ev, atk_er)
            if d_hit is None or e_hit is None:
                print(f"  {g}:{dsr_id} <- {er_id}: brak trafienia w jednej z animacji - pomijam")
                continue
            changes = []
            shifts = {}  # jt -> (stary start, nowy start)
            for e in a.Events:
                j = jt(e)
                if j not in JT_PAIRS:
                    continue
                src = next((x for want in JT_PAIRS[j] for x in sorted(er_ev, key=lambda x: x.StartTime) if jt(x) == want), None)
                if src is None:
                    continue
                new = max(d_hit, d_hit + (src.StartTime - e_hit))
                if abs(new - e.StartTime) > 0.01:
                    changes.append(f"JT{j} {e.StartTime:.2f}->{new:.2f}")
                    shifts.setdefault(j, (e.StartTime, new))
                    e.StartTime = new
                    if e.EndTime < new + 0.03:
                        e.EndTime = new + 0.03
            # Wczesna aktywacja okien (ActivateJumpTableEarly, pierwszy int = JT) wyzwala przejscie
            # PRZED startem okna - przesuwamy ja razem z oknem, zachowujac odstep.
            for e in a.Events:
                if int(e.Type) != early_ds1:
                    continue
                j = struct.unpack_from("<i", bytes(e.GetParameterBytes(False)))[0]
                if j in shifts:
                    old, new = shifts[j]
                    delta = new - old
                    e.StartTime, e.EndTime = max(0.0, e.StartTime + delta), max(0.03, e.EndTime + delta)
                    changes.append(f"wczesnaJT{j} {delta:+.2f}")
            print(f"  {g}:{dsr_id} <- ER {er_id} (trafienie DSR do {d_hit:.2f}s, ER do {e_hit:.2f}s): " + (", ".join(changes) or "bez zmian"))
        if not args.dry_run:
            dsr_file.Bytes = to_memory(dsr_tae.Write())
    if not args.dry_run:
        tmp = args.anibnd.with_suffix(".tmp")
        bnd.Write(str(tmp))
        bnd.Dispose()
        tmp.replace(args.anibnd)
    print("OK" + (" (dry-run)" if args.dry_run else f" -> {args.anibnd}"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
