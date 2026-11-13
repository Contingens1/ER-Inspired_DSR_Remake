"""Summary of the DLL enemy attack probe (er_engine.log, lines 'enemy <ctx> anim N +T ms ...').

  python tools/enemy_probe_report.py                      # last session, every attack: one line
  python tools/enemy_probe_report.py --detail 3017 3018   # plus samples every ~200 ms for these attacks

Per attack: distance / bearing to the player at the start and at the end, how far the enemy travelled, the
closest distance, and every drop of the player's HP with the time inside the attack (= a hit landed).
Only the enemy with the most attacks is reported (the boss), unless --ctx is given.
"""
from __future__ import annotations

import argparse
import re
from collections import Counter
from pathlib import Path

LOG = Path(__file__).resolve().parent.parent / "dist" / "mods" / "c0000_er_engine" / "bin" / "er_engine.log"
PAT = re.compile(r"\[ *(\d+) ms\] enemy (\w+) anim (\d+) \+ *(\d+) ms( START| END)?: dist ([\d.]+) m, "
                 r"bearing ([-+]\d+) deg, moved ([\d.]+) m, dy ([-+\d.]+), yaw ([-\d.]+), player hp (-?\d+)")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--log", type=Path, default=LOG)
    ap.add_argument("--detail", type=int, nargs="*", default=[])
    ap.add_argument("--ctx")
    args = ap.parse_args()
    lines = args.log.read_text(encoding="utf-8", errors="replace").splitlines()
    start = max((i for i, s in enumerate(lines) if "pierwsza klatka gry" in s), default=0)
    lines = lines[start:]
    rows, marks = [], []
    for s in lines:
        m = PAT.search(s)
        if m:
            rows.append(dict(ms=int(m[1]), ctx=m[2], anim=int(m[3]), t=int(m[4]), tag=(m[5] or "").strip(),
                             dist=float(m[6]), bearing=int(m[7]), moved=float(m[8]), hp=int(m[11])))
        elif "ZNACZNIK" in s:
            mm = re.search(r"\[ *(\d+) ms\].*ZNACZNIK (\d+)", s)
            if mm:
                marks.append((int(mm[1]), int(mm[2])))
    if not rows:
        print("no probe lines in the last session")
        return 1
    ctx = args.ctx or Counter(r["ctx"] for r in rows if r["tag"] == "START").most_common(1)[0][0]
    rows = [r for r in rows if r["ctx"] == ctx]
    attacks, cur = [], None
    for r in rows:
        if r["tag"] == "START" or cur is None or r["anim"] != cur[0]["anim"] or r["t"] < cur[-1]["t"]:
            cur = [r]
            attacks.append(cur)
        else:
            cur.append(r)
    print(f"enemy {ctx}: {len(attacks)} attacks; F8 markers at " + ", ".join(f"{m / 1000:.1f} s (#{n})" for m, n in marks))
    print(f"{'start s':>8} {'anim':>5} {'dur':>5} {'dist0':>6} {'bear0':>6} {'moved':>6} {'min d':>6} {'dist1':>6} {'bear1':>6}  hits (time in attack: hp)")
    for a in attacks:
        hits = [f"{b['t'] / 1000:.2f}s: {p['hp']}->{b['hp']}" for p, b in zip(a, a[1:]) if b["hp"] < p["hp"]]
        mk = "".join(f"  <F8 #{n}>" for m, n in marks if a[0]["ms"] <= m < a[-1]["ms"] + 1500)
        print(f"{a[0]['ms'] / 1000:8.1f} {a[0]['anim']:5d} {a[-1]['t'] / 1000:5.2f} {a[0]['dist']:6.2f} {a[0]['bearing']:+6d} "
              f"{max(r['moved'] for r in a):6.2f} {min(r['dist'] for r in a):6.2f} {a[-1]['dist']:6.2f} {a[-1]['bearing']:+6d}  "
              + ("; ".join(hits) or "-") + mk)
        if a[0]["anim"] in args.detail:
            last = -1000
            for r in a:
                if r["t"] - last >= 190 or r is a[-1]:
                    print(f"{'':14} t {r['t'] / 1000:4.2f}  dist {r['dist']:5.2f}  bearing {r['bearing']:+4d}  moved {r['moved']:5.2f}  hp {r['hp']}")
                    last = r["t"]
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
