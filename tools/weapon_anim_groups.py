"""
weapon_anim_groups.py - grupy animacji atakow broni DSR (EquipParamWeapon.AttackAnimationCategory)
zestawione z nazwanymi grupami ER z repozytorium animacji (foldery "a0GG - Nazwa").

Wyjscie: docs/weapon_groups_dsr_er.md (grupa DSR, przykladowe bronie, grupa ER o tym numerze).
Uzycie (CMD): python tools\\weapon_anim_groups.py
"""
from __future__ import annotations

import logging
import re
from collections import defaultdict
from pathlib import Path

logging.disable(logging.WARNING)
from soulstruct.darksouls1r.params import GameParamBND  # noqa: E402

GAMEPARAM = r"F:\SteamLibrary\steamapps\common\DARK SOULS REMASTERED\param\GameParam\GameParam.parambnd.dcx"
REPO = Path(r"C:\Users\nemos\workspace\toolsy\Player Animations Repository"
            r"\(ER) c0000 Tarnished_c0000 Chosen Undead-748-ER-1-001-1723291686\Base Game\2016 (DSR)")
OUT = Path(__file__).resolve().parent.parent / "docs" / "weapon_groups_dsr_er.md"


def main() -> int:
    gp = GameParamBND.from_path(GAMEPARAM)
    weapons = gp.get_param("EquipParamWeapon")
    groups = defaultdict(list)
    for rid, row in weapons.rows.items():
        name = str(row.Name).strip()
        if rid % 100 or not name:  # tylko bazowe warianty (bez +1..+15 i infuzji)
            continue
        groups[int(row.AttackAnimationCategory)].append(name)
    er = {}
    for d in REPO.iterdir():
        m = re.match(r"a(\d{3}) - (.+)", d.name)
        if m:
            er[int(m.group(1))] = m.group(2)
    lines = ["# Grupy animacji atakow: DSR <-> ER\n",
             "DSR: `EquipParamWeapon.AttackAnimationCategory` (grupa TAE aGG). ER: foldery repozytorium Nexus #748 (a0GG).\n",
             "Ten sam numer = kandydat na odpowiednik; kolumna 'Zgodne?' do oceny (nazwy broni vs nazwa grupy ER).\n",
             "| DSR aGG | Bronie DSR (przyklady) | ER a0GG | Zgodne? |", "|---|---|---|---|"]
    for g in sorted(groups):
        names = sorted(set(groups[g]))
        sample = ", ".join(names[:5]) + (f" (+{len(names) - 5})" if len(names) > 5 else "")
        lines.append(f"| a{g:02d} | {sample} | {er.get(g, '— brak —')} | ? |")
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    for line in lines[3:]:
        print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
