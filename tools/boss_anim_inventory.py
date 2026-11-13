"""Inwentarz animacji przeciwnika: rozpakowuje anibnd (DSR BND3 / ER BND4) do katalogu roboczego,
wypisuje wpisy HKX, naglowek formatu Havoka i nazwy kosci szkieletu (napisy ASCII ze skeleton.hkx).

  python tools/boss_anim_inventory.py dsr c2230 work/boss_port/dsr_c2230
  python tools/boss_anim_inventory.py er  c4810 work/boss_port/er_c4810
"""
from __future__ import annotations

import ntpath
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from sfbridge import load_soulsformats, read_binder  # noqa: E402

DSR_CHR = Path(r"F:\SteamLibrary\steamapps\common\DARK SOULS REMASTERED\chr")
ER_CHR = Path(r"C:\Users\nemos\workspace\nuxe\chr")


def main(game: str, chr_id: str, out_dir: str) -> None:
    out = Path(out_dir).resolve()  # przed zaladowaniem SoulsFormats (zmienia katalog roboczy)
    sf = load_soulsformats()
    out.mkdir(parents=True, exist_ok=True)
    for kind in ("anibnd", "chrbnd"):
        src = (DSR_CHR if game == "dsr" else ER_CHR) / f"{chr_id}.{kind}.dcx"
        bnd = read_binder(sf.BND3 if game == "dsr" else sf.BND4, str(src))
        print(f"== {src.name}: {bnd.Files.Count} wpisow")
        exts = {}
        for f in bnd.Files:
            name = ntpath.basename(str(f.Name))
            data = bytes(f.Bytes.ToArray())
            exts[Path(name).suffix.lower()] = exts.get(Path(name).suffix.lower(), 0) + 1
            if name.lower().endswith((".hkx", ".tae", ".compendium")) or "skeleton" in name.lower():
                (out / kind).mkdir(exist_ok=True)
                (out / kind / name).write_bytes(data)
        print("   rozszerzenia:", exts)
    hk = sorted((out / "anibnd").glob("*.hkx"))
    print(f"== HKX w anibnd: {len(hk)}")
    for p in hk[:3] + hk[-2:]:
        d = p.read_bytes()
        ver = re.search(rb"hk_20\d\d[\w.\-]*", d[:400]) or re.search(rb"20\d{6}", d[:64])
        print(f"   {p.name:28s} {len(d):8d} B  magic {d[:8].hex()}  {ver.group(0).decode() if ver else '?'}")
    sk = [p for p in (out / "anibnd").iterdir() if "skeleton" in p.name.lower()]
    for p in sk:
        d = p.read_bytes()
        names = [m.group(0).decode() for m in re.finditer(rb"[A-Za-z_\[\]][\w \[\]\-.]{2,40}(?=\x00)", d)]
        bones = [n for n in names if not n.startswith(("hk", "hka", "hkx", "hkp", "hkc")) and n not in ("skeleton",)]
        seen, uniq = set(), []
        for n in bones:
            if n not in seen:
                seen.add(n)
                uniq.append(n)
        (out / f"{chr_id}_skeleton_strings.txt").write_text("\n".join(uniq), encoding="utf-8")
        print(f"== szkielet {p.name}: {len(d)} B, napisow {len(uniq)} -> {chr_id}_skeleton_strings.txt")
        print("   ", ", ".join(uniq[:60]))


if __name__ == "__main__":
    main(*sys.argv[1:4])
