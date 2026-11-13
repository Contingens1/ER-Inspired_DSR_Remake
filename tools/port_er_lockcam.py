"""
port_er_lockcam.py - kamera i lock-on z ER w DSR (LockCamParam).

DSR LockCamParam ma 6 pol (odleglosc, min. kat pionowy, pochylenie przy locku, wysokosc punktu
patrzenia, zasieg locka, FOV). ER domyslnie (wiersz 0): odleglosc 3.8 (DSR 4.0), FOV 48 (43),
wysokosc 1.45 (1.42), pochylenie przy locku 0.45 (0.6). Wiersze DSR z wartosciami domyslnymi
dostaja wartosci ER 1:1, pozostale (bossowie, ciasne miejsca) te sama zmiane wzgledna.
Zrodlo: GameParam z gry, wynik: files/param/GameParam/GameParam.parambnd.dcx moda (ModEngine2).
Definicje parametrow: Smithbox (Assets/PARAM/DS1R/Defs).

Uzycie (CMD): python tools\\port_er_lockcam.py [--dry-run]
"""
from __future__ import annotations

import argparse
import ntpath
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from sfbridge import load_soulsformats, read_binder, read_file, to_memory  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
SRC = Path(r"F:\SteamLibrary\steamapps\common\DARK SOULS REMASTERED\param\GameParam\GameParam.parambnd.dcx")
OUT = ROOT / "dist/mods/c0000_er_engine/files/param/GameParam/GameParam.parambnd.dcx"
DEF = Path(r"C:\Users\nemos\workspace\toolsy\Smithbox_2_2_6_2026_09_20_b\Assets\PARAM\DS1R\Defs\LockCamParam.xml")
DSR_DEFAULT = {"camDistTarget": 4.0, "camFovY": 43.0, "chrOrgOffset_Y": 1.42, "lockRotXShiftRatio": 0.6}
ER_DEFAULT = {"camDistTarget": 3.8, "camFovY": 48.0, "chrOrgOffset_Y": 1.45, "lockRotXShiftRatio": 0.45}


def ported(field: str, value: float) -> float:
    d, e = DSR_DEFAULT[field], ER_DEFAULT[field]
    if field == "camFovY" or field == "chrOrgOffset_Y":
        return value + (e - d)  # przesuniecie (FOV +5 stopni, punkt patrzenia +3 cm)
    return value * (e / d)      # skala (odleglosc x0.95, pochylenie przy locku x0.75)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    load_soulsformats()
    import SoulsFormats as SF
    from System import Single
    src = OUT if OUT.exists() else SRC
    bnd = read_binder(SF.BND3, str(src))
    f = next(f for f in bnd.Files if ntpath.basename(f.Name).lower() == "lockcamparam.param")
    p = read_file(SF.PARAM, f.Bytes)
    p.ApplyParamdef(SF.PARAMDEF.XmlDeserialize(str(DEF), False))
    for r in p.Rows:
        cells = {c.Def.InternalName: c for c in r.Cells}
        old = {k: float(cells[k].Value) for k in DSR_DEFAULT}
        if src == OUT:
            print("UWAGA: kontener moda juz istnieje - zakladam, ze zawiera wartosci DSR (uruchom raz)")
            return 1
        new = {k: ported(k, v) for k, v in old.items()}
        for k, v in new.items():
            cells[k].Value = Single(v)
        print(f"  {int(r.ID):>6}: " + ", ".join(f"{k} {old[k]:.2f}->{new[k]:.2f}" for k in DSR_DEFAULT))
    if args.dry_run:
        print("OK (dry-run)")
        return 0
    f.Bytes = to_memory(p.Write())
    OUT.parent.mkdir(parents=True, exist_ok=True)
    bnd.Write(str(OUT))
    bnd.Dispose()
    print(f"OK -> {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
