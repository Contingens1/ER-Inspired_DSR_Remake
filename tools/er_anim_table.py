"""
er_anim_table.py - tabela animacji gracza ER z grafu zachowan (XML z HKLib).

Wejscie: c0000 Behaviors\\c0000.hkx z c0000.behbnd.dcx przekonwertowany HKLibCLI v0.1.2 do XML
(toolsy\\HKLibCLI_v0.1.2; uruchamiac z DOTNET_ROLL_FORWARD=Major).
Kazdy klip (hkbClipGenerator) ma animationName (np. a000_202000). Obiekty lacza sie wskaznikami,
wiec dla kazdego klipu wypisujemy lancuch nazwanych przodkow (selektor CMSG, stan, maszyna stanow) -
to daje znaczenie animacji ("W_Jump_N", "Rolling_CMSG" itp.).

Wyjscie: CSV  animacja;klip;rodzice (od najblizszego)  oraz podsumowanie w konsoli.
Uzycie (CMD): python tools\\er_anim_table.py work\\er_behavior\\c0000_behavior.xml work\\er_behavior\\er_anim_table.csv
"""
from __future__ import annotations

import csv
import sys
import xml.etree.ElementTree as ET
from collections import defaultdict

MAX_DEPTH = 6  # ile nazwanych przodkow wypisac


def parse(path: str):
    type_names: dict[str, str] = {}
    objects: dict[str, dict] = {}
    for _, el in ET.iterparse(path, events=("end",)):
        if el.tag == "type":
            name = el.find("name")
            if name is not None:
                type_names[el.get("id")] = name.get("value")
            el.clear()
        elif el.tag == "object":
            obj = {"type": el.get("typeid"), "name": None, "anim": None, "ptrs": []}
            for field in el.iter("field"):
                fname = field.get("name")
                s = field.find("string")
                if fname == "name" and s is not None and obj["name"] is None:
                    obj["name"] = s.get("value")
                elif fname == "animationName" and s is not None:
                    obj["anim"] = s.get("value")
            obj["ptrs"] = [p.get("id") for p in el.iter("pointer") if p.get("id") != "object0"]
            objects[el.get("id")] = obj
            el.clear()
    return type_names, objects


def main() -> int:
    src, out = sys.argv[1], sys.argv[2]
    type_names, objects = parse(src)
    parents: dict[str, list[str]] = defaultdict(list)
    for oid, o in objects.items():
        for p in o["ptrs"]:
            parents[p].append(oid)

    def ancestors(oid: str) -> list[str]:
        """Nazwy przodkow wszerz (BFS), od najblizszych; bez powtorzen."""
        seen, names, frontier = {oid}, [], [oid]
        while frontier and len(names) < MAX_DEPTH:
            nxt = []
            for f in frontier:
                for p in parents.get(f, []):
                    if p in seen:
                        continue
                    seen.add(p)
                    o = objects[p]
                    if o["name"] and o["name"] not in names:
                        names.append(f"{o['name']} [{type_names.get(o['type'], '?')}]")
                    nxt.append(p)
            frontier = nxt
        return names[:MAX_DEPTH]

    rows = []
    for oid, o in objects.items():
        if o["anim"]:
            rows.append((o["anim"], o["name"] or "", " | ".join(ancestors(oid))))
    rows.sort()
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(["animacja", "klip", "rodzice (od najblizszego)"])
        w.writerows(rows)
    print(f"obiektow {len(objects)}, klipow {len(rows)}, unikalnych animacji {len({r[0] for r in rows})} -> {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
