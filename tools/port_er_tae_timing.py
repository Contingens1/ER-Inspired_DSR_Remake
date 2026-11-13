"""
port_er_tae_timing.py - czasy zdarzen TAE z ER dla przewrotow/backstepow DSR (wg anim_map_movement.json).

Zdarzenia zostaja DSR-owe (gra DSR ich oczekuje); zmieniaja sie czasy. ER odziedziczyl po DS1 numeracje
glownych JumpTable (8 niesmiertelnosc, 4/16 przerwanie atakiem, 25/26 przewrot, 7 blokada obrotu), wiec:
  - JT8 (niesmiertelnosc)       <- pierwsze okno JT8 z ER
  - JT7 (blokada obrotu)        <- koniec z ER
  - JT25 (bufor przewrotu)      <- start z ER
  - SetSPRegenRatePercent (300?) / brak regeneracji staminy <- koniec z ER (zdarzenie typu 225 w DS1)
  - faza wychodzenia (zdarzenia startujace >= moment przerwania DSR - 0.15 s): przesuniete o
    delta = start JT4 w ER - start JT4 w DSR (fallback JT26).
Dziala na pliku moda files/chr/c0000.anibnd.dcx (a00.tae).

Uzycie (CMD): python tools\\port_er_tae_timing.py [--groups rolls backsteps] [--dry-run]
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

ER_ANI = Path(r"C:\Users\nemos\workspace\nuxe\chr\c0000.anibnd.dcx")
MAP = Path(__file__).resolve().parent / "anim_map_movement.json"
JT, SP_REGEN = 0, 225


def jt_of(e):
    p = bytes(e.GetParameterBytes(False))
    return struct.unpack_from("<i", p)[0] if int(e.Type) == JT and len(p) >= 4 else None


def first(events, jt=None, etype=None):
    for e in sorted(events, key=lambda e: e.StartTime):
        if (jt is not None and jt_of(e) == jt) or (etype is not None and int(e.Type) == etype):
            return e
    return None


def retime(dsr_anim, er_events) -> list[str]:
    ev = list(dsr_anim.Events)
    notes = []
    d_cancel = first(ev, jt=4) or first(ev, jt=26)
    e_cancel = first(er_events, jt=4) or first(er_events, jt=26)
    delta = (e_cancel.StartTime - d_cancel.StartTime) if (d_cancel and e_cancel) else 0.0
    threshold = d_cancel.StartTime - 0.15 if d_cancel else 99.0
    rules = {8: "invincible", 7: "turning", 25: "step_input"}
    er_ref = {name: first(er_events, jt=j) for j, name in rules.items()}
    er_sp = first(er_events, etype=SP_REGEN)
    for e in ev:
        j = jt_of(e)
        if j == 8 and er_ref["invincible"]:
            e.StartTime, e.EndTime = er_ref["invincible"].StartTime, er_ref["invincible"].EndTime
        elif j == 7 and er_ref["turning"]:
            e.EndTime = max(e.StartTime + 0.03, er_ref["turning"].EndTime)
        elif j == 25 and er_ref["step_input"]:
            e.StartTime = er_ref["step_input"].StartTime
        elif int(e.Type) == SP_REGEN and er_sp:
            e.EndTime = er_sp.EndTime
        elif e.StartTime >= threshold:
            e.StartTime = max(0.0, e.StartTime + delta)
            if e.EndTime < e.StartTime + 0.03:
                e.EndTime = e.StartTime + 0.03
    if d_cancel:
        notes.append(f"przerwania {d_cancel.StartTime + 0 if not delta else d_cancel.StartTime:.2f}s")
    notes.append(f"delta wyjscia {delta:+.2f}s")
    if er_ref["invincible"]:
        notes.append(f"niesmiertelnosc {er_ref['invincible'].StartTime:.2f}-{er_ref['invincible'].EndTime:.2f}s")
    return notes


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--groups", nargs="+", default=["rolls", "backsteps"])
    ap.add_argument("--anibnd", type=Path, default=Path("dist/mods/c0000_er_engine/files/chr/c0000.anibnd.dcx"))
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(argv)
    args.anibnd = args.anibnd.resolve()

    mapping = json.loads(MAP.read_text(encoding="utf-8"))
    pairs = {e["dsr"]: e["er"] for g in args.groups for e in mapping[g] if isinstance(e.get("dsr"), int) and e.get("er")}

    load_soulsformats()
    from SoulsFormats import BND3, BND4, TAE

    er_bnd = read_binder(BND4, str(ER_ANI))
    er_tae = read_file(TAE, next(f for f in er_bnd.Files if f.Name.lower().endswith("a00.tae")).Bytes)
    er_anims = {int(a.ID): list(a.Events) for a in er_tae.Animations if int(a.ID) in set(pairs.values())}

    bnd = read_binder(BND3, str(args.anibnd))
    tae_file = next(f for f in bnd.Files if ntpath.basename(f.Name).lower() == "a00.tae")
    tae = read_file(TAE, tae_file.Bytes)
    done = 0
    for a in tae.Animations:
        dsr_id = int(a.ID)
        if dsr_id not in pairs:
            continue
        er_ev = er_anims.get(pairs[dsr_id])
        if not er_ev:
            print(f"  {dsr_id}: brak animacji ER {pairs[dsr_id]} w TAE - pomijam")
            continue
        notes = retime(a, er_ev)
        print(f"  {dsr_id} <- ER {pairs[dsr_id]}: " + ", ".join(notes))
        done += 1
    if not args.dry_run:
        tae_file.Bytes = to_memory(tae.Write())
        tmp = args.anibnd.with_suffix(".tmp")
        bnd.Write(str(tmp))
        bnd.Dispose()
        tmp.replace(args.anibnd)
    print(f"OK: przeliczono {done} animacji" + (" (dry-run)" if args.dry_run else f" -> {args.anibnd}"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
