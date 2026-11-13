# PLAN_PROJEKTU — Movement z Elden Ringa w Dark Souls Remastered

Stan na 2026-11-13. Skrócona wersja: tylko to, co jest aktualne. Pełna historia, dowody z testów i stare migawki: `docs\archive\PLAN_PROJEKTU_2026-11-13.md` (91 KB, czytać grepem) i `docs\archive\RAPORT_NOC_2026-11-13.md`. Starsze: `docs\archive\`.

**Kierunek:** jeśli port się sprawdzi, projekt idzie w stronę remaku DS1 na silniku DSR. Małe kroki, każdy testowany w grze. Mechaniki obowiązkowe: przewrót, skok, sprint, anulowania w stylu ER, picie w ruchu, animacje ruchu. Opcjonalnie: kucanie, guard counter.

## 0. Zasady

1. **Gotowe > własne.** Własny kod tylko tam, gdzie nie ma narzędzia (DLL z hookami, małe skrypty).
2. **Formaty bibliotekami.** SoulsFormats (`work\scratch\sf\pub`, most `tools\sfbridge.py`) dla TAE/ESD/BND/DCX; HKX przez soulstruct-havok (`tools\havokbridge.py`). Bez własnych parserów.
3. **Nic nie trafia do katalogu gry** (`F:\SteamLibrary\steamapps\common\DARK SOULS REMASTERED\`). Mod ładujemy z `dist\mods\` przez Mod Engine 2.
4. **Najpierw test w grze, potem dalej.** Wynik testu zapisywać tutaj.
5. **Migawkuj dobre stany** (`work\`) i wracaj do nich zamiast dokładać poprawki po regresji.
6. **Pobieranie tylko z GitHuba** do `toolsy\`, bez instalatorów.
7. **Python do plików**, bez heredoców. **PowerShell:** wieloliniowy `.Replace` z "`n" zawodzi na CRLF — Edit albo `[IO.File]`.
8. **`gemini\`** — strefa robocza Gemini CLI, nic nie scalać automatycznie.
9. **Po stabilnym stanie proponuj migawkę i kolejne wydanie** (`build_release.ps1 -Version x.y`) — prośba gracza.
10. **Git:** e-mail autora = noreply GitHuba (ustawione globalnie); repo jest **publiczne** — żadnych sekretów, plików gry, logów ani dużych binariów. Historia przepisana 2026-11-13 (zmiana e-maila): identyfikatory commitów w archiwum są stare, przekład w `work\commit_map_email_rewrite_2026-11-13.txt`, kopia sprzed: `work\repo_before_email_rewrite_2026-11-13.bundle`.

## 1. Stan repo i wydań

- **Wydanie v1.2** (2026-11-13, GitHub Latest, `dist\release\ER-Inspired_DSR_Remake_v1.2.zip`): zbudowane z gałęzi `artorias-work` z `/DER_DIAG=0`. Nowe: aktualizacje z launchera, darmowy sprint poza walką, `HitCancelsItem`, wolny chód przy duszach / człowieczeństwie, poprawka limitu przy ciągu łyków, przewrót z kolejki z kierunkiem, przewrót przy puszczeniu dla gałki po skosie, tempo halabard. **Paczki nie uruchamiano w grze**; przewrót po skosie nie był testowany.
- **Gałęzie:** `artorias-work` (= v1.2 + plan) jest przed `main` (`21e5fb6`). `main` ma tylko stan przetestowany przed sesją 2026-11-13 popołudnie; fast-forward `artorias-work` → `main` po teście gracza pkt 1 z §5. Lokalnie są jeszcze `night-2026-11-13` i `stamina-free` (scalone, do usunięcia).
- **Repo:** `Contingens1/ER-Inspired_DSR_Remake`, publiczne od 2026-11-13 (wymóg updatera).

## 2. Co działa (przetestowane w grze)

| Mechanika | Jak | Źródło |
|---|---|---|
| Skok z miejsca / marszu / sprintu (J lub L3) | DLL wstrzykuje żądanie (`ctx+0xAE`); 901 pion, 902 krótki, 900 sprint (ER 202030 / 202000 / 202020). JT27 do końca wybicia, kolizja z mapą wyłączona na przysiad. | `tools\add_jump_anims.py`, `make_jump_variants.py`, `er_engine.cpp` (`AirMomentumTick`, `AirControlTick`, `SetMapHit`) |
| Ataki z wyskoku (v2.9, WSTRZYMANE) | Podmiana R1/R2 w skoku na zamach ER (3700/3710/4700/4710), lądowanie ID+1/ID+2, recovery w czasach ER, kolejkowanie kliku. Znana wada: lekki teleport i przeskok pozy przy dotknięciu ziemi. Właściwa droga (niezaczęta): ustawiać czas animacji wprost (pole w AnimData). Migawka `work\*.JUMPATK_V29.*`. | `tools\add_jump_attacks.py`, `open_air_attack.py`, `jump_attack_table.h` |
| Przewrót 360° przy namierzeniu | Własny OmniRoll: `+0x94..0x96` → `+0x93` z kierunkiem gałki, hook `0x2BB150` trzyma yaw 0,5 s. Przewrót z kolejki (np. po trafieniu) bierze kierunek gałki z chwili startu (do 4,5 s, `kOmniQueuedMaxMs`). `[Roll] OmniRoll=1`. | `OmniRollPostInput`, `OmniRollOnPlayAnim` |
| Przewrót przy puszczeniu przy namierzeniu | DLL odkłada przewrót do puszczenia klawisza (próg gry 400 ms, decyzja gracza: zostaje). Od v1.2 także dla wciśnięć z gałką po skosie przód–bok (NIE testowane). `[Roll] LockOnSprint=1`. | `LockOnSprintPostInput` |
| Bufor klawisza uniku | Klawisz bez kierunku czeka 250 ms (hook `0x1A46B0`); klawisz uczony do `bin\er_engine_rollkey.txt`. `[Roll] RollBuffer=1`. | `RollPressDetour`, `RollBufferTick` |
| Przewroty i backstepy z ER | HKX 700/710/720/730 = ER 27100/27110/27120/27130; okna przerwań per akcja z ER, `ActivateJumpTableEarly` 0,1 s przed oknem (unik JT26 dokładnie na oknie). | `python tools\roll_cancel_er.py --anims 700 701 702 703 710 711 712 713 720 721 722 723 --dodge-lead 0` |
| Estus i przedmioty w ruchu | Łatany vanilla ESD (picie na górnej części ciała) + TAE 7585–7589, 7500, 7501 (JT37 zamiast JT7, okna przerwań ER). Wolny chód: osie do 0,45, zdejmowany 0,3 s po rozpoczęciu odkładania; gaszenie sprintu i odskoku. Trafienie (2000–2099 na warstwie 11) kończy animację przedmiotu (`[Items] HitCancelsItem=1`). | `tools\patch_vanilla_esd.py`, `apply_estus_walk.py`, `DrinkActive`, `CapAxis`, `ItemUpperOnPlayAnim` |
| Darmowy sprint poza walką | Flaga gry „bez zużycia wytrzymałości" (`chr+0x524` bit `0x400`) tylko w klatkach sprintu bez innej akcji. „Walka" = namierzenie, utrata HP w 8 s, atak w 5 s. **Od 2026-11-13 (build dev, NIE testowane w grze):** także wróg w promieniu 40 m ze stanem AI „walka" (3) — `ScanEnemyAggro` co 250 ms; log `stamina: enemies in battle state N (nearest X m), searching M, enemies scanned K` i `combat (enemy aggro)`. `[Stamina] FreeOutOfCombat=1`. | `er_engine.cpp` (`stamina: …` w logu) |
| Tempo ataków | Prędkość animacji odcinkami, nigdy wolniej: zamach max ×1,35, końcówka max ×2 (a32/a35 ×1,5); halabardy (a38) z regułą „nigdy wcześniej niż ER". | `tools\gen_attack_speed_table.py` → `attack_speed_table.h` |
| Kamera przy namierzeniu | `LockCamParam` z ER (dystans 3,8, FOV 48, wysokość 1,45). Nie uruchamiać ponownie na pliku moda. | `tools\port_er_lockcam.py` |
| Aktualizacje (v1.2) | Launcher woła `setup\Update.ps1`: GitHub API `releases/latest`, pytanie, pobranie zipa (rozmiar + sha256), kopia do `_backup\v<stara>`, podmiana `bin\`, `files\`, `setup\`; zostają ustawienia z ini, launcher, ścieżka ME2. `[Update] CheckForUpdates=1`. Test end-to-end z GitHuba OK (kopia 1.1 → 1.2). | `native\er_engine\setup\Update.ps1`, `build_release.ps1` |

## 3. Znane błędy i niedociągnięcia

- **Zawieszenie postaci (najważniejszy otwarty błąd, przyczyna NIEUSTALONA):** po przewrocie (raz złapane: 710 kończy się normalnie) postać stoi bez animacji na warstwie 7 przez kilka sekund mimo wychylonej gałki, na ziemi; kończy je trafienie. F9 `ForceEndPlayerAnim` nie pomaga (nie ma czego kończyć). W buildzie dev jest sonda `HangProbeTick` (wpis `HANG probe: frozen …` + `hang diff <region>+0xNNN`); daje fałszywe alarmy 0,6–0,9 s (próg `kHangAfterMs` = 600, ew. podnieść do 1200). Prawdziwe zdarzenie: `hit anim L11 -1`, czas ≫ 1 s. Kandydat: zgody akcji `ActionCtrl+0x1A0..0x1B7` (= `PlayerCtrl+0x520..0x537`).
- Ataki z wyskoku: szarpnięcie przy lądowaniu (wyżej); katana i zwykły atak toporem na animacjach zastępczych; brak R2 z wyskoku w grupie 33, brak grupy 42 (pięści).
- Skok: ślizganie po lądowaniu; przeskok rąk z bronią 900 → 1550 (warstwy 8/24); 2–4 klatki zwolnienia przy zeskoku z półki ze sprintu.
- Blok tarczą w sprincie wygląda nienaturalnie (animacja sprintu ER na górze ciała).
- Sprint przy namierzeniu tylko w przód (jak vanilla).
- Estus: broń widoczna w ręce przy piciu, mignięcie w marszu.
- Darmowy sprint: wróg goniący, ale nienamierzony i bez trafienia, nie liczył się jako walka — poprawka przez stan AI wroga czeka na test (§2).
- Pad (DualSenseX → X360) bywa ignorowany także bez ME2 i DLL — poza zakresem.

## 4. Pliki, build, migawki

- **Kod DLL:** `native\er_engine\er_engine.cpp` (+ generowane `jump_attack_table.h`, `attack_speed_table.h` — nie edytować ręcznie). Dev: `native\er_engine\build.bat` (`ER_DIAG=1`; gra musi być zamknięta; ostrzeżenie `vswhere.exe` nieszkodliwe). Release: `powershell -ExecutionPolicy Bypass -File native\er_engine\build_release.ps1 [-Version 1.2] [-Repo owner/name]` — DLL z `/DER_DIAG=0` (sprawdzane), paczka + zip, test `Setup.ps1` i test aktualizacji z lokalnego zipa. Wydanie na GitHub: `gh release create vX.Y <zip> --target <pełny SHA> --notes-file …` (opis po polsku, pokazywany w oknie aktualizacji, pierwsze 700 znaków).
- **Szablony paczki:** `native\er_engine\setup\Setup.ps1` (okno „konfiguracja", launcher), `setup\Update.ps1`, `README_release.md` (placeholdery `{VERSION}`, `{REPO}`, `{EXE_SHA256}`).
- **Mod dev:** `dist\mods\c0000_er_engine\` — `files\chr\` (anibnd gracza, `c0000.esd.dcx`), `files\param\GameParam\` (lockcam), `bin\er_engine.dll` + `er_engine.ini` (ini nie jest w repo), start `launch_er_engine.bat` (offline, ME2 z `toolsy\ModEngine2`).
- **Log (dev):** `dist\mods\c0000_er_engine\bin\er_engine.log`; bufor 6000 linii × 240 znaków, F8 = znacznik + zrzut. Diag: F5 OmniRoll, F6 bufor uniku, F7 rozpęd w skoku, F8 znacznik, F9 `ForceEndPlayerAnim`.
- **Migawki (folder `work\`; powrót = skopiować `files\`, `bin\` → `dist\mods\c0000_er_engine\`, `native\` → `native\er_engine\`, `tools\` → `tools\`):** `V13_STAMINA\` (V12 + darmowy sprint; ostatni pełny stan przed zmianami DLL z 2026-11-13 popołudnie), `V12_ITEMS\`, `V11_ROLLS\` (= v1.1). DLL z 2026-11-13: `DLL_PROBE_2026-11-13\`, `DLL_ITEMHIT_2026-11-13\`, `DLL_QUEUEDROLL_2026-11-13\`. Ataki z wyskoku: `*.JUMPATK_V29.*`. Brak migawki stanu v1.2 poza samą paczką w `dist\release\` — zrobić `work\V14_…` po teście.
- **Dokumentacja:** `docs\weapon_groups_dsr_er.md` (grupy ataków DSR ↔ ER), `docs\er_anim_a000.md` (72 KB, tylko grep), `docs\ref_DSR-Gadget_DSROffsets.cs`.

## 5. Lista zadań

1. **Test gracza (zaległy):** przewroty po skosie przód–bok przy namierzeniu; Artorias 3019 z bliska (okno trafienia wypadu od 2,00 s; pośrednio np. 2,07 s); przy okazji zwykła gra na paczce v1.2. Po akceptacji: fast-forward `main`, migawka `work\V14_…`.
2. **Zawieszenie** (§3): przy następnym wystąpieniu F8, porównać `hang diff` z kilku zdarzeń, potem poprawka.
3. **Artorias, drobne** (§6): szarża 3027 przelatuje za gracza (`--rm-scale 1003027:…`); 3026 wyłączony.
4. **Skok — wygląd:** ślizganie po lądowaniu (wygaszać rozpęd albo dopasować animację); 900 → 1550 (podmiana na 906 na warstwach 8/24 w `PlayAnimDetour`); zwolnienie z półki (skrócić JT27 w 900 albo dosuwać pozycję).
5. **Blok tarczą w sprincie:** najpierw sprawdzić vanilla; opcje: ignorować żądanie bloku w sprincie / blok przerywa sprint / osobna animacja górnej części ciała.
6. **Sprint w bok i w tył przy namierzeniu** (większe; zgoda gracza, że warto): Ghidra — czytelnik `ctx+0x1E4` i warunek kierunku; co obraca postać do celu; hook.
7. **Darmowy sprint — test stanu AI wrogów:** podejść do mobów bez namierzania; w logu `stamina: enemies in battle state …` ma rosnąć, gdy mob zauważy gracza, i spadać, gdy zgubi. Do ustalenia: czy liczyć też stan 2 („szukanie"), czy 40 m to dobry promień, czy liczba `enemies scanned` jest sensowna (0 = zły offset listy postaci).
8. **Ataki z wyskoku** (wstrzymane): czas animacji lądowania wprost; 3800/3810; pętla spadania 31060; katana a029 na szkielet DSR; R2 w grupie 33, grupa 42.
9. **Estus — chowanie broni (zaparkowane):** ER robi to eventem TAE 710 `HideEquippedWeapon`; DSR — w animacji (kość `R_Weapon`).
10. **Do zbadania (pomysły gracza):** recovery po powaleniu DSR vs ER; mnożniki obrażeń ataków z wyskoku; ignorowanie kolizji w fazie wybicia skoku; dynamic poise (najniższy priorytet); modularny mod (gracz / bossowie osobno, przełączniki w ini i w `Setup.ps1`).
11. **Boss c2232 (Asylum Demon, wstrzymany):** ER 3015 (tupnięcie, obrażenia z fali), 3016 (brak w `c4810.anibnd`), fala przy 3008, mniej kurzu; synchronizacja fali (`tools\boss_tae_sync_hits.py`) niesprawdzona w grze. Paczka `dist\mods\boss_asylum_test\`.
12. **Przed publicznym wydaniem:** zgoda autorów Player Animations Repository (animacje w `files\chr\*.anibnd.dcx`); README każe grać offline — mod nie ma własnej blokady sieci.

## 6. Artorias (c4100) z Nightreign — paczka testowa

Cel gracza: Artorias jako szczytowy boss — szybszy, trudniejszy do unikania, dopasowany do nowego ruchu; mniej doskoków niż w NR (zamknięta arena). Nie jest częścią wydań.

- **Paczka:** `dist\mods\bossy_nightreign\launch_nr_artorias_v2.bat` (`files_c4100_v2\chr\c4100.anibnd.dcx` + `files_c4100_v2\script\m12_01_00_00.luabnd.dcx`). Ładuje DLL dev głównego moda.
- **Stan (przetestowany, „bardzo dobrze"):** nowe ataki NR jako własne numery: 3026 (3026), 3027 (3027), 3028 (3028), 3030 → 3017, 3031 → 3018, 3032 → 3019, 3033 → 3024, 3034 → 3025. Łańcuchy: 3017 → 3018 → 3019, 3004 → 3024, 3007 → 3025, 3027 → 3028, 3003 → 3009 → 3026 (3026 wyłączony: `USE_3026 = False`, bez skalowania doskoku NR mija). Nowe ruchy przez całą walkę (bez fazy). Doskoki wyprostowane (rzut na kierunek netto) i skrócone; okna obrotu `SetTurnSpeed` i blokady JT7 z NR.
- **AI:** `python tools\make_artorias_ai.py` (edycje na zdekompilowanym skrypcie DSR → `work\boss_ai\410000_battle.nr_v2.lua`); łańcuchy z kątem powodzenia 180°; akcja 14 (3017…) z bliska NIE blokowana (decyzja gracza).
- **Odtworzenie anibnd:** `python tools\nr_boss_port.py --nr c7720 --dsr c4100 --tag _v2 --pair 1003026:3007:3026 --pair 1003027:3005:3027 --pair 1003028:3000:3028 --pair 1003030:3001:3017 --pair 1003031:3011:3018 --pair 1003032:3004:3019 --pair 1003033:3014:3024 --pair 1003034:3011:3025 --install --nr-turn --nr-ai --extra-hits --jt 3004:23:2.067 --jt 3007:23:2.433 --rm-scale 1003030:0.45 --rm-scale 1003033:0.5 --rm-scale 1003028:0.6 --rm-scale 1003032:0.6 --rm-straighten 1003030 1003031 1003032 1003033 1003034 --hit-start 3019:2.13:2.0 --reuse`
- **Narzędzia analizy:** `python tools\enemy_probe_report.py [--detail 3017 3018 3019]` (z logu sondy `enemy <ctx> anim …`: odległość, kąt, droga, trafienia po spadku HP gracza); `python tools\nr_rootmotion_profile.py c7720 <id…>`; `python tools\nr_timing_table.py c4100 c7720`; `python work\scratch\rm_check_ported.py c4100_v2 <id…>`.
- **Punkty powrotu:** `work\ARTORIAS_V2_TURNLOCK\` (stan przed `--hit-start`), `ARTORIAS_V2_STRAIGHT2\`, `ARTORIAS_V2_STRAIGHT1\`.
- **Ustalenia:** NR c7720 (AI 772000); ataki 3000–3014, 3023 to te same klipy co DS1. `enemyCommon.esd` przyjmuje ataki 3000–3029. NR skaluje doskoki do celu zdarzeniem TAE 760 (`RootMotionMultiplierEX`) — DSR go nie ma (odpowiednik wymagałby DLL). U wrogów JT7 też blokuje obrót. Inne bossy NR do portu: Gaping Dragon c5260 ↔ c7700, Centipede c5200 ↔ c7710; Capry brak w plikach.

## 7. Offsety i funkcje (Ghidra)

Cel: `DarkSoulsRemastered.exe`, SHA-256 `A45AAA36…`. Arxan szyfruje część kodu — analiza na zrzucie `work\ghidra\DSR_decrypted.exe` (projekt `DSR_dec`), dekompilacja w `work\ghidra\decomp\`. Headless: `JAVA_TOOL_OPTIONS=-Duser.name=nemos`, `-readOnly`.

**Hooki:** PlayAnim RVA `0x37A040` `(ctx, out, anim, layer, a5, a6, a7)`; handler wejścia `0x396860`, w nim `FUN_140398920(ctx, dt, p3)` = unik i skok; `0x1A46B0` akcja `0x5C` (unik wciśnięty), `0x1A4610` akcja `0x5B` (trzymany); krok fizyki `0x2BB150`. Prologi odszyfrowane przez Arxana (`WaitForGameReady`): `0x396860`, `0x37A040`, `0x398E4F`, `0x2BB150`.

**Warstwy animacji gracza:** 7/23 całe ciało; 5/17 góra ciała (ESD slot 4); 8/24 spadanie; 6/18 przedmioty (picie 7585–7589, 7500, 7501); 11/26 reakcje na trafienie (2000–2099; 2026 = powalenie 4,1 s, unik od 3,0 s).

**Obiekt gracza:** `PlayerIns` = `[base+0x1C77E50]`; `+0x68` → ChrMapData (`+0x48` z DSR-Gadget błędny); `ChrMapData+0x18` → AnimData, `+0xA8` prędkość animacji; `ChrMapData+0x28` → pozycja (`+0x04` yaw, `+0x10/14/18` XYZ; przód = `(-sin, -cos)`); `ChrMapData+0x104` bit `0x10` DisableMapHit. HP `PlayerIns+0x3E8`, wytrzymałość `chr+0x3F8`, flagi `chr+0x524` (bit `0x400` = bez zużycia wytrzymałości). Cel namierzenia `chr+0x1A0`; `p3+0x21D` = 1 ruch swobodny, 0 namierzenie. Właściciel ctx PlayAnim: `*(ctx+0x10)` → `+0x68` → `+0x28` (działa też dla wrogów).

**Postacie i AI (Ghidra 2026-11-13, z bindingów Lua AI):** `WorldChrMan` = `[base+0x1C77E50]`: `+0x28` int liczba bloków mapy, `+0x30` bloki co `0xE8`; blok `+0x48` int liczba, `+0x50` wpisy co `0x38`, wpis `+0x00` = `ChrIns*` (`FUN_140371360`, `FUN_14033ec10`); drugi zbiór pod `+0x38`/`+0x40` (gracze). vtable `EnemyIns` = RVA `0x1322E68`, `PlayerIns` = `0x13251F0`. AI wroga: `*(chr+0x570)` (vtable +0xF8) → `+0x230` = obiekt AI → `+0x30` → `int +0xE0`: 0 spokój, 1 czujność (`IsCautionState`), 2 szukanie (`IsFindState`), 3 walka (`IsBattleState`). Cel AI: `FUN_1405c9070(ai, typ)` (typy <10 → `FUN_14061d860(ai+0x30, 0, typ)`). Skrypty: `native\ghidra_scripts\run_script.ps1 <Script.java> <args>` (`FindStringRefs`, `InspectAddrs`, `VtableOf`, `DecompileFuncs`).

**Kontroler fizyki** (`ChrMapData+0x28`): `+0x32` na ziemi, `+0x33` zbocze, `+0x38` `hkpCharacterProxy*` (prędkość `proxy+0x60`), `+0x6D` zachowaj prędkość w powietrzu, `+0xD0` prędkość z poprzedniej klatki, `+0xF0` mnożnik XZ w spadaniu (0,98), `+0x144` prędkość obrotu, `+0x1B0/1B4` czas w powietrzu, `+0x1E4` skala grawitacji, `+0x1F0` swobodne spadanie, `+0x1F2/1F4` grawitacja wył., `+0x1F3` = 1 od wybicia do lądowania. Globalne: `0x141a2ae54` 6,0 m/s XZ, `0x141a2ae58` 1,0 (Y w górę), `0x141a2ae5c` 50 (Y w dół). Łańcuch: `FUN_140379880` → `FUN_1402bb020` → `FUN_1402bb150` → `FUN_1402bbe40` (root motion lub bezwładność + grawitacja → proxy).

**Wejście (ctx):** `+0x93..0x96` unik przód/tył/lewo/prawo; `+0x8E` odskok; `+0xAE` skok; `+0x1C4` bit żądania; `+0x224` kolejka akcji (−1 pusta, indeks względem `+0x84`); `+0xF0 + 4·(flaga−0x84)` czas żądania; `+0x260` czas trzymania uniku; `+0x1E4` = 1 sprint (po progu `0x1A2C0A0` = 0,4 s); `+0x324/+0x328` timer i flaga odskoku (0,103 s); `+0x329` unik przy puszczeniu; ataki `+0x84`/`+0x8B` R1, `+0x89` R2. `g_axis[0]` > 0 = przód, `g_axis[1]` > 0 = prawo; osie ograniczone przez DLL gra widzi jako „bez kierunku". Przy namierzeniu vanilla: bok / tył = przewrót przy wciśnięciu, przód = przy puszczeniu. `g_playerAnimCtx = g_inputCtx + 0x3A0`.

**ESD:** spadanie 1550 przez `FUN_140385550(ctx, anim, slot, …)`; sloty → warstwy w `0x14132d000` / `0x14132d030`.

**JumpTable (TAE, gracz i wrogowie):** JT1 klawisz ataku, JT4 przerwanie atakiem, JT7 blokada obrotu (też u wrogów), JT11 przerwanie ruchem, JT23 okno combo bossa, JT26 przewrót, JT27 Ignore Gravity, JT51 Disable Fall Motion, JT66 Special Transition, JT78/79/86 okna AI. `ActivateJumpTableEarly`: pierwszy int16 = numer JT; przerwanie działa 0,02–0,06 s po starcie tego zdarzenia (realny czas), przy zmianie okien przesuwać oba. TAE typ 1 = trafienie (int w +8 = zachowanie ataku), typ 224 = `SetTurnSpeed` (°/s). Pliki gracza: SDKV `20160100` w modzie, Havok 2015.

**Nie powtarzać:** pętla 906 na warstwie 7; przechwytywanie `-1`; lądowanie z warstwy 8; rozpęd przez zapis pozycji; JT51/JT66 w skoku; przesuwanie okien JT jako sposób na tempo ataku; flaga uniku wstawiana po handlerze (bufor V1–V3); F9 jako leczenie zawieszenia.

## 8. Czytanie logu (dev)

- Ostatnia sesja = od ostatniego `pierwsza klatka gry`. Linie `fiz +`, `enemy 0`, `pad-diag` są liczne — filtrować.
- Animacje: `L7 ctx=… anim=720 … (gracz)`; `-1` na L7 = gra zakończyła animację. `unik-stan`: `namierzenie=0` = namierzony, `trzymanie` = `+0x260`, `odskok=a/b` = `+0x324/+0x328`, `przy-puszczeniu` = `+0x329`.
- Wpisy: `drink stage: A -> B after X ms`, `drink: backstep request dropped`, `lock-on sprint: …`, `omniroll: armed / commit … (queued roll)`, `item: hit reaction N during item anim M`, `stamina: …`, `HANG probe: …`, `enemy <ctx> anim N +T ms …` (boss i gracz mają różne ctx; raport wybiera bossa sam).
