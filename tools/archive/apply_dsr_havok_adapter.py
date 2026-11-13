"""
apply_dsr_havok_adapter.py - adapter mechanik postaci Elden Ring -> Dark Souls Remastered.

Biblioteka: SoulsFormats (.NET) przez pythonnet (`tools/sfbridge.py`).
  ER  : BND4 + DCX_KRAK (Oodle), TAE 0x1000D
  DSR : BND3 + DCX_DFLT_10000_24_9, TAE 0x1000B, zachowanie gracza w EzState (c0000.esd.dcx)

Co robi skrypt (dla mechanik RollStrafe, MobileItemUse, OmniJump):
  1. Bierze zrodlowe animacje DSR danej mechaniki (z mapy, domyslnie wyprowadzone z ESD gracza).
  2. Tworzy klon kazdej z nich pod nowym kodem akcji >= 0x1000 (wolnym we wszystkich TAE c0000)
     i kopiuje plik HKX animacji pod nowa nazwa w odpowiednim c0000_aXx.anibnd.dcx.
     Animacje ER nie sa przenoszone 1:1 - ich HKX to Havok 2018 (DSR: 2015) i wymaga konwertera.
  3. Jesli w mapie wskazano animacje ER, przenosi z niej okna anulowania (zdarzenia JumpTable,
     typ 0) - czasy przeskalowane do dlugosci animacji DSR, payload w formacie DSR.
  4. Przepina stany EzState gracza (ChangeGeneralAnimCategorized) ze starych ID na nowe kody.
  5. Zapisuje wynik do --out (nigdy do katalogu gry).

Ograniczenie: warunki przejsc EzState nie sa modyfikowane - np. skok nadal wymaga warunku
z oryginalnego ESD (bieg). Zmiana warunkow wymaga recznej edycji bytecode i testow w grze.

Uzycie (CMD), z katalogu ds1-elden-port:
    python tools\\apply_dsr_havok_adapter.py --dsr-chr "F:\\...\\DARK SOULS REMASTERED\\chr" ^
        --er-chr "C:\\Users\\nemos\\workspace\\nuxe\\chr" --out dist\\mods\\c0000_er_engine
"""

from __future__ import annotations

import argparse
import glob
import ntpath
import json
import os
import struct
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sfbridge import load_soulsformats, read_binder, read_file, to_memory, net_bytes  # noqa: E402

ACTION_ID_BASE = 0x1000
ACTION_ID_LIMIT = 10000  # nazwy HKX w DSR maja 4 cyfry: aXX_NNNN.hkx
ESD_BANK, ESD_CHANGE_ANIM = 1, 3  # ChangeGeneralAnimCategorized(category, anim_id, ...)
JUMP_TABLE = 0

#: Brak domyslnej mapy: weryfikacja ESD wykazala, ze przewrot, skok i picie gracza DSR NIE sa
#: sterowane z c0000.esd (to logika exe). ID wyprowadzone wczesniej z ESD okazaly sie reakcjami
#: na trafienie (3150-5200), drabina (7001-7012) i stanami po ataku (6401/6414/6516).
#: Mape trzeba podac jawnie: {"Mechanika": {"dsr": [ID...], "er": ID|null}}.
DEFAULT_MAP: dict = {}


# --------------------------------------------------------------------------- EZL

def ezl_int(value: int) -> bytes:
    if -64 <= value <= 63:
        return bytes([value + 64, 0xA1])
    return b"\x82" + struct.pack("<i", value) + b"\xA1"


def ezl_parse_int(data: bytes) -> int | None:
    if len(data) == 2 and data[1] == 0xA1 and data[0] < 0x80:
        return data[0] - 64
    if len(data) == 6 and data[0] == 0x82 and data[5] == 0xA1:
        return struct.unpack("<i", data[1:5])[0]
    return None


# --------------------------------------------------------------------------- TAE

def clone_event(ev, start=None, end=None):
    from SoulsFormats import TAE
    return TAE.Event(ev.StartTime if start is None else start, ev.EndTime if end is None else end,
                     ev.Type, ev.Unk04, ev.GetParameterBytes(False), False)


def jump_table_id(ev) -> int | None:
    p = bytes(ev.GetParameterBytes(False))
    return struct.unpack_from("<i", p, 0)[0] if ev.Type == JUMP_TABLE and len(p) >= 4 else None


def anim_length(anim) -> float:
    return max((e.EndTime for e in anim.Events), default=0.0)


def transplant_windows(clone, er_anim, dsr_vocab: dict) -> int:
    """Przenies okna JumpTable z animacji ER na klon DSR. Zwraca liczbe przeniesionych okien."""
    scale = (anim_length(clone) / anim_length(er_anim)) if anim_length(er_anim) else 1.0
    moved = 0
    for er_ev in er_anim.Events:
        jt = jump_table_id(er_ev)
        if jt is None or jt not in dsr_vocab:
            continue
        start, end = er_ev.StartTime * scale, er_ev.EndTime * scale
        existing = [e for e in clone.Events if jump_table_id(e) == jt]
        for e in existing:
            e.StartTime, e.EndTime = start, end
        if not existing:
            clone.Events.Add(clone_event(dsr_vocab[jt], start, end))
        moved += 1
    return moved


def clone_animation(src, new_id: int, group: str):
    from SoulsFormats import TAE
    name = src.AnimFileName
    if name and not src.AnimFileReference:
        name = f"a{group}_{new_id:04d}.HKXwin"
    dst = TAE.Animation(new_id, src.AnimFileReference, src.Unknown1, src.Unknown2, name)
    for ev in src.Events:
        dst.Events.Add(clone_event(ev))
    for g in src.EventGroups:
        ng = TAE.EventGroup(g.EventType)
        for i in g.Indices:
            ng.Indices.Add(i)
        dst.EventGroups.Add(ng)
    return dst


def sort_animations(tae) -> None:
    anims = sorted(list(tae.Animations), key=lambda a: a.ID)
    tae.Animations.Clear()
    for a in anims:
        tae.Animations.Add(a)


# --------------------------------------------------------------------------- main

def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Adapter mechanik ER -> DSR (c0000).")
    ap.add_argument("--dsr-chr", required=True, type=Path)
    ap.add_argument("--er-chr", required=True, type=Path)
    ap.add_argument("--out", default=Path("dist/mods/c0000_er_engine"), type=Path)
    ap.add_argument("--map", type=Path, help="JSON z mapa mechanik (format jak DEFAULT_MAP).")
    ap.add_argument("--sf-dir", help="Katalog z SoulsFormats.dll i oo2core_6_win64.dll.")
    args = ap.parse_args(argv)

    if args.out.resolve().is_relative_to(args.dsr_chr.resolve().parent):
        sys.exit("BLAD: --out wskazuje do katalogu gry. Zapis tylko poza gra.")
    mech_map = json.loads(args.map.read_text("utf-8")) if args.map else DEFAULT_MAP
    if not mech_map:
        sys.exit("BLAD: podaj --map z ID animacji (domyslne ID z ESD byly bledne - zob. komentarz).")
    # sfbridge zmienia katalog roboczy procesu (Oodle) - wszystkie sciezki absolutne.
    args.dsr_chr, args.er_chr, args.out = (p.resolve() for p in (args.dsr_chr, args.er_chr, args.out))

    load_soulsformats(args.sf_dir)
    from SoulsFormats import BND3, BND4, TAE, ESD

    out_chr = args.out / "chr"
    out_chr.mkdir(parents=True, exist_ok=True)
    report: dict = {"mechanics": {}, "warnings": []}

    # -- 1. TAE DSR -----------------------------------------------------------
    dsr_ani = read_binder(BND3, str(args.dsr_chr / "c0000.anibnd.dcx"))
    taes = {}  # nazwa wpisu -> (BinderFile, TAE)
    for bf in dsr_ani.Files:
        if bf.Name.lower().endswith(".tae"):
            try:
                taes[ntpath.basename(bf.Name)] = (bf, read_file(TAE, bf.Bytes))
            except Exception as exc:  # noqa: BLE001
                report["warnings"].append(f"TAE {bf.Name}: {exc}")
    used_ids = {int(a.ID) for _, t in taes.values() for a in t.Animations}

    # -- 2. TAE ER (zrodlo okien anulowania) ----------------------------------
    er_ids = {m["er"] for m in mech_map.values() if m.get("er") is not None}
    er_anims = {}
    if er_ids:
        er_ani = read_binder(BND4, str(args.er_chr / "c0000.anibnd.dcx"))
        for bf in er_ani.Files:
            if not bf.Name.lower().endswith(".tae"):
                continue
            try:
                t = read_file(TAE, bf.Bytes)
            except Exception as exc:  # noqa: BLE001
                report["warnings"].append(f"ER TAE {ntpath.basename(bf.Name)}: {str(exc)[:80]}")
                continue
            for a in t.Animations:
                if int(a.ID) in er_ids and int(a.ID) not in er_anims:
                    er_anims[int(a.ID)] = a

    # -- 3. Kody akcji >= 0x1000 + klony -------------------------------------
    remap: dict[int, int] = {}
    next_id = ACTION_ID_BASE
    hkx_copies = []  # (nazwa_zrodla, nazwa_nowa)
    for mech, cfg in mech_map.items():
        er_anim = er_anims.get(cfg.get("er")) if cfg.get("er") is not None else None
        if cfg.get("er") is not None and er_anim is None:
            report["warnings"].append(f"{mech}: brak animacji ER {cfg['er']} - bez przeniesienia okien")
        entries = []
        for src_id in cfg["dsr"]:
            if src_id not in used_ids:
                report["warnings"].append(f"{mech}: animacji DSR {src_id} nie ma w zadnym TAE - pominieta")
                continue
            while next_id in used_ids:
                next_id += 1
            if next_id >= ACTION_ID_LIMIT:
                sys.exit("BLAD: zabraklo wolnych kodow akcji < 10000.")
            new_id = next_id
            used_ids.add(new_id)
            remap[src_id] = new_id
            windows = 0
            for name, (bf, tae) in taes.items():
                src = next((a for a in tae.Animations if int(a.ID) == src_id), None)
                if src is None:
                    continue
                group = name[1:3]  # "a20.tae" -> "20"
                vocab = {}
                for a in tae.Animations:
                    for e in a.Events:
                        jt = jump_table_id(e)
                        if jt is not None:
                            vocab.setdefault(jt, e)
                clone = clone_animation(src, new_id, group)
                if er_anim is not None:
                    windows += transplant_windows(clone, er_anim, vocab)
                tae.Animations.Add(clone)
                if not src.AnimFileReference:
                    hkx_copies.append((f"a{group}_{src_id:04d}.hkx", f"a{group}_{new_id:04d}.hkx"))
            entries.append({"dsr_src": src_id, "action_code": hex(new_id), "er_windows": windows})
        report["mechanics"][mech] = {"er_src": cfg.get("er"), "clones": entries}

    for bf, tae in taes.values():
        sort_animations(tae)
        bf.Bytes = to_memory(tae.Write())
    dsr_ani.Write(str(out_chr / "c0000.anibnd.dcx"))

    # -- 4. Kopie HKX w c0000_aXx.anibnd.dcx ----------------------------------
    pending = dict(hkx_copies)
    for path in sorted(glob.glob(str(args.dsr_chr / "c0000_a*.anibnd.dcx"))):
        bnd = read_binder(BND3, path)
        names = {ntpath.basename(bf.Name).lower(): bf for bf in bnd.Files}
        added = 0
        for src_name, new_name in list(pending.items()):
            bf = names.get(src_name.lower())
            if bf is None:
                continue
            from SoulsFormats import BinderFile
            full = ntpath.join(ntpath.dirname(bf.Name), new_name)
            new_bf = BinderFile(bf.Flags, max(int(f.ID) for f in bnd.Files) + 1, full, bf.Bytes)
            bnd.Files.Add(new_bf)
            del pending[src_name]
            added += 1
        if added:
            bnd.Write(str(out_chr / os.path.basename(path)))
            report.setdefault("hkx_files", {})[os.path.basename(path)] = added
    for src_name in pending:
        report["warnings"].append(f"Nie znaleziono HKX {src_name} w c0000_a*.anibnd.dcx")

    # -- 5. EzState gracza: przepiecie anim_id -------------------------------
    esd = read_file(ESD, str(args.dsr_chr / "c0000.esd.dcx"))
    patched = 0
    for group in esd.StateGroups:
        for state in group.Value:
            st = state.Value
            for cmds in (st.EntryCommands, st.WhileCommands, st.ExitCommands):
                for c in cmds:
                    if c.CommandBank != ESD_BANK or c.CommandID != ESD_CHANGE_ANIM or c.Arguments.Count < 2:
                        continue
                    old = ezl_parse_int(bytes(c.Arguments[1]))
                    if old in remap:
                        c.Arguments[1] = net_bytes(ezl_int(remap[old]))
                        patched += 1
    esd.Write(str(out_chr / "c0000.esd.dcx"))
    report["esd_patched_commands"] = patched

    # -- 6. chrbnd: rig/model DSR bez zmian, przepakowany jako BND3 -----------
    chr_bnd = read_binder(BND3, str(args.dsr_chr / "c0000.chrbnd.dcx"))
    chr_bnd.Write(str(out_chr / "c0000.chrbnd.dcx"))

    # -- 7. Weryfikacja: ponowny odczyt wynikow -------------------------------
    check = read_binder(BND3, str(out_chr / "c0000.anibnd.dcx"))
    found = set()
    for bf in check.Files:
        if bf.Name.lower().endswith(".tae"):
            found |= {int(a.ID) for a in read_file(TAE, bf.Bytes).Animations}
    report["verified_action_codes"] = sorted(hex(i) for i in set(remap.values()) & found)
    report["remap"] = {str(k): hex(v) for k, v in remap.items()}

    (args.out / "adapter_report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), "utf-8")
    print(json.dumps({k: report[k] for k in ("remap", "esd_patched_commands", "warnings")}, indent=1))
    print(f"Zapisano do {args.out.resolve()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
