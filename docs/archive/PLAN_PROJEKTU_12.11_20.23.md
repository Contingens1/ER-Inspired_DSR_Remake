# PLAN_PROJEKTU — Movement z Elden Ringa w Dark Souls Remastered

Data: 2026-11-12 · Ostatni zatwierdzony stan: **V08** (migawka `work\er_engine.V08_STABLE.*`) · W modzie (`dist\`) i w `native\` jest teraz **V08 + ataki z wyskoku v2.2** (niezatwierdzone, §4) · Historia i szczegóły: `docs\ARCHIWUM_BADAN.md`

**Kierunek długoterminowy:** jeśli port się sprawdzi, projekt idzie w stronę remaku DS1 na silniku DSR. Do tego czasu: małe kroki, każdy testowany w grze.
**Mechaniki obowiązkowe:** przewrót, skok, sprint, anulowania w stylu ER, picie w ruchu, animacje ruchu.
**Opcjonalnie:** kucanie, guard counter. Parry już jest w DSR.

## 0. Zasady

1. **Gotowe > własne.** Własny kod tylko tam, gdzie nie ma narzędzia: DLL z hookami do exe i małe skrypty sklejające.
2. **Formaty czytamy bibliotekami, nie ręcznie.** SoulsFormats (`work\scratch\sf\pub`, most `tools\sfbridge.py`) to jedyna warstwa I/O dla TAE/ESD/BND. Nie piszemy własnych parserów TAE/HKX.
3. **Nic nie trafia do katalogu gry.** Mod ładujemy z `dist\mods\` przez Mod Engine 2 (wspiera DSR).
4. **Najpierw test w grze, potem dalej.** Każdy etap kończy się testem offline w DSR.
5. **Migawkuj dobre stany i wracaj do nich** zamiast dokładać poprawki po regresji.
6. **Pobieranie bez pytania tylko z GitHuba** do `toolsy\`, bez instalatorów. Zasoby ER tylko jako referencja albo przez skrypty działające na własnych plikach.
7. **Skrypty Pythona zapisuj do plików** i uruchamiaj stamtąd. Heredoc w bashu psuje apostrofy i ukośniki.
8. **PowerShell:** wieloliniowy `.Replace` z "`n" zawodzi przez CRLF. Używać Edit albo `[IO.File]` z `[Environment]::NewLine`.

## 1. Stan V08 — co działa (przetestowane w grze)

| Mechanika | Jak | Źródło |
|---|---|---|
| Skok z miejsca / z marszu / ze sprintu (J lub L3) | DLL wstrzykuje żądanie (`ctx+0xAE`); wariant wg stanu ruchu: 901 pion, 902 krótki, 900 sprint. Animacje z ER (900 ← 202030, 901 ← 202000, 902 ← 202020) z root motion w osi Y. JT27 Ignore Gravity do końca wybicia. Kolizja z mapą wyłączona na przysiad (350 ms). Skok z półki w dół: fizyka zatwierdzona (v0.7). | `tools\add_jump_anims.py`, `tools\make_jump_variants.py`, `er_engine.cpp` (`AirMomentumTick`, `AirControlTick`, `SetMapHit`) |
| Przewrót w 8 kierunkach przy namierzeniu | DSROmniRoll (cudzy mod, Nexus DSR #1378), ładowany przed naszym DLL | ModEngine2 |
| Unik z buforem klawisza (V4) | Hook `FUN_1401a46b0` (RVA `0x1A46B0`, akcja `0x5C`): klawisz uniku bez kierunku czeka do 250 ms na kierunek. Klawisz uczony z udanych uników (`bin\er_engine_rollkey.txt` = `6`, XBUTTON2). TAE 710 wariant A (blokada obrotu JT7 do 2,33 s). | `er_engine.cpp` (`RollPressDetour`, `RollBufferPre`, `RollBufferTick`) |
| Picie estusa w ruchu, ze skręcaniem | ESD bez blokady ruchu, picie na górnej części ciała | Simple Estus Walking (cudzy, `c0000.esd.dcx` bez zmian) + `tools\apply_estus_walk.py` |
| Wolny chód w trakcie picia | DLL ogranicza osie ruchu (`0x1A3700` / `0x1A3750`) do 0,45 podczas animacji picia | `er_engine.cpp` |
| Tempo ataków R1/R2, z biegu, z przewrotu | DLL zmienia prędkość animacji odcinkami; nigdy nie zwalnia | `tools\gen_attack_speed_table.py` → `native\er_engine\attack_speed_table.h` (129 animacji, 14 grup) |
| Kamera przy namierzeniu | Wartości ER w `LockCamParam` (patrz tabela niżej) | `tools\port_er_lockcam.py` |

**Limity tempa ataków:** zamach do trafienia max ×1,35; końcówka do okna następnej akcji max ×2; grupy ciężkie a32 i a35: końcówka max ×1,5.

**LockCamParam (DSR → ER):** `camDistTarget` 4.0 → 3.8; `camFovY` 43 → 48; `chrOrgOffset_Y` 1.42 → 1.45; `lockRotXShiftRatio` 0.6 → 0.45. Pozostałe wiersze (bossowie, ciasne miejsca) dostają tę samą zmianę względną. Skrypt nie uruchamiać ponownie na istniejącym pliku moda.

**Znane niedociągnięcia (wygląd, nie fizyka):**
- lekkie ślizganie postaci przy lądowaniu po skoku (także po sprincie);
- przeskok modelu rąk z bronią przy przejściu skok → spadanie (900 → 1550 na warstwach 8/24);
- blok tarczą/bronią w sprincie nie jest blokowany, górna część ciała wygląda absurdalnie (animacja sprintu z ER);
- estus: broń zostaje w ręce (patrz §5), mignięcie broni przy piciu w marszu;
- sprint z półki: 2–4 klatki zwolnienia przed spadaniem.

## 2. Aktywne pliki i migawki (`work\`)

**Aktualna migawka — V08 (skok v0.7 + unik v4 + log w pamięci).** Pliki robocze różnią się od niej o ataki z wyskoku v2.1 (§4); powrót = skopiować wszystkie pozycje poniżej:
- `work\er_engine.V08_STABLE.cpp` → `native\er_engine\er_engine.cpp`
- `work\er_engine.V08_STABLE.dll` → `dist\mods\c0000_er_engine\bin\er_engine.dll` (i `dinput8.dll`)
- `work\c0000.anibnd.V08_STABLE.dcx`, `work\c0000_a00_lo.V08_STABLE.dcx` → `dist\mods\c0000_er_engine\files\chr\`
- `work\c0000_a2x.anibnd.V08_STABLE.dcx`, `work\c0000_a3x.anibnd.V08_STABLE.dcx`, `work\c0000_a4x.anibnd.V08_STABLE.dcx` → `files\chr\`
- `work\jump_attack_table.V08_STABLE.h` → `native\er_engine\jump_attack_table.h`

**Wcześniejsze migawki (powrót w razie regresji):** `JUMP_V07_STABLE`, `V07_DIAG`, `ROLLBUF_V1..V4`, `ROLL_V4_STABLE`, `PRE_MOMENTUM`, `MOMENTUM_V06`, `c0000.anibnd.before_rollA.dcx`, `c0000.anibnd.before_jump_attacks.dcx`, `boss_port\c2232.anibnd.er_before_sync.dcx`.

**Pliki robocze:**
- kod DLL: `native\er_engine\` (`er_engine.cpp`, `jump_attack_table.h`, `attack_speed_table.h`); build: `build.bat` (gra musi być zamknięta, inaczej DLL się nie skopiuje);
- dane moda: `dist\mods\c0000_er_engine\files\` (`chr\c0000.anibnd.dcx`, `chr\c0000_a00_lo`, `chr\c0000_a00_md`, `chr\c0000_a2x/a3x/a4x`, `param\GameParam\GameParam.parambnd.dcx`);
- start: `dist\mods\c0000_er_engine\launch_er_engine.bat` (tylko offline, ModEngine2 z `toolsy\ModEngine2`);
- logi: `dist\mods\c0000_er_engine\bin\er_engine.log`, `toolsy\...\DSROmniRoll\DSROmniRoll.log`;
- boss (Asylum Demon, c2232): `dist\mods\boss_asylum_test\` (launchery `launch_asylum_er*.bat`, `launch_asylum_*_orig*`);
- release: `dist\release\BetterMovementAndEstus_v0.5.zip` (ostatni zbudowany; wersji 0.6 jeszcze nie ma).

**Dokumentacja:** `docs\compact.txt` (ustalenia techniczne), `docs\NOC_2026-11-12.md` (boss, AI w Lua), `docs\PROMPT_ATAKI_Z_WYSKOKU.md`, `docs\ARCHIWUM_BADAN.md`.

**Diagnostyka (tylko przy `ER_DIAG=1`):** F6 bufor uniku wł./wył.; F7 rozpęd w skoku wł./wył. (A/B); F8 znacznik + zrzut bufora logu do `er_engine.log` i 2,5–3 s zapisu wprost; F9 wymuszone `-1` na warstwach 7 i 23 (eksperyment, nie pomaga). Log trzyma 6000 linii w pamięci i zrzuca je dopiero po F8.

## 3. Potwierdzone offsety i funkcje (Ghidra)

Cel: `DarkSoulsRemastered.exe`, SHA-256 `A45AAA36…` (build OmniRoll). Arxan szyfruje część kodu na dysku, więc analiza jest na zrzucie: `work\ghidra\DSR_decrypted.exe` (projekt `DSR_dec`), dekompilacja w `work\ghidra\decomp\`. Ghidra headless wymaga `JAVA_TOOL_OPTIONS=-Duser.name=nemos` oraz `-readOnly`.

**Hooki i wejście**
- PlayAnim: RVA `0x37A040`, sygnatura `(ctx, out, anim, layer, a5, a6, a7)`. Warstwy 7 i 23 to całe ciało.
- Handler wejścia: RVA `0x396860` (DSROmniRoll hookuje go też; nasz hook jest na wierzchu).
- `FUN_140398920(ctx, dt, p3)`: obsługa uniku i skoku (dekompilacja `FUN_140398E4F.c`).
- `FUN_1401a46b0` (RVA `0x1A46B0`): akcja `0x5C` = klawisz uniku właśnie wciśnięty; `FUN_1401a4610` (RVA `0x1A4610`): akcja `0x5B` = trzymany.

**Obiekt gracza**
- `PlayerIns` = `[base+0x1C77E50]`; `PlayerIns+0x68` → ChrMapData (`+0x48` z DSR-Gadget jest dla tego exe błędny).
- `ChrMapData+0x18` → AnimData; `AnimData+0xA8` = prędkość animacji (float). Tempo ataków zmieniamy właśnie tędy.
- `ChrMapData+0x28` → pozycja: `+0x04` kąt, `+0x10` / `+0x14` / `+0x18` = X / Y / Z. Kierunek „przód” = `(-sin(kąt), -cos(kąt))`.
- `ChrMapData+0x104` bit `0x10` = DisableMapHit (wyłączenie kolizji z mapą).
- Kontroler fizyki (`PlayerIns+0x68` → `+0x28`, w DLL `ChrPosData()`):
  - `+0x32` na ziemi, `+0x33` na zboczu;
  - `+0x38` = `hkpCharacterProxy*`; prędkość liniowa = `proxy+0x60` (getter `0x140a79b10`, setter `0x140a79b20`);
  - `+0x6D` „zachowaj prędkość w powietrzu”; `+0xD0` prędkość z poprzedniej klatki;
  - `+0xF0` mnożnik XZ w swobodnym spadaniu (0,98);
  - `+0x1B0` / `+0x1B4` czas w powietrzu; `+0x1E4` skala grawitacji (< 1.0 = jak na ziemi);
  - `+0x1F0` tryb swobodnego spadania; `+0x1F2` / `+0x1F4` grawitacja wyłączona (`+0x1F4` z ESD); `+0x1F3` = 1 od wybicia do lądowania.
- Globalne limity: `0x141a2ae54` = 6.0 m/s na oś XZ (podnoszone do 12 na czas rozpędu w spadaniu), `0x141a2ae58` = 1.0 (Y w górę), `0x141a2ae5c` = 50 (Y w dół).

**Łańcuch fizyki (co klatkę):** `FUN_140379880` (ChrCtrl) → `FUN_1402bb020` → `FUN_1402bb150` → `FUN_1402bbe40` (RVA `0x2BBE40`). Ostatnia wybiera prędkość z root motion lub bezwładność, dodaje grawitację i zapisuje do proxy:
- `+0x1F0 == 1`: prędkość = bieżąca prędkość proxy, obcięta do ±6 m/s XZ, × `+0xF0`, + grawitacja;
- w innym razie (gdy `+0x6D` i nie na ziemi, albo `+0x1F3`): prędkość = `+0xD0`, + grawitacja.

**Komendy ESD:** spadanie 1550 zlecane przez `FUN_140385550(ctx, anim, slot, ...)` z `0x14038dd6e` i `0x14038e137`. Tabela slot → warstwy (`0x14132d000` / `0x14132d030`): slot 4 = warstwy 5/17 (góra ciała), slot 6 = 7/23 (akcja), slot 7 = 8/24 (spadanie).

**Unik i odskok (ctx = obiekt wejścia)**
- `ctx+0x93..0x96`: żądanie uniku (przód/tył/lewo/prawo), flaga `kRollFlag = 0x93`;
- `ctx+0x8E` odskok; `ctx+0xAE` skok; `ctx+0x1C4` bit „jest żądanie”;
- przyciski ataku (z logu zmian ctx, 2026-11-12): `ctx+0x84` i `+0x8B` = R1 trzymany (lewy przycisk myszy), `ctx+0x89` = R2 trzymany; flagi `+0xB9`/`+0xC0` i `+0xBE` idą za nimi z opóźnieniem jednej klatki;
- `ctx+0xF0` licznik czasu żądania (float) = `ctx+0xF0 + 4·(flaga−0x84)`;
- `ctx+0x260` czas trzymania klawisza uniku;
- `ctx+0x324` / `+0x328` timer i flaga odskoku (`DAT_141a2c0b4` ≈ 0,103 s);
- `ctx+0x329` „unik też przy puszczeniu”; próg trzymania `DAT_141a2c0a0`; `DAT_141c78add == 0` = unik przy wciśnięciu;
- `p3+0x21D` = namierzenie (lock-on);
- wytrzymałość: `*(int*)(*(p3+0x10)+0x3F8)`; unik kosztuje ok. 25–30 (95 → 70 → 55 → 30 → 0 → −15);
- unik to animacja `710`.

**Tabela JumpTable w TAE**

| JT | Działanie |
|---|---|
| JT1 | klawisz ataku prawą ręką (w skoku nie kolejkuje kliknięcia sprzed okna JT4) |
| JT4 | przerwanie atakiem prawą ręką |
| JT7 | Disable Turning (unik 710 wariant A: 0,07–2,33 s; usunięty z animacji skoku) |
| JT11 | przerwanie ruchem |
| JT23 | okno combo (bossy) |
| JT26 | przewrót |
| JT27 | Ignore Gravity |
| JT51 | Disable Fall Motion |
| JT66 | Special Transition (po ok. 0,7 s gra zamienia skok w spadanie) |
| JT78 / 79 / 86 | okna AI bossa |

**Pliki gracza w modzie:** nagłówek SDKV `20160100`, gra go czyta. Oryginalne pliki DSR mają `20150100`. DSR używa Havoka 2015, nie 2016.

**Nie powtarzać (cofnięte lub zawodne):**
- pętla w powietrzu 906 na warstwie 7; przechwytywanie `-1`; lądowanie z warstwy 8 w skoku;
- przenoszenie rozpędu przez zapis pozycji (w fazie spadania zapis z `AirControlTick` jest wyłączony);
- dopisywanie JT51 / JT66 do skoku; przesuwanie JT51 / JT66 (wpływa tylko na spadanie 1550, które zleca ESD);
- podmiana spadania 1550 na inne ID w samym skoku;
- przesuwanie okien JumpTable w TAE jako sposób na tempo ataku (dawało 30–80 ms);
- flaga uniku wstawiana po handlerze wejścia (ROLLBUF V1–V3): DSROmniRoll nie widzi wtedy kierunku;
- `ForceEndPlayerAnim` (F9) nie rozwiązuje zawieszenia.

## 4. Ataki z wyskoku — AKTYWNA PRACA (v2.2 w modzie, NIE sprawdzone w grze)

**Uwagi gracza do V08:** brak lądowania (długie przykucnięcie, nieresponsywne, zwłaszcza lekkie bronie); atak zaczyna się za późno i z przeskokiem (koniec dosuwania, początek spadania); trafienie nie jest zgrane z ziemią.

**Jak to działa w ER** (TAE `nuxe\chr\c0000.anibnd.dcx`, nazwy stanów z `c0000.hks`; dekompilacja hks przez Soulstruct nie działa: `Unimplemented opcode`):
- skok (202000/202020/202030): przerwanie atakiem od 0,20 s;
- zamach w powietrzu 31030 / 31230 / 33030 / 33230 (stan `JumpAttack_Start_Falling`): bez ruchu postaci i bez okien przerwań, trafienie ok. 0,37–0,50 s (miecz prosty);
- lądowanie = ID zamachu + 40 (31070 itd., stany `Jump_LandAttack_Normal/Hard`): ten sam ruch na ziemi + wstawanie, trafienie w tym samym czasie co zamach, okna przerwań (miecz prosty: atak 0,83 s, unik 0,93 s, ruch 1,03 s). Wniosek (nie dowód): lądowanie wchodzi w czasie, w którym trwał zamach.
- nie przeniesione: 31060 (pętla spadania), 31071 / 31072 / 31081 / 31082 (lądowania po pętli).

**Jak DSR sam obsługuje atak w skoku** (log z testu 2026-11-12):
- R1 (lewy przycisk myszy, flagi `ctx+0x84` / `+0x8B`) w skoku → własny atak DSR `GG3900` (1H) / `GG4900` (2H); kolejny klik w spadaniu → atak ze spadania `GG3800`; lądowanie → `GG3810` (długie przyklęknięcie). Katana (29) nie ma 3800 i gra bierze `233800`.
- R2 (flaga `ctx+0x89`) w skoku → zwykłe `GG3300` / `GG4300`.
- Gra reaguje tylko na wciśnięcie, które wypadnie w oknie JT4 skoku (najwcześniejszy atak w logu: dokładnie 250 ms). JT1 od 0,00 s **nie** kolejkuje kliknięcia.
- Zlecenie ataku: `-1` na warstwach 7 i 23, potem animacja na 7 i 23 z `a5=0`, `a6` jak w skoku, `a7=0`.

**Stan kodu i danych (v2.1):**
- `tools\open_air_attack.py`: JT4 w skokach 900/901/902 od 0,25 s (root motion skoku przecina poziom startu ok. 0,23 s); JT1 od 0,00 s (bez efektu, patrz wyżej).
- `tools\add_jump_attacks.py`: zamach `GG3700/3710/4700/4710` (ER 31030/31230/33030/33230) ze zdarzeniami ataku DSR przesuniętymi na czas trafienia ER, bez okien przerwań i bez `ActivateJumpTableEarly`, z JT51 na całość. Lądowanie ID+1 (z trafieniem) i ID+2 (bez trafienia, tylko zdarzenia JumpTable; ten sam HKX ER xx070); okna przerwań w czasach ER (ten sam numer JT, inaczej czas JT11).
- Grupy zastępcze (v2.2, `FALLBACK` w skrypcie): plik ER jest używalny tylko, gdy ma 61 ścieżek; inaczej animacja i czasy z pokrewnej grupy ER: katana 29 ← 28 (R2 oburącz ← 23), topór 30 R1 ← 33 (młot), 28 R2 oburącz ← 23. To rozwiązanie zastępcze — właściwe animacje katany wymagałyby przeliczenia plików ER na szkielet DSR.
- Zakres: 54 ataki, 14 grup: 20, 23, 25–30, 32, 33, 35, 36, 38, 43. Brak: R2 w grupie 33 (ataki DSR 3300 / 4300 nie mają zdarzenia trafienia), grupa 42 (pięści; nie była generowana).
- `jump_attack_table.h` (generowany, nie edytować): `{anim, hitMs, swingEndMs, landHit, landFollow, landEndMs}`; `swingEndMs` = koniec trafienia ER + 0,5 s; `landEndMs` = start otwartego `BlendToIdleOrMovementAnim` w lądowaniu ER.
- `er_engine.cpp`:
  1. `AirAttackSubstitute()` w `PlayAnimDetour`, okno 230–1100 ms skoku: 3000/3001/3002/3500/**3900** → 3700; 4000/4001/4002/4500/**4900** → 4700; 3300/3310 → 3710; 4300/4310 → 4710. Tylko ID z tabeli; warstwa 23 powtarza podmianę z warstwy 7 (do 100 ms). Każde zlecenie gry na warstwie 7 kończy stan ataku z wyskoku.
  2. `AirAttackBuffer()` (po handlerze wejścia): klik ataku między startem skoku a 255 ms jest odtwarzany w 255–310 ms (flagi `+0x84`/`+0x8B` albo `+0x89` na 1 i bit `+0x1C4`; przy trzymanym przycisku jedna klatka z 0). Wyłącznik `kAtkBuffer`.
  3. Od ataku lot balistyczny (`AirMomentumTick`) z wektorem ostatniej klatki skoku (`g_jumpV`); pion ograniczony do szczytu zwykłego skoku (`kJumpApex` 1,16 m); grawitacja `kAirAtkGravity` 16 m/s² trzymana przez DLL do lądowania.
  4. `AirAttackTick()`: lądowanie (`+0x32` = 1, `+0x1F3` = 0, grawitacja włączona) → animacja lądowania zlecana przez DLL na warstwach 7 i 23, przewijana ×4,5 do czasu zamachu (`kLandSync`, `kLandSyncSpeed`; musi być < 5, bo `AnimSpeedPtrVia` odrzuca wskaźnik przy wartości ≥ 5); przed trafieniem ID+1, po trafieniu ID+2; zamach skończony w powietrzu → `-1` i zwykłe spadanie gry; bez inputu koniec po `landEndMs`.
  5. Wzlot po wczesnym ataku (v2.2): przez `kAirAtkLiftMs` = 250 ms od przejęcia lotu DLL trzyma `+0x1F3` = 1, dopóki `+0x32` nie spadnie do 0; lądowanie bez wcześniejszego oderwania liczy się dopiero po 350 ms zamachu.
  6. `AirAttackAutoEnd` usunięte.

**Testy w grze:**
- v2 (2026-11-12, katana i inne): gracz — spłaszczony skok przy niektórych broniach, trudna aktywacja (trzeba trafić w okno albo spamować), nadal długie przyklęknięcie. Przyczyna z logu: podmiana nie zadziałała ani razu przy R1, bo 3900/4900 nie było w podmianie; gracz oceniał ataki DSR (3900 → 3800 → 3810). Lądowania z ER i lotu po ataku nikt jeszcze w grze nie widział.
- v2.1 (2026-11-12): podmiana i lądowanie z ER działają (log: `293900 -> 293700`, lądowanie → `293701` / `293702`). Gracz: katana — model postaci się rozpada (szkielet wygięty w lewo); topór gargulca (grupa 30, oburącz) — nadal atak DSR. Przyczyny: (1) pliki katany a029 w repozytorium ER (i `a028_033270`) mają 42 ścieżki z numerami kości ER zamiast 61 ścieżek szkieletu DSR — nieprzeliczone; (2) grupa 30 nie ma w repozytorium zamachu R1 (31030 / 33030), więc nie było wiersza w tabeli; (3) atak w 250 ms skoku (0,31 m nad ziemią): po włączeniu grawitacji silnik uznał postać za stojącą, zgasił `+0x1F3` i wyzerował prędkość („lądowanie” po 15 ms); atak w 297 ms (0,62 m) poleciał poprawnie.
- v2.2: czeka na test.

**Sprawdzone poza grą:** DLL się buduje; TAE a23 3700/3701/3702 ma oczekiwane zdarzenia; kontenery a2x/a3x/a4x: 84/60/12 nowych wpisów HKX bez duplikatów ID; oryginalna gra nie używa ID 37xx/47xx w grupach broni. Z logu: `+0x1F3` = 1 i `+0x32` = 1 w 406 ms skoku.

**Niewiadome do testu:**
- czy gra przyjmie klik odtworzony przez `AirAttackBuffer` (flaga ustawiona po handlerze);
- czy przy aktywnym zamachu (JT51) kolejny klik nadal zleca 3800/3810 — wtedy trzeba je przechwycić;
- czy trzymanie `+0x1F3` rzeczywiście pozwala oderwać się od ziemi przy ataku w 0,25 s (silnik może zerować prędkość mimo flagi);
- czy animacje zastępcze (katana z miecza zakrzywionego, topór z młota) wyglądają akceptowalnie;
- czy przewijanie ×4,5 wygląda dobrze i czy silnik je przyjmuje;
- czy gra sama kończy animację lądowania na końcu HKX i czy ESD nie gubi stanu po zleceniu lądowania przez DLL;
- czy łuk po wczesnym ataku jest naturalny (16 m/s² dobrane z obliczeń, nie z gry);
- recovery lekkich broni po lądowaniu z ER (katana: atak 0,77 s, ruch 1,03 s) — gracz oczekuje wyraźnie krótszego niż przy ciężkich.

**Powrót:** migawka V08 (§2). Skrypty `add_jump_attacks.py` i `open_air_attack.py` są już w wersji v2; wersji sprzed v2 nie ma.

## 5. Aktywna lista zadań

Kolejność od najważniejszego:

1. **Test ataków z wyskoku v2.1** (R1 i R2, lekka i ciężka broń, pojedynczy klik zaraz po skoku i osobno spamowanie; F8 po każdym złym ataku). Jeśli dobre: snapshot `work\*.JUMPATK_STABLE.*` (kod, DLL, `c0000.anibnd`, `a2x/a3x/a4x`, `jump_attack_table.h`). Potem: krótsze recovery lekkich broni, jeśli czasy ER okażą się za długie; przechwycenie 3800/3810, jeśli gra nadal je zleca; pętla spadania 31060 i lądowania 31071/31072 dla długich upadków; właściwe animacje katany (przeliczenie plików ER a029 na szkielet DSR); R2 w grupie 33, grupa 42; atak z odskoku (ID DSR niepotwierdzone); opcjonalnie słabsze przyspieszenie ciężkich broni (a32/a35).
2. **Test w grze rzeczy z V08, których nie sprawdzono:** synchronizacja fali z trafieniem (`tools\boss_tae_sync_hits.py`); log z bufora + F8; `launch_no_omniroll.bat` (kontrola bez DSROmniRoll); pełny przegląd trafień w `launch_asylum_er.bat`.
3. **Skok — wygląd:** ślizganie przy lądowaniu (wygaszać rozpęd w ostatnich klatkach albo dopasować animację lądowania); przeskok rąk 900 → 1550 (plan: podmiana ID 1550 → 906 na warstwach 8/24 w `PlayAnimDetour`, bez przenoszenia na warstwę 7); 2–4 klatki zwolnienia przed spadaniem z półki (skrócić JT27 w 900 albo dosuwać pozycję).
4. **Blok w sprincie.** Najpierw sprawdzić vanilla DSR (czy blok przerywa sprint). Opcje: (a) ignorować żądanie bloku w sprincie (flaga w handlerze wejścia); (b) blok przerywa sprint do biegu; (c) osobna animacja górnej części ciała dla sprintu z gardą.
5. **Unik — monitorować.** W V4 zawieszenia nie udało się wywołać i przyczyna nie jest ustalona wprost. Jeśli wróci: F8 przy wystąpieniu + log `unik-stan` + test `launch_no_omniroll.bat`.
6. **Estus — chowanie broni (zaparkowane).** ER chowa broń eventem TAE 710 `HideEquippedWeapon`; DSR robi to w samej animacji (kość `R_Weapon`). Droga: DSAS SoulsAssetPipeline + Havoc.dll / TagTools, albo flaga w pamięci przez DLL. Dochodzi mignięcie broni przy piciu w marszu.
7. **Boss c2232 (Asylum Demon):** ER 3015 (tupnięcie w bok; w ER obrażenia zadaje pocisk/fala, w DSR trzeba dorobić), ER 3016 (brak pliku w `c4810.anibnd`), fala uderzeniowa przy 3008, porównanie okien AI i tempa.
8. **Sprawdzić `work\dsr\GameParam.parambnd.dcx`:** wersja 556 KB vs `.bak` 498 KB. Upewnić się, że zmodyfikowana wersja nie trafiła do katalogu gry (zasada 3).
9. **Status niepotwierdzony z dawnego M0** (do sprawdzenia, nie zakładać): round-trip SoulsFormats (`verify_sf.py` → `analysis\sf_roundtrip.txt`), dekompilacja `c0000.esd.dcx` (które akcje gracza są sterowane w ESD). Pierwotny plan etapów w archiwum.
10. **Wydanie v0.6** po potwierdzeniu w grze punktów 1–2.
11. **Poza zakresem moda:** pad (DualSenseX → wirtualny X360) bywa ignorowany przez grę także bez ModEngine2 i DLL.

## 6. Nowe ustalenia z zamkniętych wątków (2026-11-12)

- **Unik — czemu nie wychodził:** gra zgłasza unik (`+0x93`) tylko wtedy, gdy kierunek jest wciśnięty w chwili klawisza uniku. Klawisz uniku wciśnięty 15–30 ms przed kierunkiem daje zero reakcji. Bufor z §1 to rozwiązuje.
- **Unik „na wprost”:** przy puszczeniu klawisza gra zgłaszała drugie żądanie (`+0x329`). DSROmniRoll wtedy kasował kierunek (`reason=superseded`). Gaszenie `+0x329` w V4 to usuwa.
- **Nieudane uniki przy szybkich seriach:** przyczyną była wytrzymałość (potwierdzone logiem `+0x3F8`), a nie zawieszenie.
- **Zawieszenie po uniku** (przy lock-onie): log DSROmniRoll pokazał `reason=timeout frames=90`, czyli gra uważała animację 710 za trwającą. Przy wariancie A TAE (JT7) nie wystąpiło w V4. Przyczyna nie jest ustalona wprost.
- **Lądowanie w skoku:** wykrywać po `+0x32` / `+0x1F3`, nie po wysokości startu (wysokość nie działa na nizszej półce).
- **Rozpęd w swobodnym spadaniu** gaśnie o ok. 2,4% na klatkę (3,65 → 2,0 m/s w 0,4 s), co jest zgodne z mnożnikiem `+0xF0` = 0,98 (plus wpływ root motion w ostatnich klatkach animacji).
- **Tempo ataków:** ścieżka prędkości animacji to `PlayerIns+0x68 → +0x18 → +0xA8` (ścieżka `+0x48` jest zła dla tego exe).
- **Asylum Demon = c2232** (AI `223200_battle.lua`). Stray Demon = c2230 (AI `223000`). Wcześniejsze testy na c2230 zostały usunięte.
- **Combo bossa:** w ER efekty 17302/3/4 z TAE; DSR ma własne kontynuacje 3010/3011/3012 (krótszy doskok: 3,8 / 2,2 / 0,3 m wobec 9,1 / 5,9 / 6,4 m w ER). Szczegóły w archiwum.
- **Fala uderzeniowa (N+1):** w wersji z synchronizacją startuje razem z trafieniem głównym (N) i zachowuje swoją długość (`tools\boss_tae_sync_hits.py`; zastosowane w 3000, 3001, 3006, 3007, 3008, 3010, 3012, 3013; 3023 pominięte). **Niesprawdzone w grze** (patrz §5, punkt 2).
- **Port animacji ER → DSR:** retarget `obrót_DSR(t) = obrót_ER(t) · ER_spocz⁻¹ · DSR_spocz` w przestrzeni modelu; skala S = 3,23 / 2,80; kość Master niesie pozycję i obrót miednicy. Narzędzia: `tools\boss_anim_port.py`, `boss_bone_map.py`, `boss_anim_install.py` (`--base`, `--combo-window ANIM:START`).
- **Diagnostyka:** `er_engine` loguje do bufora pierścieniowego 6000 × 240 znaków (CRITICAL_SECTION). Log startu idzie do pliku, potem tylko do bufora; F8 zrzuca.
