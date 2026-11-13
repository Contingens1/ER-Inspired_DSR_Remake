"""AI przeciwnikow DSR (script/*.luabnd.dcx): dekompilacja, podmiana jednego skryptu, spakowanie.

Uzywa Soulstruct (pip) - ma w srodku DSLuaDecompiler i LuaC x64 dla DSR. Nic nie pisze do katalogu gry.

  python tools/ai_lua.py list   m18_01_00_00
  python tools/ai_lua.py dump   m18_01_00_00 analysis/ai/m18_01          # wszystkie skrypty -> .lua
  python tools/ai_lua.py build  m18_01_00_00 223000_battle.lua moj.lua OUT.luabnd.dcx
  python tools/ai_lua.py verify OUT.luabnd.dcx 223000_battle.lua          # ponowna dekompilacja z paczki
"""
from __future__ import annotations

import sys
from pathlib import Path

GAME = Path(r"F:\SteamLibrary\steamapps\common\DARK SOULS REMASTERED")


def _open(name_or_path: str):
    from soulstruct.containers import Binder
    p = Path(name_or_path)
    if not p.exists():
        p = GAME / "script" / f"{name_or_path}.luabnd.dcx"
    return Binder.from_path(p), p


def _entry_name(e) -> str:
    return Path(e.path.replace("\\", "/")).name


def cmd_list(name):
    bnd, p = _open(name)
    print(p)
    for e in bnd.entries:
        print(f"  {e.entry_id:5d} {len(e.data):7d} {_entry_name(e)}")


def cmd_dump(name, out_dir):
    from soulstruct.base.ai.lua import decompile_lua, LuaDecompileError
    bnd, _ = _open(name)
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    ok = bad = 0
    for e in bnd.entries:
        n = _entry_name(e)
        if not n.endswith(".lua"):
            (out / n).write_bytes(e.data)
            continue
        if not e.data.startswith(b"\x1bLua"):
            (out / n).write_bytes(e.data)  # juz tekst
            ok += 1
            continue
        try:
            (out / n).write_text(decompile_lua(e.data, n), encoding="shift_jis", errors="replace")
            ok += 1
        except LuaDecompileError as ex:
            bad += 1
            print("  BLAD dekompilacji", n, str(ex)[:200])
    print(f"zdekompilowano {ok}, bledow {bad} -> {out}")


def cmd_build(name, script_name, lua_path, out_path, plain="0"):
    """Podmienia jeden skrypt. plain=1: wklada tekst zrodlowy bez kompilacji (do testu, czy gra to czyta)."""
    from soulstruct.base.ai.lua import compile_lua
    bnd, _ = _open(name)
    src = Path(lua_path).read_text(encoding="shift_jis")
    target = [e for e in bnd.entries if _entry_name(e) == script_name]
    assert len(target) == 1, f"brak wpisu {script_name}"
    if plain == "1":
        data = src.encode("shift_jis")
    else:
        data = compile_lua(src, script_name, x64=True)
    old = len(target[0].data)
    target[0].data = data
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    # Binder.write pakuje wpisy tak jak sa (bez regeneracji LuaBND) - zmienia sie tylko jeden wpis.
    bnd.write(out)
    print(f"{script_name}: {old} -> {len(data)} B; zapisano {out} ({out.stat().st_size} B)")


def cmd_verify(path, script_name):
    from soulstruct.base.ai.lua import decompile_lua
    from soulstruct.containers import Binder
    b = Binder.from_path(Path(path))
    e = [e for e in b.entries if _entry_name(e) == script_name][0]
    text = e.data.decode("shift_jis") if not e.data.startswith(b"\x1bLua") else decompile_lua(e.data, script_name)
    sys.stdout.write(text)


if __name__ == "__main__":
    {"list": cmd_list, "dump": cmd_dump, "build": cmd_build, "verify": cmd_verify}[sys.argv[1]](*sys.argv[2:])
