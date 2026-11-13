"""Generuje konfiguracje ModEngine2 i pliki .bat dla moda testowego bossa (dist/mods/boss_asylum_test).
Mod gracza (er_engine) jest dolaczany bez zmian z ../c0000_er_engine.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent / "dist" / "mods" / "boss_asylum_test"
OMNI = ("C:/Users/nemos/workspace/toolsy/ModEngine2 Version - DSR Omni-Directional Rolling 1378 1.01 "
        "2026-07-24T21-39Z 8HOjd3zer/dllMods/DSROmniRoll/DSROmniRoll.dll")
LAUNCHER = "C:/Users/nemos/workspace/toolsy/ModEngine2/modengine2_launcher.exe".replace("/", chr(92))
VARIANTS = {
    # Asylum Demon = c2232, AI 223200. (c2230 / AI 223000 to Stray Demon.)
    "er": ("Asylum Demon z atakami ER: 3008, 3010, 3011, 3012 z Erdtree Avatara + polaczenia combo z ER w AI",
           ["files_c2232_er", "files_c2232_er_ai"]),
    "er_anim_only": ("tylko animacje ER (3008, 3010-3012), AI oryginalne", ["files_c2232_er"]),
    "hip_er": ("TEST: boss robi tylko atak 3008 (skok i siad) w wersji ER", ["files_c2232_anim3008", "files_c2232_ai3008"]),
    "hip_orig": ("TEST: boss robi tylko atak 3008 (skok i siad), animacja oryginalna", ["files_c2232_ai3008"]),
}

for key, (desc, dirs) in VARIANTS.items():
    mods = "".join(f'    {{ enabled = true, name = "boss_{d}", path = "{d}" }},\n' for d in dirs)
    (ROOT / f"config_asylum_{key}.toml").write_text(
        f"# Test bossa (Asylum Demon) - {desc}.\n"
        "# Mod gracza (er_engine: DLL + pliki c0000) ladowany bez zmian z ../c0000_er_engine.\n"
        "[modengine]\ndebug = false\nexternal_dlls = [\n"
        f'    "{OMNI}",\n'
        '    "../c0000_er_engine/bin/er_engine.dll",\n]\n\n'
        "[extension.mod_loader]\nenabled = true\nloose_params = false\nmods = [\n"
        f"{mods}"
        '    { enabled = true, name = "er_engine", path = "../c0000_er_engine/files" },\n]\n\n'
        "[extension.scylla_hide]\nenabled = false\n",
        encoding="utf-8", newline="\r\n")
    (ROOT / f"launch_asylum_{key}.bat").write_text(
        "@echo off\nchcp 65001 >nul\n"
        f"rem Test bossa: {desc}. Tylko offline.\n"
        'cd /d "%~dp0"\n'
        f'"{LAUNCHER}" -t dsr -c "%~dp0config_asylum_{key}.toml"\n',
        encoding="utf-8", newline="\r\n")
    print("zapisano", key)
