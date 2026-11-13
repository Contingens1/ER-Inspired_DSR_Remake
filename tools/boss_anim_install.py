"""Wstawia przeniesiona animacje (tools/boss_anim_port.py) do kopii anibnd przeciwnika i przesuwa zdarzenia TAE
tej animacji na nowy czas (odcinkami liniowo miedzy punktami kotwiczacymi stary_czas:nowy_czas).

  python tools/boss_anim_install.py c2230 3003 work/boss_port/ported/a00_3003.hkx \
      --anchor 2.03:1.10 --anchor 2.33:1.33 --anchor 5.43:3.13 --anchor 5.57:3.67 \
      --out dist/mods/boss_asylum_test/files_anim

Czyta oryginal z katalogu gry, pisze tylko do --out.
"""
from __future__ import annotations

import argparse
import ntpath
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from sfbridge import load_soulsformats, net_bytes, read_binder, read_file, to_memory  # noqa: E402

DSR_CHR = Path(r"F:\SteamLibrary\steamapps\common\DARK SOULS REMASTERED\chr")


def warp(t: float, anchors: list[tuple[float, float]]) -> float:
    if t >= anchors[-1][0]:  # za ostatnia kotwica: bez rozciagania
        return anchors[-1][1] + (t - anchors[-1][0])
    for (a0, b0), (a1, b1) in zip(anchors, anchors[1:]):
        if a0 <= t <= a1:
            return b0 + (t - a0) * (b1 - b0) / (a1 - a0) if a1 > a0 else b0
    return t


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("chr")
    ap.add_argument("anim", type=int)
    ap.add_argument("hkx", type=Path)
    ap.add_argument("--anchor", action="append", default=[], help="stary:nowy czas [s]; 0:0 dodawane samo")
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--base", type=Path, help="anibnd wyjsciowy zamiast oryginalu z gry (laczenie kilku podmian)")
    ap.add_argument("--combo-window", action="append", default=[], metavar="ANIM:START",
                    help="dodaj okno kontynuacji combo (JumpTable 23) w innej animacji, od START do jej konca")
    args = ap.parse_args(argv)
    out, hkx = args.out.resolve(), args.hkx.resolve()
    base = args.base.resolve() if args.base else None
    anchors = sorted([(0.0, 0.0)] + [tuple(float(x) for x in a.split(":")) for a in args.anchor])

    load_soulsformats()
    from SoulsFormats import BND3, TAE
    src = DSR_CHR / f"{args.chr}.anibnd.dcx"
    bnd = read_binder(BND3, str(base or src))
    hname = f"a{args.anim // 10000:02d}_{args.anim % 10000:04d}.hkx"
    hentry = next(f for f in bnd.Files if ntpath.basename(str(f.Name)).lower() == hname)
    old_size = int(hentry.Bytes.Length)
    data = hkx.read_bytes()
    hentry.Bytes = to_memory(net_bytes(data))
    print(f"{hname}: {old_size} B -> {len(data)} B ({hentry.Name})")

    tentry = next(f for f in bnd.Files if ntpath.basename(str(f.Name)).lower() == f"{args.chr}.tae")
    tae = read_file(TAE, tentry.Bytes)
    anim = next(a for a in tae.Animations if int(a.ID) == args.anim)
    for e in sorted(anim.Events, key=lambda e: (float(e.StartTime), int(e.Type))):
        s0, e0 = float(e.StartTime), float(e.EndTime)
        s1 = round(warp(s0, anchors) * 30) / 30.0
        e1 = max(round(warp(e0, anchors) * 30) / 30.0, s1 + 1 / 30.0)
        p = bytes(e.GetParameterBytes(False))
        arg = struct.unpack_from("<i", p + b"\0\0\0\0")[0]
        print(f"   typ {int(e.Type):3d} arg {arg:10d}: {s0:5.2f}-{e0:5.2f} -> {s1:5.2f}-{e1:5.2f}")
        e.StartTime, e.EndTime = s1, e1
    if args.combo_window:
        # wzor zdarzenia: dowolne istniejace JumpTable 23 w tym TAE
        tpl_ev = next(e for a in tae.Animations for e in a.Events if int(e.Type) == 0
                      and struct.unpack_from("<i", bytes(e.GetParameterBytes(False)))[0] == 23)
        for spec in args.combo_window:
            aid, start = spec.split(":")
            a = next(a for a in tae.Animations if int(a.ID) == int(aid))
            jts = [struct.unpack_from("<i", bytes(e.GetParameterBytes(False)))[0] for e in a.Events if int(e.Type) == 0]
            if 23 in jts:
                print(f"   a{aid}: okno combo juz jest - bez zmian")
                continue
            end = max(float(e.EndTime) for e in a.Events if int(e.Type) == 0 and
                      struct.unpack_from("<i", bytes(e.GetParameterBytes(False)))[0] in (78, 86))
            a.Events.Add(TAE.Event(float(start), end, 0, int(tpl_ev.Unk04), tpl_ev.GetParameterBytes(False), False))
            print(f"   a{aid}: dodane okno combo (JT23) {float(start):.2f}-{end:.2f}")
    tentry.Bytes = to_memory(tae.Write())
    dst = out / "chr" / src.name
    dst.parent.mkdir(parents=True, exist_ok=True)
    bnd.Write(str(dst))

    chk = read_binder(BND3, str(dst))
    h2 = next(f for f in chk.Files if ntpath.basename(str(f.Name)).lower() == hname)
    t2 = read_file(TAE, next(f for f in chk.Files if ntpath.basename(str(f.Name)).lower() == f"{args.chr}.tae").Bytes)
    same = bytes(h2.Bytes.ToArray()) == data
    print(f"zapisano {dst} ({dst.stat().st_size} B, oryginal {src.stat().st_size} B); plikow {chk.Files.Count} "
          f"(bylo {bnd.Files.Count}); hkx po odczycie identyczny: {same}; animacji w TAE {t2.Animations.Count}")
    return 0 if same else 1


if __name__ == "__main__":
    raise SystemExit(main())
