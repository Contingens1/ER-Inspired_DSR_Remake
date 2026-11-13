"""Nightreign chr inventory and DS1-boss matching.

Reads every chr in nuxe_nr/chr through SoulsFormats (BND4), reports container readability, HKX/TAE counts,
skeleton bone names, and scores each NR chr against DSR boss skeletons by bone-name overlap.

  python tools/nr_inventory.py                 # table + matches -> analysis/nr_inventory.txt
  python tools/nr_inventory.py --unpack c7500  # also dump HKX/TAE/skeleton to work/boss_port/nr_c7500
"""
from __future__ import annotations

import argparse
import ntpath
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from sfbridge import load_soulsformats, read_binder  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
NR_CHR = ROOT / "nuxe_nr" / "chr"
DSR_CHR = Path(r"F:\SteamLibrary\steamapps\common\DARK SOULS REMASTERED\chr")
DSR_BOSSES = {"c4100": "Artorias", "c2240": "Capra Demon", "c5260": "Gaping Dragon", "c5200": "Centipede Demon"}
STR_RE = re.compile(rb"[A-Za-z_\[\]][\w \[\]\-.]{2,40}(?=\x00)")


def bone_strings(data: bytes) -> list[str]:
    seen, out = set(), []
    for m in STR_RE.finditer(data):
        n = m.group(0).decode()
        if n.startswith(("hk", "hka", "hkx", "hkp", "hkc")) or n in ("skeleton", "float", "char", "void"):
            continue
        if n not in seen:
            seen.add(n)
            out.append(n)
    return out


def norm(name: str) -> str:
    return re.sub(r"[^a-z0-9]", "", name.lower())


def entries(sf, cls, path: Path):
    bnd = read_binder(cls, str(path))
    return [(ntpath.basename(str(f.Name)), f) for f in bnd.Files]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--unpack", nargs="*", default=[])
    args = ap.parse_args(argv)
    sf = load_soulsformats()
    lines: list[str] = []

    def emit(s: str = "") -> None:
        print(s)
        lines.append(s)

    dsr = {}
    for cid, label in DSR_BOSSES.items():
        skel = None
        n_hkx = 0
        for kind in ("anibnd", "chrbnd"):
            for name, f in entries(sf, sf.BND3, DSR_CHR / f"{cid}.{kind}.dcx"):
                low = name.lower()
                if low.endswith(".hkx") and kind == "anibnd" and "skeleton" not in low:
                    n_hkx += 1
                if "skeleton" in low and skel is None:
                    skel = bone_strings(bytes(f.Bytes.ToArray()))
        dsr[cid] = {norm(b) for b in (skel or [])}
        emit(f"DSR {cid} {label}: {n_hkx} anims, {len(dsr[cid])} skeleton strings")

    emit()
    emit(f"{'chr':6} {'ok':3} {'hkx':>5} {'tae':>4} {'bones':>5}  DCX / best DSR match (shared bone names)")
    ids = sorted({p.name[:5] for p in NR_CHR.glob("c*.anibnd.dcx")})
    for cid in ids:
        n_hkx = n_tae = 0
        skel: list[str] = []
        ok = "ok"
        dcx_type = "?"
        dump = cid in args.unpack
        out = ROOT / "work" / "boss_port" / f"nr_{cid}" / "anibnd"
        try:
            for p in sorted(NR_CHR.glob(f"{cid}*.anibnd.dcx")):
                head = p.read_bytes()[:0x30]
                dcx_type = head[0x28:0x2C].decode("ascii", "replace")
                for name, f in entries(sf, sf.BND4, p):
                    low = name.lower()
                    data = None
                    if low.endswith(".hkx") and "skeleton" not in low:
                        n_hkx += 1
                    if low.endswith(".tae"):
                        n_tae += 1
                    if "skeleton" in low:
                        data = bytes(f.Bytes.ToArray())
                        skel = bone_strings(data)
                    if dump and low.endswith((".hkx", ".tae", ".compendium")):
                        out.mkdir(parents=True, exist_ok=True)
                        (out / name).write_bytes(data if data is not None else bytes(f.Bytes.ToArray()))
        except Exception as ex:  # report, keep going
            ok = "ERR"
            emit(f"{cid}: {type(ex).__name__}: {str(ex)[:160]}")
        nb = {norm(b) for b in skel}
        scores = sorted(((len(nb & d) / max(1, len(d)), len(nb & d), k) for k, d in dsr.items()), reverse=True)
        # second percentage: share of the NR chr's own names found in the DSR skeleton
        best = ", ".join(f"{DSR_BOSSES[k]} {int(s * 100)}%/{int(100 * n / max(1, len(nb)))}% ({n})"
                         for s, n, k in scores[:2])
        emit(f"{cid:6} {ok:3} {n_hkx:5d} {n_tae:4d} {len(skel):5d}  {dcx_type} / {best}")
        if dump:
            (out.parent / f"{cid}_skeleton_strings.txt").write_text("\n".join(skel), encoding="utf-8")
    (ROOT / "analysis").mkdir(exist_ok=True)
    (ROOT / "analysis" / "nr_inventory.txt").write_text("\n".join(lines), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
