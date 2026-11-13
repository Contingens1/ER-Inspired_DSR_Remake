"""Which attack / animation numbers does an enemy's ESD mention? Lists every int constant in a range found in
state commands and condition evaluators of chr/<chr>.chresdbnd or the ESD inside chrbnd.

  python tools/esd_attack_ids.py c4100 [lo hi]
"""
from __future__ import annotations

import ntpath
import struct
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from sfbridge import load_soulsformats, read_binder, read_file  # noqa: E402

DSR = Path(r"F:\SteamLibrary\steamapps\common\DARK SOULS REMASTERED")


def ints_in(raw: bytes):
    i = 0
    while i < len(raw):
        b = raw[i]
        if b == 0x82 and i + 5 <= len(raw):
            yield struct.unpack_from("<i", raw, i + 1)[0]
            i += 5
        elif b == 0x80 and i + 5 <= len(raw):
            yield int(struct.unpack_from("<f", raw, i + 1)[0])
            i += 5
        elif b == 0x81 and i + 9 <= len(raw):
            yield int(struct.unpack_from("<d", raw, i + 1)[0])
            i += 9
        else:
            i += 1


def main(chr_id: str, lo: str = "2990", hi: str = "3100") -> int:
    lo_i, hi_i = int(lo), int(hi)
    cands = [p for p in (DSR / "chr").glob(f"{chr_id}*") if "esd" in p.name.lower() or "chrbnd" in p.name.lower()]
    print("files:", [p.name for p in cands])
    sf = load_soulsformats()
    common = DSR / "chr" / "enemyCommon.esd.dcx"  # DSR enemies share one state machine
    if chr_id == "common":
        esd = read_file(sf.ESD, str(common))
        vals = Counter()
        for g in esd.StateGroups:
            for kv in g.Value:
                st = kv.Value
                stack = list(st.Conditions)
                cmds = list(st.EntryCommands) + list(st.ExitCommands) + list(st.WhileCommands)
                while stack:
                    c = stack.pop()
                    vals.update(v for v in ints_in(bytes(c.Evaluator)) if lo_i <= v <= hi_i)
                    cmds += list(c.PassCommands)
                    stack += list(c.Subconditions)
                for cmd in cmds:
                    for a in cmd.Arguments:
                        vals.update(v for v in ints_in(bytes(a)) if lo_i <= v <= hi_i)
        print("enemyCommon.esd constants:", sorted(vals.items()))
        return 0
    for p in cands:
        for f in read_binder(sf.BND3, str(p)).Files:
            name = ntpath.basename(str(f.Name))
            if not name.lower().endswith(".esd"):
                continue
            esd = read_file(sf.ESD, f.Bytes)
            found, n_states = Counter(), 0
            for g in esd.StateGroups:
                for kv in g.Value:
                    st = kv.Value
                    n_states += 1
                    cmds = list(st.EntryCommands) + list(st.ExitCommands) + list(st.WhileCommands)
                    stack = list(st.Conditions)
                    while stack:
                        c = stack.pop()
                        for v in ints_in(bytes(c.Evaluator)):
                            if lo_i <= v <= hi_i:
                                found[("cond", v)] += 1
                        cmds += list(c.PassCommands)
                        stack += list(c.Subconditions)
                    for cmd in cmds:
                        for a in cmd.Arguments:
                            for v in ints_in(bytes(a)):
                                if lo_i <= v <= hi_i:
                                    found[("cmd", v)] += 1
            print(f"{p.name} / {name}: {n_states} states")
            for kind in ("cond", "cmd"):
                print(f"   {kind}:", sorted(v for (k, v) in found if k == kind))
    return 0


if __name__ == "__main__":
    sys.exit(main(*sys.argv[1:4]))
