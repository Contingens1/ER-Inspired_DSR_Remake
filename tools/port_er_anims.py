"""
port_er_anims.py - podmiana animacji ruchu DSR na odpowiedniki z ER wg mapy (anim_map_movement.json).

Dla kazdej pary dsr -> er: plik a00_NNNN.hkx w kontenerze c0000_a00_*.anibnd.dcx dostaje dane
a000_NNNNNN.hkx z repozytorium animacji ER (Nexus #748, folder "2016 (DSR)"). ID wpisu i nazwa
zostaja (gra szuka HKX po ID = ID animacji). Zdarzenia TAE (niesmiertelnosc, okna przerwan) zostaja
DSR-owe. Kontener bierzemy z katalogu moda (files/chr), a jesli go tam nie ma - z gry.

Uzycie (CMD): python tools\\port_er_anims.py [--groups rolls backsteps] [--dry-run]
"""
from __future__ import annotations

import argparse
import json
import ntpath
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from sfbridge import load_soulsformats, read_binder, to_memory  # noqa: E402

DSR_CHR = Path(r"F:\SteamLibrary\steamapps\common\DARK SOULS REMASTERED\chr")
REPO = Path(r"C:\Users\nemos\workspace\toolsy\Player Animations Repository"
            r"\(ER) c0000 Tarnished_c0000 Chosen Undead-748-ER-1-001-1723291686\Base Game\2016 (DSR)")
MAP = Path(__file__).resolve().parent / "anim_map_movement.json"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--groups", nargs="+", default=["rolls", "backsteps"])
    ap.add_argument("--out", type=Path, default=Path("dist/mods/c0000_er_engine/files"))
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--stance-groups", nargs="*", default=["00"],
                    help="grupy postaw (DSR aGG <-> ER a0GG), np. 00 02 03 10 12 13 14 15 16")
    args = ap.parse_args(argv)
    out_chr = (args.out / "chr").resolve()

    mapping = json.loads(MAP.read_text(encoding="utf-8"))
    pairs = {e["dsr"]: e["er"] for g in args.groups for e in mapping[g] if isinstance(e.get("dsr"), int) and e.get("er")}
    er_files = {p.stem: p for p in REPO.rglob("a0*.hkx")}
    # Cel (nazwa pliku DSR) -> plik ER. Grupa postawy GG: aGG_NNNN.hkx <- a0GG_0xxxxx.hkx.
    targets = {}
    for gg in args.stance_groups:
        for dsr, er in pairs.items():
            stem = f"a0{gg}_{er:06d}"
            if stem in er_files:
                targets[f"a{gg}_{dsr:04d}.hkx"] = stem
            elif gg == "00":
                print(f"  UWAGA: brak {stem} w repozytorium - a00_{dsr:04d} zostaje DSR")

    load_soulsformats()
    from SoulsFormats import BND3
    from System import Array, Byte

    todo = dict(targets)
    total = len(todo)
    for game_file in sorted(DSR_CHR.glob("c0000_a*.anibnd.dcx")):
        src = out_chr / game_file.name if (out_chr / game_file.name).exists() else game_file
        bnd = read_binder(BND3, str(src))
        changed = 0
        for f in bnd.Files:
            n = ntpath.basename(f.Name).lower()
            if n not in todo:
                continue
            stem = todo.pop(n)
            data = er_files[stem].read_bytes()
            print(f"  {game_file.name}: {n} <- {stem}.hkx ({len(data)} B)")
            if not args.dry_run:
                f.Bytes = to_memory(Array[Byte](list(data)))
            changed += 1
        if changed and not args.dry_run:
            out_chr.mkdir(parents=True, exist_ok=True)
            tmp = out_chr / (game_file.name + ".tmp")
            bnd.Write(str(tmp))
            bnd.Dispose()
            tmp.replace(out_chr / game_file.name)
        else:
            bnd.Dispose()
    if todo:
        print("UWAGA: nie znaleziono w kontenerach gry:", sorted(todo))
    print(f"OK: podmieniono {total - len(todo)} animacji" + (" (dry-run)" if args.dry_run else f" -> {out_chr}"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
