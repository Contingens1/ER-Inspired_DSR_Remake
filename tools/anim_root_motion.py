"""
anim_root_motion.py - kierunek i dystans ruchu postaci (root motion) animacji HKX DSR / repozytorium ER.

Probki ruchu postaci (hkaDefaultAnimatedReferenceFrame) to float4 (x, y, z, w) na klatke, za wektorami
"w gore" (0,1,0,0) i "do przodu" (0,0,1,0) oraz wierszem z czasem trwania (patrz make_jump_variants.py).
Ostatnia probka = przesuniecie na koncu animacji: z<0 do przodu, z>0 do tylu, x w bok.

Uzycie (CMD):
  python tools\\anim_root_motion.py dsr 700-743          (animacje a00 z c0000_a00_*.anibnd.dcx gry)
  python tools\\anim_root_motion.py er 27100-27133        (a000_0xxxxx.hkx z repozytorium ER, format DSR)
"""
from __future__ import annotations

import math
import ntpath
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from make_jump_variants import find_reference_frame  # noqa: E402

DSR_CHR = Path(r"F:\SteamLibrary\steamapps\common\DARK SOULS REMASTERED\chr")
ER_REPO = Path(r"C:\Users\nemos\workspace\toolsy\Player Animations Repository"
               r"\(ER) c0000 Tarnished_c0000 Chosen Undead-748-ER-1-001-1723291686\Base Game\2016 (DSR)")


UP = struct.pack("<4f", 0.0, 1.0, 0.0, 0.0)
FWD = struct.pack("<4f", 0.0, 0.0, 1.0, 0.0)


def motion(data: bytes):
    """Probki za naglowkiem (0,1,0,0)(0,0,1,0)(czas trwania, ...) - bez zalozen o kierunku ruchu."""
    # DSR (HKX 2015): (0,1,0,0)(0,0,1,0)(czas, n) i probki od +48. Pliki z repozytorium ER
    # (HKX 2016) maja inny uklad naglowka - dla nich kierunek bierzemy z nazw w grafie zachowan ER
    # (tools/er_anim_table.py), nie z tego pomiaru.
    anchor = data.find(UP + FWD)
    if anchor < 0:
        return None
    dur = struct.unpack_from("<f", data, anchor + 32)[0]
    start = anchor + 48
    count, o = 0, start
    while o + 16 <= len(data):
        x, y, z, w = struct.unpack_from("<4f", data, o)
        if w != 0.0 or not all(math.isfinite(v) and abs(v) < 100 for v in (x, y, z)):
            break
        count, o = count + 1, o + 16
    # Koniec tablicy: w danych za nia trafiaja sie zera - bierzemy ostatnia niezerowa probke.
    last = start
    for i in range(count):
        if any(struct.unpack_from("<3f", data, start + 16 * i)):
            last = start + 16 * i
    if count < 2:
        return None
    x, y, z, _ = struct.unpack_from("<4f", data, last)
    return x, y, z, dur, count


def describe(x: float, z: float) -> str:
    if math.hypot(x, z) < 0.3:
        return "w miejscu"
    ang = math.degrees(math.atan2(-x, -z))  # 0 = przod, 90 = prawo; w ukladzie gry +x = LEWO (MoveParam: 702 RollLeft)
    for name, a in (("przod", 0), ("prawo", 90), ("tyl", 180), ("tyl", -180), ("lewo", -90)):
        if abs(ang - a) <= 45:
            return f"{name} ({ang:+.0f} st.)"
    return f"{ang:+.0f} st."


def ids(spec: str):
    a, _, b = spec.partition("-")
    return range(int(a), int(b or a) + 1)


def main() -> int:
    game, spec = sys.argv[1], sys.argv[2]
    wanted = set(ids(spec))
    found = {}
    if game == "dsr":
        from soulstruct.containers import Binder
        for f in sorted(DSR_CHR.glob("c0000_a00_*.anibnd.dcx")):
            for e in Binder.from_path(f).entries:
                n = ntpath.basename(e.name).lower()
                if n.startswith("a00_") and n.endswith(".hkx") and int(n[4:8]) in wanted:
                    found[int(n[4:8])] = e.get_uncompressed_data()
    else:
        for p in ER_REPO.rglob("a000_*.hkx"):
            i = int(p.stem[5:])
            if i in wanted and i not in found:
                found[i] = p.read_bytes()
    for i in sorted(found):
        m = motion(found[i])
        if not m:
            print(f"{i:7d}: brak probek ruchu")
            continue
        x, y, z, dur, n = m
        print(f"{i:7d}: {describe(x, z):18s} dystans {math.hypot(x, z):4.2f} m  (x {x:+.2f}, z {z:+.2f})  {dur:.2f} s")
    missing = sorted(wanted - set(found))
    if missing and len(missing) < 40:
        print("brak plikow:", missing)
    return 0


if __name__ == "__main__":
    sys.exit(main())
