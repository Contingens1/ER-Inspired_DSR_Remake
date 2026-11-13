"""
NIE UZYWAC (wycofane 2026-11-11): migniecie broni przy piciu w ruchu NIE pochodzi z przerwy
miedzy stanami ESD (zostalo po tej poprawce), a poprawka psuje czyszczenie reki, gdy picie
przerwie trafienie (flaszka zostaje "przyklejona"). Prawdopodobna przyczyna migniecia: maska
kosci warstw (warstwa gornej czesci ciala nie steruje koscia broni) - odlozone do etapu animacji ER.

fix_estus_flicker.py - plynne przejscia miedzy czesciami picia (ESD Simple Estus Walking).

W ESD z modu Simple Estus Walking kazdy stan uzycia przedmiotu (maszyna stanow 1) przy wyjsciu
wysyla ChangeUpperBodyAnim(-1, ...) ("wyczysc gorna czesc ciala"), a stan nastepny dopiero potem
odtwarza kolejna animacje - przez chwile reka jest pusta i miga bron.

Dla stanow, ktore odtwarzaja animacje gornej czesci ciala, narzedzie:
  - usuwa to czyszczenie z komend wyjscia,
  - dodaje je jako komende przejscia (pass command) do kazdego przejscia prowadzacego do stanu,
    ktory sam NIE odtwarza animacji gornej czesci ciala (przerwanie, koniec) - tam reka dalej
    jest czyszczona. Przejscia do stanow z wlasna animacja (kolejna czesc picia) ida bez przerwy.
ESD tego modu przechodzi przez SoulsFormats bajt w bajt (sprawdzone), wiec zapis jest bezpieczny.

Uzycie (CMD): python tools\\fix_estus_flicker.py [--src <c0000.esd.dcx>] [--out <c0000.esd.dcx>]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from sfbridge import load_soulsformats, read_file  # noqa: E402

SRC = Path(r"C:\Users\nemos\workspace\toolsy\Simple Estus Walking\chr\c0000.esd.dcx")
OUT = Path("dist/mods/c0000_er_engine/files/chr/c0000.esd.dcx")
UPPER_BODY = (1, 1)   # ChangeUpperBodyAnim (bank, id)
CLEAR_ARG = b"\x3f\xa1"  # EZL: -1 (bajt 0x3F = -1 + 64) + koniec wyrazenia


def is_clear(cmd) -> bool:
    return (cmd.CommandBank, cmd.CommandID) == UPPER_BODY and cmd.Arguments.Count and bytes(cmd.Arguments[0]) == CLEAR_ARG


def plays_upper(state) -> bool:
    return any((c.CommandBank, c.CommandID) == UPPER_BODY and not is_clear(c) for c in state.EntryCommands)


def leaves(conds):
    for c in conds:
        if c.TargetState is not None:
            yield c
        yield from leaves(c.Subconditions)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", type=Path, default=SRC)
    ap.add_argument("--out", type=Path, default=OUT)
    ap.add_argument("--group", type=int, default=1, help="maszyna stanow z uzyciem przedmiotu")
    args = ap.parse_args(argv)
    args.src, args.out = args.src.resolve(), args.out.resolve()

    load_soulsformats()
    from SoulsFormats import ESD

    esd = read_file(ESD, str(args.src))
    group = next(kv.Value for kv in esd.StateGroups if kv.Key == args.group)
    states = {int(kv.Key): kv.Value for kv in group}
    changed = 0
    for sid, st in states.items():
        if not plays_upper(st):
            continue
        clears = [c for c in st.ExitCommands if is_clear(c)]
        if not clears:
            continue
        for c in clears:
            st.ExitCommands.Remove(c)
        moved = 0
        for cond in leaves(st.Conditions):
            target = states.get(int(cond.TargetState))
            if target is None or not plays_upper(target):
                cond.PassCommands.Insert(0, clears[0])
                moved += 1
        changed += 1
        print(f"  stan {sid}: czyszczenie przeniesione z wyjscia na {moved} przejsc (bez przejsc do stanow z wlasna animacja)")
    if not changed:
        sys.exit("BLAD: nie znaleziono stanow do poprawy - inny plik ESD?")
    args.out.parent.mkdir(parents=True, exist_ok=True)
    esd.Write(str(args.out))
    print(f"OK: {changed} stanow -> {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
