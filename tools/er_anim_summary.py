"""
er_anim_summary.py - czytelny wyciag z tabeli animacji ER (er_anim_table.csv).

Dla kazdej animacji z podanego prefiksu (domyslnie a000_ = ruch bazowy) bierze pierwsza nazwe
przodka, ktora nie jest nazwa klipu (zwykle selektor CMSG albo stan), i grupuje animacje po
kategorii (Rolling, BackStep, Jump, Move, Land, Item...). Wynik: markdown do docs.

Uzycie (CMD): python tools\\er_anim_summary.py work\\er_behavior\\er_anim_table.csv docs\\er_anim_a000.md [a000_]
"""
from __future__ import annotations

import csv
import re
import sys
from collections import defaultdict

CATEGORIES = [
    ("Przewroty (Rolling)", r"roll"), ("Backstep", r"backstep"), ("Skok", r"jump"),
    ("Ladowanie / upadek", r"land|fall"), ("Chod / bieg / sprint", r"move|walk|run|dash|sprint|stealth"),
    ("Obrot", r"turn"), ("Przedmioty / estus", r"item|drink|estus|flask"), ("Blok / parowanie", r"guard|parry"),
    ("Stanie (idle)", r"idle|stand|wait"), ("Obrazenia", r"damage|down|knockback"),
]


def main() -> int:
    src, out = sys.argv[1], sys.argv[2]
    prefix = sys.argv[3] if len(sys.argv) > 3 else "a000_"
    names: dict[str, str] = {}
    for anim, clip, parents in csv.reader(open(src, encoding="utf-8"), delimiter=";"):
        if not anim.startswith(prefix) or anim in names:
            continue
        first = next((p.split(" [")[0] for p in parents.split(" | ") if p and not p.startswith(anim)), "")
        names[anim] = first
    groups = defaultdict(list)
    for anim, name in sorted(names.items()):
        cat = next((c for c, rx in CATEGORIES if re.search(rx, name, re.I)), "Inne")
        groups[cat].append((anim, name))
    with open(out, "w", encoding="utf-8") as f:
        f.write(f"# Animacje gracza ER ({prefix}*) - nazwy z grafu zachowan\n\n")
        f.write("Zrodlo: `c0000.behbnd` (Behaviors/c0000.hkx) -> XML (HKLibCLI v0.1.2) -> `tools/er_anim_table.py`.\n"
                "Nazwa = najblizszy nazwany selektor/stan nad klipem. Pelne lancuchy: `work/er_behavior/er_anim_table.csv`.\n\n")
        for cat in [c for c, _ in CATEGORIES] + ["Inne"]:
            if groups.get(cat):
                f.write(f"## {cat} ({len(groups[cat])})\n\n| Animacja | Nazwa w ER |\n|---|---|\n")
                for anim, name in groups[cat]:
                    f.write(f"| `{anim}` | {name} |\n")
                f.write("\n")
    print({c: len(v) for c, v in groups.items()}, "->", out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
