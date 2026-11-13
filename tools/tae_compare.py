"""
tae_compare.py - zdarzenia TAE animacji DSR i ER obok siebie, z nazwami z szablonow DS Anim Studio.

Uzycie (CMD): python tools\\tae_compare.py <dsr_id> <er_id> [<dsr_id> <er_id> ...]
Szablony: toolsy\\DSAS_4.9.9_HOTFIX_b\\Res\\TAE.Template.DS1.xml i TAE.Template.ER.xml.
Pomija zdarzenia dzwiekow/efektow (typy w SKIP), zostawia okna przerwan, niesmiertelnosc itp.
"""
from __future__ import annotations

import ntpath
import struct
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from sfbridge import load_soulsformats, read_binder, read_file  # noqa: E402

DSAS = Path(r"C:\Users\nemos\workspace\toolsy\DSAS_4.9.9_HOTFIX_b\Res")
DSR_ANI = Path(r"F:\SteamLibrary\steamapps\common\DARK SOULS REMASTERED\chr\c0000.anibnd.dcx")
ER_ANI = Path(r"C:\Users\nemos\workspace\nuxe\chr\c0000.anibnd.dcx")
SKIP_NAMES = ("Sound", "FFX", "SFX", "Decal", "Rumble", "Footstep", "Bullet", "Camera")


def template(path: Path):
    """{event_id: (nazwa, {jumptable_id: nazwa})}"""
    out = {}
    for ev in ET.parse(path).getroot().iter("event"):
        jt = {}
        for e in ev.iter("entry"):
            try:
                jt[int(e.get("value"))] = e.get("name")
            except (TypeError, ValueError):
                pass
        out[int(ev.get("id"))] = (ev.get("name"), jt)
    return out


def events(tae, anim_id: int, tpl):
    a = next((x for x in tae.Animations if int(x.ID) == anim_id), None)
    if a is None:
        return None
    rows = []
    for e in a.Events:
        name, jt = tpl.get(int(e.Type), (f"typ{e.Type}", {}))
        if any(s.lower() in (name or "").lower() for s in SKIP_NAMES):
            continue
        p = bytes(e.GetParameterBytes(False))
        if int(e.Type) == 0 and len(p) >= 4:
            j = struct.unpack_from("<i", p)[0]
            name = f"JT {jt.get(j, j)}"
        else:
            name = f"{name} {p[:8].hex()}"
        rows.append((round(e.StartTime, 2), round(e.EndTime, 2), name))
    return sorted(rows), max((e.EndTime for e in a.Events), default=0.0)


def load_taes(path: Path, BND):
    taes = {}
    for f in read_binder(BND, str(path)).Files:
        n = ntpath.basename(f.Name).lower()
        if n.endswith(".tae"):
            taes[n] = f
    return taes


def find(taes, anim_id, TAE, tpl):
    for n, f in taes.items():
        r = events(read_file(TAE, f.Bytes), anim_id, tpl)
        if r:
            return n, r
    return None, None


def main() -> int:
    ids = [int(x) for x in sys.argv[1:]]
    load_soulsformats()
    from SoulsFormats import BND3, BND4, TAE
    t_ds1, t_er = template(DSAS / "TAE.Template.DS1.xml"), template(DSAS / "TAE.Template.ER.xml")
    dsr_taes, er_taes = load_taes(DSR_ANI, BND3), {"a00.tae": None}
    er_bnd = read_binder(BND4, str(ER_ANI))
    er_taes = {ntpath.basename(f.Name).lower(): f for f in er_bnd.Files if f.Name.lower().endswith("a00.tae")}
    for dsr_id, er_id in zip(ids[::2], ids[1::2]):
        dn, dr = find(dsr_taes, dsr_id, TAE, t_ds1)
        en, er = find(er_taes, er_id, TAE, t_er)
        print(f"===== DSR {dsr_id} ({dn}, {dr[1] if dr else 0:.2f} s)   vs   ER {er_id} ({en}, {er[1] if er else 0:.2f} s)")
        for label, r in (("DSR", dr), ("ER ", er)):
            if not r:
                print(f"  {label}: brak animacji")
                continue
            for s, e, n in r[0]:
                print(f"  {label} {s:5.2f}-{e:5.2f}  {n}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
