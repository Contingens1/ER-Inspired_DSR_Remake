"""Root motion of Nightreign boss attacks over time, next to their RootMotionMultiplierEX (TAE type 760)
windows. Shows how far the raw clip moves inside the windows NR scales at run time.

  python tools/nr_rootmotion_profile.py c7720 1003030 1003033 1003026
"""
from __future__ import annotations

import json
import struct
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from havokbridge import load_havok  # noqa: E402
from sfbridge import load_soulsformats, read_file  # noqa: E402

BP = Path(__file__).resolve().parent.parent / "work" / "boss_port"


def main(nr: str, *ids: str) -> int:
    ED = BP / f"nr_{nr}" / "anibnd"
    sf = load_soulsformats()
    tae = {int(a.ID): a for a in read_file(sf.TAE, str(ED / f"{nr}.tae")).Animations}
    load_havok()
    from soulstruct.havok.core import HKX
    from soulstruct.havok.fromsoft import eldenring as e
    cmap = json.loads((ED / "compendium_map.json").read_text(encoding="utf-8"))
    comps = {}
    for s in ids:
        i = int(s)
        name = f"a{i // 1000000:03d}_{i % 1000000:06d}.hkx"
        cn = cmap.get(name) or next(v for v in cmap.values() if v)
        comps.setdefault(cn, HKX.from_path(ED / cn))
        c = e.AnimationHKX.from_path(ED / name, compendium=comps[cn]).animation_container
        rm = np.asarray(c.get_reference_frame_samples(), dtype=float)
        dur = float(c.hkx_animation.duration)
        t = np.linspace(0, dur, len(rm))

        def at(x):
            return np.array([np.interp(x, t, rm[:, k]) for k in range(4)])

        print(f"== {i}: clip {dur:.2f} s, root motion end x {rm[-1, 0]:.2f} z {rm[-1, 2]:.2f} yaw {np.degrees(rm[-1, 3]):.0f} deg")
        marks = [0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 5.0, 6.0]
        print("   dist travelled by t: " + "  ".join(f"{m:.1f}s={np.hypot(*(at(m)[[0, 2]])):.1f}m" for m in marks if m <= dur))
        for ev in tae[i].Events:
            p = bytes(ev.GetParameterBytes(False))
            if int(ev.Type) == 760:
                fl = struct.unpack_from("<5f", p, 4) if len(p) >= 24 else struct.unpack_from(f"<{(len(p) - 4) // 4}f", p, 4)
                s0, s1 = float(ev.StartTime), float(ev.EndTime)
                d = np.hypot(*((at(s1) - at(s0))[[0, 2]]))
                print(f"   760 {s0:.2f}-{s1:.2f}: floats {[round(x, 2) for x in fl]}; raw clip moves {d:.2f} m in the window")
            if int(ev.Type) == 1 and float(ev.StartTime) > 0.01:
                print(f"   hit {float(ev.StartTime):.2f}-{float(ev.EndTime):.2f}: clip at {np.hypot(*(at(float(ev.StartTime))[[0, 2]])):.1f} m")
    return 0


if __name__ == "__main__":
    sys.exit(main(*sys.argv[1:]))
