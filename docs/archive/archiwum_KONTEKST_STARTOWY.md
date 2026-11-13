# KONTEKST_STARTOWY — Souls Stance & Combat Overhaul (ER → DS1)

Data: 2026-10-26/27

## 1. Co ustalono i zrobiono

**Decyzje (potwierdzone przez użytkownika):**
- Baza portu: **DSR** (Dark Souls Remastered). Referencja: **Elden Ring**.
- Referencyjne paramy ER pozyskane przez **rozpakowanie `regulation.bin`** (WitchyBND).
- Pierwszy przebieg: **tylko ekstrakcja + plan, bez zapisu do plików gry**.
- Otwarte: konwersja `.param` → XML — ustalono **zostawiamy ER w formacie binarnym `.param`**.

**Środowisko (rozpoznane):**

| Zasób | Stan |
|---|---|
| `F:\SteamLibrary\steamapps\common\DARK SOULS REMASTERED` | rozpakowany: `param/DrawParam/*.parambnd.dcx` (10 pl.), `param/GameParam/GameParam.parambnd.dcx`, `paramdef/paramdef.paramdefbnd.dcx`, `chr/*.chrbnd.dcx`, `script/*.luabnd.dcx` |
| `F:\SteamLibrary\steamapps\common\ELDEN RING\Game` | `regulation.bin` (2 045 728 B), `Data0-3.bhd/bdt`, `DLC.bhd/bdt` |
| `F:\SteamLibrary\steamapps\common\DARK SOULS III` | **nierozpakowany** (89 plików) — poza zakresem |
| `C:\Users\nemos\workspace\toolsy` | Nuxe 1.2.1, WitchyBND 3.0.1.0 (win-x64) |
| Plugin `universal-modder` | 12 skills, baza 201 notatek; kluczowa: `knowledge/games/elden-ring/porting-dark-souls-remastered-enemies-into-elden-ring.md` |
| Python | 3.15.2 w `C:\Python315`; stdlib `compression.zstd`; zainstalowane: `soulstruct` 2.6.0, `pyyaml`, `zstandard` |

**Wykonane operacje:**
- `regulation.bin` (kopia w workspace) **rozpakowany** WitchyBND → `work/er/regulation-bin/`: **195 plików `.param`** + manifest `_witchy-bnd4.xml` (wersja `11730034`, `DCX_ZSTD`, root DLC02).
- Ustalono format: pliki ER `.param` to **binarny FSParam**; nazwy kolumn są **poza plikiem** (w `Names1`/`Names2` w `regulation.bin`), dlatego nagłówek pliku wygląda na „pusty".
- Paramdex w `Assets/Paramdex/ER/`: `Defs/` (194 definicje XML), `Names/` (741 plików .txt z kolejnością kolumn i ID).
- `soulstruct` ma gotowe mapowania dla `ELDEN_RING` i `DARK_SOULS_DSR`, w tym `GameParamBND`, `ParamCrypt`, `examine_er_params`.

**Pułapki / ustalenia techniczne:**
- Klasyfikator bezpieczeństwa Bash bywa blokujący lub pada timeoutem — **pracować krótkimi komendami i ponawiać**, nie przepisywać poleceń.
- `regulation.bin` jest zaszyfrowany (magic `00 00 00 00`) — dekoduje go `ParamCrypt` w soulstruct, nie ręcznie.
- WitchyBND: `unpack <plik>` działa; inne wierzchy nie odpowiadają (brak `--help`).
- W Paramdex występują pola z `RemovedVersion` — **trzeba je pominąć** (2 pola w `EquipParamWeapon`).
- Pola bitowe (`Def="u8 nazwa:1"`) **pakują się do wspólnych bajtów** — nie liczyć ich jako osobnych kolumn.
- DSR używa DCX z nagłówkiem `'DCX\0'` + wewnętrznym `'DCS\0'`/`'DFL\0'` (wariant `Dcx\0` z blokami zlib).

**Podejście zmienione (dyrektywa użytkownika):** nie analizować bajtów `.param` ręcznie ani nie liczyć bitfields na piechotę — użyć gotowej biblioteki (`soulstruct` / SoulsFormats) albo pracować na XML/JSON.

## 2. Wygenerowane narzędzia (`C:\Users\nemos\workspace\ds1-elden-port\tools\`)

| Plik | Rola | Status |
|---|---|---|
| `dcx.py` | dekoder DCX (zlib bloki, `Dcx\0`/`DFL\0`/`Dcx\1`/`Dcx\2`) | działa |
| `bnd.py` | DCX + BND4 read/write + szkielet parsera PARAM | działa częściowo (PARAM do poprawy) |
| `probe.py` | rozpoznanie formatu pliku (magic → DCX/BND4) | działa |
| `fsparam.py` | parser FSParam (DS1 i ER wariant) | **do zastąpienia** przez soulstruct |
| `paramdef.py` | czytnik definicji kolumn z Paramdex XML (`Def=...`, `RemovedVersion`) | działa, przydatny jako referencja |
| `sizes.py` | dopasowanie rozmiaru wiersza do definicji | diagnostyczne |
| `oracle.py` | oracle kolejności kolumn (sortId/behaviorVariationId) | diagnostyczne |
| `probe_er.py` | sonda nagłówka ER `.param` | działa |
| `wbcli.py` / `run_witchy.py` | wrapper na `WitchyBND.exe` (subprocess) | działa |

Dane: `work/er/regulation-bin/` (195 `.param`), `work/er/regulation.bin` (kopia), `analysis/` (pusty), `docs/` (pusty).

## 3. Dokładny punkt zatrzymania

**Zatrzymano na:** czytaniu źródła `soulstruct.base.params.ParamCrypt.ParamCrypt` (polecenie odrzucone przez użytkownika) — czyli tuż przed właściwym wczytaniem `regulation.bin` przez bibliotekę.

**Zadanie na jutro (kolejność):**
1. Przeczytać `ParamCrypt` + `GameParamBND` w `soulstruct` i **wczytać `work/er/regulation.bin`** (ER) → wyeksportować potrzebne tabele do **JSON/XML** (nie binarne `.param`).
2. Tabele docelowe dla etapu 1: `EquipParamWeapon` (poise/weight), `EquipParamProtector` (poise), `NpcParam` (poise bossów), `AtkParam_Npc`/`AtkParam_Pc` (obrażenia, hitboxy), `SpEffectParam` (efekty: guard break, poise damage), `BehaviorParam` (ID wariantów ataku), `ChrModelParam`.
3. To samo dla **DSR** (`param/GameParam/GameParam.parambnd.dcx` + `paramdef/paramdef.paramdefbnd.dcx`) przez `soulstruct` (moduł `dark_souls_dsr`).
4. **Skrypt ekstrakcji** (`tools/extract_lists.py`): wypisać listę wszystkich broni (z poise) i listę bossów (z poise/HP) do zmodyfikowania — z DSR i z ER, do porównania.
5. **PLAN_PROJEKTU.md**: etapy + wykaz modyfikowanych zmiennych (poise → posture-break, wagi, obrażenia pozy, stamina, scaling).

**Nie robić (bez potwierdzenia):** żadnych zapisów do `F:\SteamLibrary\...\DARK SOULS REMASTERED` ani `ELDEN RING\Game`.

**Do ustalenia z użytkownikiem:** docelowy format pośredni (JSON vs XML) i czy w ogóle konwertować ER do XML, skoro ustalono „zostawiamy ER w `.param`”.
