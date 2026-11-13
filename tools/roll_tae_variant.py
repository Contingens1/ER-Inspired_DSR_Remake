"""Warianty TAE uniku 710 do testu zawieszenia po uniku (2026-11-12). Bierze c0000.anibnd.dcx z moda,
zmienia jedna rzecz w animacji 710 i zapisuje do osobnego katalogu moda + konfiguracja i .bat.

  A: blokada obrotu (JumpTable 7) do konca jak w oryginale (2.33 s; w modzie konczy sie w 0.70 s)
  B: wczesna aktywacja okien przerwan (ActivateJumpTableEarly) konczy sie tam, gdzie zaczynaja sie okna
     (0.57-0.67 s; w modzie 0.57-1.10 s, czyli naklada sie na otwarte okna)

  python tools/roll_tae_variant.py
"""
from __future__ import annotations

import ntpath
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from sfbridge import load_soulsformats, read_binder, read_file, to_memory  # noqa: E402
from tae_compare import DSAS, template  # noqa: E402

MOD = Path(__file__).resolve().parent.parent / "dist" / "mods" / "c0000_er_engine"
LAUNCHER = "C:/Users/nemos/workspace/toolsy/ModEngine2/modengine2_launcher.exe".replace("/", chr(92))


def main() -> None:
    mod = MOD.resolve()
    load_soulsformats()
    from SoulsFormats import BND3, TAE
    tpl = template(DSAS / "TAE.Template.DS1.xml")
    base_cfg = (mod / "config_er_engine.toml").read_text(encoding="utf-8-sig")
    for key, desc in (("A", "blokada obrotu do konca uniku jak w oryginale"),
                      ("B", "wczesna aktywacja okien przerwan tylko do 0.67 s")):
        bnd = read_binder(BND3, str(mod / "files" / "chr" / "c0000.anibnd.dcx"))
        entry = next(f for f in bnd.Files if ntpath.basename(str(f.Name)).lower() == "a00.tae")
        tae = read_file(TAE, entry.Bytes)
        anim = next(a for a in tae.Animations if int(a.ID) == 710)
        cancel_start = min(float(e.StartTime) for e in anim.Events if int(e.Type) == 0
                           and struct.unpack_from("<i", bytes(e.GetParameterBytes(False)))[0] == 11)
        end = max(float(e.EndTime) for e in anim.Events)
        n = 0
        for e in anim.Events:
            name = tpl.get(int(e.Type), ("", {}))[0]
            jt = struct.unpack_from("<i", bytes(e.GetParameterBytes(False)) + b"\0\0\0\0")[0]
            if key == "A" and int(e.Type) == 0 and jt == 7:
                print(f"  {key}: JT7 {float(e.StartTime):.2f}-{float(e.EndTime):.2f} -> koniec {end:.2f}")
                e.EndTime = end
                n += 1
            if key == "B" and name == "ActivateJumpTableEarly" and float(e.EndTime) > cancel_start:
                e.EndTime = cancel_start
                n += 1
        assert n, key
        entry.Bytes = to_memory(tae.Write())
        dst = mod / f"files_roll{key}" / "chr" / "c0000.anibnd.dcx"
        dst.parent.mkdir(parents=True, exist_ok=True)
        bnd.Write(str(dst))
        cfg = base_cfg.replace('    { enabled = true, name = "er_engine", path = "files" },',
                               f'    {{ enabled = true, name = "roll{key}", path = "files_roll{key}" }},\n'
                               '    { enabled = true, name = "er_engine", path = "files" },')
        assert f"files_roll{key}" in cfg
        (mod / f"config_roll_test{key}.toml").write_text(f"# TEST uniku {key}: {desc}\n" + cfg, encoding="utf-8", newline="\r\n")
        (mod / f"launch_roll_test{key}.bat").write_text(
            "@echo off\nchcp 65001 >nul\n" f"rem TEST uniku {key}: {desc}. Tylko offline.\n" 'cd /d "%~dp0"\n'
            f'"{LAUNCHER}" -t dsr -c "%~dp0config_roll_test{key}.toml"\n', encoding="utf-8", newline="\r\n")
        print(f"wariant {key}: zmieniono {n} zdarzen (okna przerwan od {cancel_start:.2f} s); zapisano {dst} ({dst.stat().st_size} B)")


if __name__ == "__main__":
    main()
