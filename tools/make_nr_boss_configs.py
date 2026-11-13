"""Mod Engine 2 configs and .bat launchers for the Nightreign boss test package (dist/mods/bossy_nightreign).
The player mod (er_engine DLL + c0000 files) is loaded unchanged from ../c0000_er_engine. Offline only.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent / "dist" / "mods" / "bossy_nightreign"
LAUNCHER = r"C:\Users\nemos\workspace\toolsy\ModEngine2\modengine2_launcher.exe"
VARIANTS = {
    "artorias_new": ("Artorias (c4100): 7 new Nightreign attacks (a001 set) placed on old attack slots "
                     "3000/3001/3004/3005/3007/3011/3014; original AI", ["files_c4100_nr_new"]),
    "artorias_v2": ("Artorias (c4100) v2: all original attacks kept, 8 Nightreign phase-2 attacks added as "
                    "3017-3019 / 3024-3028, AI uses them for the whole fight (tools/make_artorias_ai.py)",
                    ["files_c4100_v2"]),
    "centipede": ("Centipede Demon (c5200): attacks 3000-3009 with Nightreign animations; original AI",
                  ["files_c5200"]),
    "gaping": ("Gaping Dragon (c5260): attacks 3000-3010 with Nightreign animations; original AI",
               ["files_c5260"]),
    "all": ("all three bosses at once", ["files_c4100_nr_new", "files_c5200", "files_c5260"]),
}

# Variants that load a player DLL other than the main mod's (untested player changes ride along).
PLAYER_DLL: dict[str, str] = {}

for key, (desc, dirs) in VARIANTS.items():
    missing = [d for d in dirs if not (ROOT / d / "chr").is_dir()]
    if missing:
        print("skipped", key, "- missing", missing)
        continue
    mods = "".join(f'    {{ enabled = true, name = "nr_{d}", path = "{d}" }},\n' for d in dirs)
    (ROOT / f"config_nr_{key}.toml").write_text(
        f"# Nightreign boss test - {desc}.\n"
        "# Player mod (er_engine: DLL + c0000 files) loaded unchanged from ../c0000_er_engine.\n"
        "[modengine]\ndebug = false\nexternal_dlls = [\n"
        f'    "{PLAYER_DLL.get(key, "../c0000_er_engine/bin/er_engine.dll")}",\n]\n\n'
        "[extension.mod_loader]\nenabled = true\nloose_params = false\nmods = [\n"
        f"{mods}"
        '    { enabled = true, name = "er_engine", path = "../c0000_er_engine/files" },\n]\n\n'
        "[extension.scylla_hide]\nenabled = false\n",
        encoding="utf-8", newline="\r\n")
    (ROOT / f"launch_nr_{key}.bat").write_text(
        "@echo off\nchcp 65001 >nul\n"
        f"rem Nightreign boss test: {desc}. Offline only.\n"
        'cd /d "%~dp0"\n'
        f'"{LAUNCHER}" -t dsr -c "%~dp0config_nr_{key}.toml"\n',
        encoding="utf-8", newline="\r\n")
    print("written", key)
