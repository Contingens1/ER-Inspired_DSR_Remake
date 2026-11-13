# ARCHIWUM BADAŃ — ds1-elden-port

Data przeniesienia: 2026-11-12. Aktualny stan projektu jest w `docs/PLAN_PROJEKTU.md`.

Zawartość tego pliku:
- **A.** Historyczne sekcje z `PLAN_PROJEKTU.md` (stan sprzed porządków, linie 17–318): inwentarz i pierwotne etapy M0–M3, stan z 2026-11-11, sondy skoku v0.5–v0.7, wersje uniku V1–V4, wątek bossów c2232 (Asylum Demon), szczegóły ataków z wyskoku v2. Treść bez zmian.
- **B.** Pełny `docs/compact.txt` (dwa podsumowania z zamkniętych wątków), bez zmian.

---

## A. Sekcje z PLAN_PROJEKTU.md (przed porządkiem)

## 1. Architektura: trzy warstwy

| Warstwa | Co to jest w DSR | Narzędzie | Kto robi |
|---|---|---|---|
| **A. Animacje** | `.hkx` (Havok 2016) w `c0000.anibnd.dcx` | Nexus DSR #748 (Tarnished już przeniesiony na szkielet DSR), DSAnimStudio, Soulstruct for Blender | gotowe + poprawki |
| **B. Timing** | TAE: okna anulowania, i-frame’y, zużycie staminy | DSAnimStudio (edytor TAE), Smithbox (paramy) | ręczna edycja danych |
| **C. Logika** | kiedy jaki ruch jest dozwolony: exe + (do weryfikacji) `chr/c0000.esd.dcx` | ESD: Soulstruct/ESDLang; exe: własny DLL | **my** |

**Ważne:** grafu behavior z ER (`c0000.behbnd` + HKS) **nie da się** przenieść do DSR. Silnik DSR go nie wykonuje. Port polega na odtworzeniu *zachowania* ER warstwami A–C, a nie na kopiowaniu plików ER.

## 2. Inwentarz tego, co już jest

### Zostaje (dobre fundamenty)
- `toolsy/`: Nuxe 1.2.1, UXM 2.4, WitchyBND 3.0.1.
- `nuxe/chr`: rozpakowane ER `c0000` (behbnd, anibnd, chrbnd). Służą jako **referencja** (podgląd timingu ER w DSAnimStudio).
- `work/scratch/sf/`: SoulsFormats (Grimrukh) zbudowany pod .NET 10 + `tools/sfbridge.py` (pythonnet). **To ma być jedyna warstwa I/O formatów.**
- `work/scratch/sf/verify_sf.py`: test round-tripu TAE (DSR/ER), ESD, BND3. Uruchomić i zapisać wynik (pkt 4, M0).
- `work/er/regulation-bin/`: paramy ER (referencja prędkości, kosztów staminy itp.).
- `tools/dcx.py`, `bnd.py`, `paramdef.py`: zostawić tylko jako referencję, nie rozwijać.

### Do archiwum (nie budować na tym)
- `tools/convert_er_c0000_to_dsr.py` + `work/havok-port/*`: mapowanie stanów ER → DSR po **regexie na nazwach** (np. `W_Fall` → „roll”), z wymyślonymi slotami DSR `#1000…`. Wynik nie ma znaczenia dla silnika. Wersje Havoka w opisie (2010.1/2010.2) też są błędne: DSR używa HKX 2016.
- `tools/apply_dsr_havok_adapter.py`: własny parser TAE (dubluje SoulsFormats). Kopiuje eventy TAE z ER do TAE DSR, a typy i parametry eventów różnią się między grami. Wskazuje na pliki `.hkx` ze szkieletu ER. `build_ds_r_chrbnd` nic nie robi. Stałe komend ESD nie są zweryfikowane. Nie uruchamiać w trybie zapisu.
- Ścieżka stance/poise (`generate_ds_stance_params.py`, `apply_to_dsr.py`): poza zakresem tego projektu, a dodatkowo ma błędy:
  - dopasowuje broń ER do DSR po prefiksie ID, a numeracje broni w obu grach nie są ze sobą zgodne;
  - wpisuje tę samą wartość do 4 różnych pól (`saDmgRatio`, `saDmgAtkDmg`, `saDurability`, `staminaDmg`);
  - w linii 49 jest błąd priorytetu operatorów (`a or b if c else None`).
  - ⚠️ `work/dsr/GameParam.parambnd.dcx` jest zmodyfikowany (556 KB vs 498 KB w `.bak`). **Sprawdzić, czy ta wersja nie trafiła do katalogu gry.**

### Do weryfikacji (może zmienić plan)
- **`chr/c0000.esd.dcx` w DSR.** Jeżeli część logiki akcji gracza siedzi w EzState (a nie tylko w exe), część mechanik (np. skok z miejsca, picie w ruchu) da się zrobić w danych bez DLL. To pierwsze pytanie badawcze.

## 3. Brakujące narzędzia (do pobrania)

| Narzędzie | Po co |
|---|---|
| **Mod Engine 2** (GitHub vswarte/ModEngine2) | ładowanie moda bez ruszania plików gry |
| **DSAnimStudio** (Meowmaritus) | podgląd animacji ER/DSR, edycja TAE, import animacji |
| **Smithbox** (vawser) | paramy DSR (MoveParam, BehaviorParam_PC, SpEffect) |
| **Nexus DSR mod #748** (repozytorium animacji) | Tarnished `c0000` przeniesiony na szkielet DSR |
| Soulstruct (GUI) / ESDLang | dekompilacja `c0000.esd` do czytelnej postaci |
| Cheat Engine + tabela DSR | podgląd stanu gracza w pamięci, testy |
| (później) Visual Studio 2022 + MinHook | DLL dla warstwy C |

## 4. Etapy

### M0 — Fundament (bez zmian w grze)
- [ ] Uruchomić `verify_sf.py`, zapisać wynik round-tripu do `analysis/sf_roundtrip.txt`.
- [ ] Zdekompilować `c0000.esd.dcx` (Soulstruct/ESDLang) → `analysis/c0000_esd/`. Odpowiedzieć: które akcje gracza są tam sterowane?
- [ ] Postawić Mod Engine 2 z pustym folderem `mod/` i sprawdzić, że gra startuje offline.
- [ ] Ustalić listę mechanik (pkt 5).

### M1 — „Czucie ER” samymi danymi
- [ ] Z repo #748 podmienić w `c0000.anibnd`: idle, chód, bieg, sprint, przewroty (light/medium/fat), backstep.
- [ ] W DSAnimStudio przenieść timing okien anulowania z TAE ER (referencja z `nuxe/chr`) do TAE DSR, **ręcznie, typami eventów DSR**.
- [ ] MoveParam: prędkości zbliżone do ER.
- **Kryterium:** przewrót i bieg wyglądają i „czują się” jak w ER, gra stabilna 30 min.

### M2 — Logika (ESD lub DLL)
Kolejność według zysku do kosztu (do potwierdzenia po M0):
1. Skok z miejsca (osobny przycisk).
2. Przewrót w dowolnym kierunku przy namierzeniu (precedens: Nexus DSR #1378 OmniRoll).
3. Sprint i przewrót bez konfliktu na jednym przycisku.
4. Anulowanie animacji w stylu ER (np. atak → przewrót).
- **Kryterium:** każda mechanika ma osobny przełącznik w `.ini` i test w grze.

### M3 — Nowe stany (opcjonalnie)
Guard counter, kucanie, atak z wyskoku z ER. Wymagają nowych akcji, których DSR nie zna. Oceniamy po M2.

## 5. Otwarte decyzje

- Które mechaniki ER są **obowiązkowe**? (przewrót · skok · sprint · anulowania · guard counter · kucanie · picie w ruchu)
- Czy ścieżka stance/poise wraca później jako osobny moduł, czy ją porzucamy?
- Dystrybucja: tylko Mod Engine 2 czy też „drop-in” do katalogu gry?

## 6. Stan na 2026-11-11 (M2 w toku)

Uruchamianie: `dist\mods\c0000_er_engine\launch_er_engine.bat` (ModEngine2 z `toolsy\ModEngine2`, tylko offline). Pliki gry nietknięte; podmiany w `dist\mods\c0000_er_engine\files\`, kod w `bin\er_engine.dll` (źródła: `native\er_engine\`, build: `build.bat`).

**Działa (przetestowane w grze):**
| Mechanika | Jak | Źródło |
|---|---|---|
| Skok z miejsca / z marszu / ze sprintu (J lub L3) | DLL wstrzykuje żądanie skoku (`+0xAE`), wariant wg stanu ruchu (`0x37BB60`): 901 pion, 902 krótki, 900 vanilla; brak przewrotu po lądowaniu (wymuszony koniec animacji 750 ms) | nasze: `tools\add_jump_anims.py`, `tools\make_jump_variants.py`, DLL |
| Przewrót w 8 kierunkach przy namierzeniu | DSROmniRoll (wersja ME2), ładowany przed naszym DLL | Nexus DSR #1378 (cudzy) |
| Picie estusa w ruchu, ze skręcaniem | ESD bez blokady ruchu, picie na górnej części ciała | Simple Estus Walking (cudzy, `c0000.esd.dcx` bez zmian) + nasze TAE (`tools\apply_estus_walk.py`: bez blokady obrotu) |
| Wolny chód w trakcie picia (jak ER) | DLL ogranicza osie ruchu (`0x1A3700/0x1A3750`) do 0,45 podczas animacji picia | nasze, DLL |

**Odłożone świadomie (do etapu animacji z ER):** mignięcie broni przy piciu w marszu i krótkie „zostanie” flaszki w ręce po trafieniu — oba z mieszania warstw animacji (maska kości warstwy górnej części ciała), nie z logiki. Wygląd skoku (dziś animacja DSR), wysokość, sterowanie w locie, docelowy przycisk skoku.

**Poza zakresem moda:** pad (DualSenseX → wirtualny X360) bywa ignorowany przez grę także bez ModEngine2 i bez naszego DLL.

**Kluczowe ustalenia techniczne:** exe = build docelowy OmniRoll (SHA-256 `A45AAA36…`); Arxan szyfruje część kodu na dysku — analiza w Ghidrze na zrzucie z pamięci (`work\ghidra\DSR_decrypted.exe`); przewrót i skok są w exe, użycie przedmiotów i zmiana broni w ESD (maszyna stanów 1, `SwitchMotion` = blokada ruchu); ID wpisu HKX w archiwum = ID animacji.

**Cudze mody w użyciu** (do podziękowań/zgody przy publikacji): DSROmniRoll, Simple Estus Walking; kandydaci: Modern Roll (Nexus 615), Realistic Jump.

**Następne kroki do wyboru:** anulowania animacji w stylu ER (np. Modern Roll jako baza TAE), sprint i przewrót bez konfliktu, sterowanie skokiem w locie, etap wyglądu (animacje ER z repozytorium Nexus #748).

### Czasy atakow z ER (2026-11-11)
- Okna JumpTable w TAE daly tylko 30-80 ms (ER jest szybszy glownie PRZED trafieniem) - porzucone.
- Dziala: er_engine.dll zmienia predkosc odtwarzania (PlayerIns+0x68 -> +0x18 -> +0xA8; sciezka z DSR-Gadget +0x48 jest zla dla tej wersji exe) odcinkami: 0 -> trafienie -> koniec trafienia -> okno JT4, tak by wypadaly w czasach ER. Zamach/trafienie max x1.35 (x2 wygladalo niewiarygodnie), koncowka max x2, nigdy nie zwalniamy.
- Tabela: tools/gen_attack_speed_table.py + tools/anim_map_attacks.json -> native/er_engine/attack_speed_table.h (129 animacji, 14 grup: R1 1H/2H, atak z biegu 3500/4500, z przewrotu 3900/4900).
- Do zrobienia: R2 (ER start/substart/end), atak z odskoku (ID DSR niepotwierdzone), opcjonalnie slabsze przyspieszenie dla ciezkich broni (a32/a35).

### Skok z ER - stan v0.5 (2026-11-11)
- Dziala: animacje wybicia ER (900/901/902 <- 202030/202000/202020) z oryginalnym root motion y (przysiad + szczyt ~1.15 m); TAE: JT27 Ignore Gravity do konca wybicia, bez JT7; DLL: wylaczona kolizja z mapa na przysiad (0.35 s), dosuwanie w locie (przod = -sin/-cos kata), wykrywanie ladowania na wysokosci startu. Migawka: work/*.JUMP_STABLE.* (kod + dane).
- Do zrobienia (nieudane proby 2026-11-11 - NIE powtarzac w tej formie): skok na nizsza polke - gra przerywa skok ~0.7 s (JT66 Special Transition) i spada pionowo bez rozpedu; rece z bronia przeskakuja (spadanie 1550 na warstwie nog). Pr\u00f3by: petla lotu 906 na warstwie 7, przechwytywanie -1, lapanie ladowania z warstwy 8, przenoszenie rozpedu zapisem pozycji, przesuniecie JT51/JT66 - kruche (tekstury, zawieszanie) albo bez efektu. Kandydat na przyszlosc: znalezc w exe/ESD przejscie do spadania lub predkosc postaci (zamiast zapisu pozycji).
- Lekkie slizganie przy ladowaniu po sprincie - akceptowane.

### Skok - rozped przy spadaniu (2026-11-11, analiza statyczna exe z Linuksa)

**Stan:** ZAKONCZONE - sonda przetestowana, wynik i poprawka w sekcji "wynik sondy i poprawka v0.6" nizej. Ponizej zapis analizy statycznej (historyczny).

**Stan z 2026-11-11:** przyczyna ustalona statycznie (Ghidra + objdump na `work\ghidra\DSR_decrypted.exe`), NIE zweryfikowana w grze. Do `native\er_engine\er_engine.cpp` dopisana sonda `PhysProbeTick` (tylko odczyt, tylko `ER_DIAG=1`) - nieskompilowana i nieuruchomiona. Nastepny krok: build + test sondy na Windowsie, potem hook predkosci.

**Objaw (log):** przy skoku z polki gra po ~735 ms sama konczy skok (`PlayAnim -1` na warstwach 7/23), 30 ms pozniej zleca spadanie 1550 na warstwach 8/24; predkosc pozioma spada wtedy z ~8.5 m/s do ~2 m/s.

**Ustalenia:**
- Rozped poziomy pochodzi wylacznie z root motion animacji skoku (+ dosuwanie pozycji w `AirControlTick`). Po przerwaniu animacji zostaje sama grawitacja.
- Spadanie 1550 zleca komenda ESD, nie exe: `FUN_140385550(ctx, anim, slot, ...)` wolana z `0x14038dd6e` i `0x14038e137`. Dlatego przesuwanie JT51/JT66 w TAE nic nie dawalo.
- Tabela slot -> warstwy (`0x14132d000` / `0x14132d030`): slot 4 = 5/17 (gorna czesc ciala), slot 6 = 7/23 (akcja), slot 7 = 8/24 (spadanie).
- Obiekt `PlayerIns+0x68 -> +0x28` (w DLL `ChrPosData()`) to kontroler fizyki postaci:
  - `+0x04` kat, `+0x10` pozycja, `+0x32` na ziemi, `+0x33` na zboczu
  - `+0x38` hkpCharacterProxy*; predkosc liniowa = `proxy+0x60` (getter `0x140a79b10`, setter `0x140a79b20`)
  - `+0x6D` "zachowaj predkosc w powietrzu" (ustawiane co klatke argumentem `FUN_1402bb020`), `+0xD0` predkosc z poprzedniej klatki, `+0xF0` mnoznik XZ w swobodnym spadaniu
  - `+0x1B0` / `+0x1B4` czas w powietrzu, `+0x1E4` skala grawitacji (< 1.0 = traktowany jak na ziemi)
  - `+0x1F0` tryb swobodnego spadania, `+0x1F2` / `+0x1F4` grawitacja wylaczona (`1F4` z ESD), `+0x1F3`
- Globalne limity spadania: `0x141a2ae54` = 6.0 m/s (XZ, na os), `0x141a2ae58` = 1.0 (Y w gore), `0x141a2ae5c` = 50 (Y w dol).
- Lancuch wywolan co klatke: `FUN_140379880` (ChrCtrl) -> `FUN_1402bb020` -> `FUN_1402bb150` -> `FUN_1402bbe40`. Ta ostatnia (RVA `0x2BBE40`, argumenty: kontroler, wektor wyjsciowy, delta root motion, czas {`+8` dt, `+0xC` 1/dt}) wybiera miedzy predkoscia z root motion a bezwladnoscia, dodaje grawitacje i zapisuje predkosc do proxy.
- Nieustalone: ktora galaz `FUN_1402bbe40` zeruje rozped w chwili przejscia w spadanie - to ma pokazac sonda.

**Plan rozwiazania:**
1. Sonda (zrobiona w kodzie, do przetestowania): od zlecenia skoku przez 2.5 s co klatke linia `fiz +...ms` z polami: `ziemia`, `zbocze`, `6D`, `1F0`, `1F2`, `1F3`, `1F4`, `graw` (`+0x1E4`), `xz*` (`+0xF0`), `t_pow` (`+0x1B0`/`+0x1B4`), `poz`, `v_proxy` (+ dlugosc w poziomie), `v_poprz` (`+0xD0`).
2. Hook MinHook na `FUN_1402bbe40`: po oryginale, tylko dla gracza i tylko w fazie lotu, nadpisac X/Z predkosci proxy wlasnym wektorem rozpedu (start = predkosc z klatki wybicia, galka zmienia go z ograniczonym przyspieszeniem). Os Y zostaje przy silniku.
3. Usunac zapis pozycji z `AirControlTick` (kolizje liczy wtedy Havok; rozped nie zalezy od animacji, wiec przechodzi przez zmiane 900 -> 1550).
4. Ladowanie wykrywac po `+0x32` zamiast `y <= g_airY0 + 0.05` (obecny warunek z definicji nie dziala na nizszej polce).
- Pozniej, osobno: przeskakiwanie rak - podmiana samego ID 1550 -> 906 na tych samych warstwach 8/24 w `PlayAnimDetour` (bez przenoszenia na warstwe 7).
- Mozliwe ograniczenie: limit 6 m/s na os w swobodnym spadaniu moze przycinac skok ze sprintu - ewentualnie podniesc `0x141a2ae54`.

**Test sondy (Windows):**
1. `native\er_engine\build.bat`, potem `dist\mods\c0000_er_engine\launch_er_engine.bat`.
2. Po 2-3 skoki kazdego rodzaju, rozdzielone znacznikiem F8: z miejsca na plaskim; z biegu na plaskim; z biegu z polki w dol; ze sprintu z polki w dol.
3. Analiza `dist\mods\c0000_er_engine\bin\er_engine.log`:
   - czy `v_proxy` ma sensowne wartosci (kilka m/s w poziomie w trakcie wybicia); smieci albo `(brak proxy)` = zly offset `+0x38 -> +0x60`, hook trzeba oprzec na czyms innym;
   - w ktorej klatce `xz` spada i co sie wtedy zmienia (`ziemia 1->0`, `1F0 0->1`, `6D`, `1F2`/`1F4`) - wskazuje galaz do obejscia;
   - czy `ziemia` wraca na 1 dokladnie przy ladowaniu na nizszej polce - wtedy nadaje sie na warunek ladowania.

**Analiza exe z Linuksa (gdyby byla potrzebna):** Ghidra headless dziala na gotowym projekcie z `JAVA_TOOL_OPTIONS=-Duser.name=nemos` (inaczej `NotOwnerException`) i `-readOnly`; `objdump -d -M intel -j .text` na `DSR_decrypted.exe` daje listing do grepowania.

### Skok - rozped przy spadaniu: wynik sondy i poprawka v0.6 (2026-11-12)

**Stan:** sonda przetestowana w grze (log: `analysis\jump_phys_probe_2026-11-11.log`, 4 serie rozdzielone F8), poprawka zaimplementowana i zbudowana, NIE przetestowana w grze. Migawka sprzed zmiany: `work\er_engine.PRE_MOMENTUM.cpp` / `.dll` (powrot = skopiowac dll do `dist\mods\c0000_er_engine\bin\er_engine.dll`).

**Co pokazala sonda (offsety z analizy statycznej potwierdzone):**
- `v_proxy` (`+0x38 -> +0x60`) jest poprawne: bieg 4.15 m/s, sprint ~6.1, lot 902 ~4.4, lot 900 ~7.3 m/s.
- `+0x32` ("ziemia") jest 1 przez caly lot napedzany animacja (grawitacja wylaczona `+0x1F2 = 1`), 0 tylko w prawdziwym spadaniu, wraca na 1 dokladnie w klatce ladowania (takze na nizszej polce). `+0x1F3 = 1` od wybicia do ladowania.
- Gra sama konczy animacje skoku zawsze (takze na plaskim): 902 po ~0.70 s, 900 po ~0.73 s, 901 po ~0.85 s; 30 ms pozniej 1550. Na plaskim spadanie trwa ~80 ms, z polki do ladowania.
- Rozped nie jest zerowany jednorazowo: w swobodnym spadaniu (`+0x1F0 = 1`) gasnie o 2.4% na klatke (3.65 -> 2.0 m/s w 0.4 s). W skoku ze sprintu dodatkowo root motion 900 zwalnia juz 1-2 klatki przed koncem animacji (7.3 -> 1.3 m/s) i spadanie startuje od 1.3 m/s.
- Kolejnosc w klatce: handler wejscia (nasz tick) dziala PO kroku Havoka (przyrost pozycji = `v_proxy` biezacej klatki * 1/60).

**Dekompilacja `FUN_1402bbe40`** (`work\ghidra\decomp\`, projekt `DSR_dec`, program `DSR_decrypted.exe`):
- `v_anim` = root motion / dt + `+0x130`; przy wylaczonej grawitacji (`+0x1F2`/`+0x1F4`) to jest predkosc koncowa.
- `+0x1F0 == 1`: predkosc = biezaca predkosc proxy, obcieta do +-6 m/s na os XZ (`0x141a2ae54`), XZ * `+0xF0` (0.98), + grawitacja.
- inaczej gdy (`+0x6D` i nie na ziemi) lub `+0x1F3`: predkosc = `+0xD0`, + grawitacja.
- na koncu `+0xD0` = predkosc proxy sprzed zapisu, proxy = nowa predkosc.

**Poprawka (bez nowego hooka, `AirMomentumTick` w `er_engine.cpp`):**
- W locie (grawitacja wylaczona) zbiera sredni rozped poziomy z okna 400-600 ms.
- Od wlaczenia grawitacji (t >= 400 ms, w powietrzu) do ladowania (`+0x32 = 1` i `+0x1F3 = 0`) co klatke wpisuje X/Z: proxy `+0x60` = rozped / `+0xF0`, `+0xD0`/`+0xD8` = rozped. Os Y zostaje przy silniku. Na ten czas limit `0x141a2ae54` 6 -> 12 m/s (sprint), potem przywracany.
- Galka w spadaniu dociaga rozped do kierunku patrzenia (4 m/s^2, do max(rozped, 2 m/s)). Zapis pozycji z `AirControlTick` wylaczony w fazie spadania (zostaje w locie - tam predkosc = root motion i zapis predkosci nic nie daje).
- F7 (tylko ER_DIAG) wlacza/wylacza poprawke w trakcie gry - test A/B. Log: `rozped: spadanie od ...`, `rozped: koniec (ladowanie) ...`.

**Test w grze (do zrobienia):**
1. `dist\mods\c0000_er_engine\launch_er_engine.bat` (DLL juz zbudowany).
2. Z biegu z polki w dol x3, ze sprintu z polki w dol x3, z miejsca z polki (z galka do przodu) x2, potem F7 i jeszcze raz z biegu z polki (porownanie), F7 z powrotem. Kontrolnie po 2 skoki na plaskim (z miejsca, bieg, sprint) - nie powinno byc gorzej niz w v0.5.
3. Ocena: czy postac leci po luku zamiast spadac pionowo; czy nie ma szarpniecia w chwili przejscia w spadanie; czy przy ladowaniu nie ma slizgu / przenikania; czy przy scianie nic sie nie zawiesza.

**Znane ograniczenia / nastepne kroki:**
- Sprint z polki: 2-4 klatki zwolnienia (do ~1.3 m/s) przed spadaniem zostaja - grawitacja jest jeszcze wylaczona i predkosc = root motion. Jesli widoczne: skrocic JT27 w TAE 900 albo dosuwac pozycje w tych klatkach.
- Rece z bronia przy przejsciu 900 -> 1550 bez zmian (osobny krok: podmiana ID 1550 -> 906 na warstwach 8/24 w `PlayAnimDetour`).
- Wykrywanie ladowania w `AirControlTick` nadal po wysokosci startu (nieszkodliwe: gra sama konczy animacje skoku); mozna przejsc na `+0x32`/`+0x1F3`.

### Skok - rozped przy spadaniu v0.7: gladkie przejscie (2026-11-12)

**Stan:** zbudowane, NIE przetestowane w grze. Migawka v0.6: `work\er_engine.MOMENTUM_V06.cpp` / `.dll`; log testu v0.6: `analysis\jump_momentum_v06_test_2026-11-12.log`.

**Wynik testu v0.6 (gracz):** zmiana wyrazna, ale przejscie w spadanie czuc "jak trafienie w teksture", a potem postac jest jakby popchnieta do przodu.

**Przyczyna (log v0.6, skok ze sprintu z polki):**
- Ostatnie klatki animacji skoku to autorskie ladowanie: root motion hamuje jeszcze przy wylaczonej grawitacji. Poziom 7.3 -> 5.4 -> 1.3 m/s, pion -6.8 -> -2.0 -> 0.0 m/s (klatki 703-766 ms). To jest "tekstura".
- Po wlaczeniu grawitacji v0.6 przywracalo od razu 7.2 m/s w poziomie, a pion startowal od ~0 - stad "pchniecie" i zbyt plaski, daleki lot.
- Skok z biegu (902): pion ciagly, poziom 3.4 -> 4.5 m/s (lekkie pchniecie).

**Zmiana v0.7 (`AirMomentumTick`):**
1. Animacje skoku konczymy sami tuz przed hamowaniem (`MomCutMs`: 650 ms dla 900/902, 770 ms dla 901; tylko gdy na warstwie 7 nadal gra skok, nie atak z wyskoku). Gra wlacza grawitacje 1-2 klatki pozniej.
2. Rozped = predkosc ostatniej dobrej klatki lotu (nie srednia z 400-600 ms) + skladowa dosuwania galka z `AirControlTick` (ciaglosc predkosci).
3. Pion: przejmujemy predkosc pionowa z ostatniej dobrej klatki (kontynuacja balistyczna) i wpisujemy ja do proxy `+0x64` i `+0xD4`, dopoki silnik nie wejdzie w swobodne spadanie (`+0x1F0 = 1`); dalej silnik sam dodaje grawitacje.
- F7 nadal przelacza calosc (wylaczone = zachowanie v0.5, bez ciecia animacji).

**Skutek uboczny do oceny:** na plaskim skok tez konczy sie balistycznie (postac jest ~0.5 m nad ziemia w chwili ciecia i doladowuje z rozpedem zamiast autorskiego hamowania). Jesli na plaskim jest gorzej niz w v0.5: podniesc `MomCutMs` albo ciac tylko gdy pod postacia nie ma ziemi.

**Test:** jak w v0.6 (z biegu / ze sprintu / z miejsca z polki, F7 do porownania, kontrolnie plaskie). W logu: `rozped: koniec animacji skoku ...`, `rozped: spadanie od ..., poziom ..., pion ... (silnik ...)`.

### Skok v0.7 - ZATWIERDZONY jako stabilny (2026-11-12)

**Wynik testu v0.7 (gracz):** fizyka skoku (takze z polki w dol) jest dobra - to jest punkt odniesienia. Wyglad (animacje) do dopracowania.

**Migawka `JUMP_V07_STABLE`** (powrot = skopiowac na miejsce):
- kod: `work\er_engine.JUMP_V07_STABLE.cpp` -> `native\er_engine\er_engine.cpp`
- DLL: `work\er_engine.JUMP_V07_STABLE.dll` -> `dist\mods\c0000_er_engine\bin\er_engine.dll` (i `dinput8.dll`)
- dane: `work\c0000.anibnd.JUMP_V07_STABLE.dcx`, `work\c0000_a00_lo.JUMP_V07_STABLE.dcx` -> `dist\mods\c0000_er_engine\files\chr\`

**Do dopracowania (wyglad, nie fizyka) - uwagi gracza z testu v0.7:**
1. Lekkie slizganie postaci (przy ladowaniu / po przejsciu w spadanie). Kandydaci: rozped trzymany do klatki ladowania wlacznie, brak animacji ladowania dopasowanej do predkosci; sprawdzic, czy wygaszac rozped w ostatnich klatkach przed ziemia albo dopasowac animacje ladowania.
2. Przeskok modelu rak (z bronia) przy przejsciu skok -> spadanie (900 -> 1550 na warstwach 8/24). Plan: podmiana ID 1550 -> 906 (petla lotu z ER) na tych samych warstwach w `PlayAnimDetour`, bez przenoszenia na warstwe 7.
3. Blok w sprincie (przeoczone wczesniej): animacja sprintu jest z ER (postac mocno pochylona), a blok tarcza/bronia nie jest w sprincie blokowany - gorna czesc ciala trzyma bron przed soba i wyglada to absurdalnie. Do ustalenia: jak jest w vanilla DSR (czy blok przerywa sprint / sprint opuszcza garde) i jak w ER (sprint z uniesiona tarcza ma osobna poze). Opcje: (a) w sprincie ignorowac zadanie bloku (DLL, flaga zadania bloku w handlerze wejscia), (b) blok przerywa sprint do biegu, (c) osobna animacja gornej czesci ciala dla sprintu z garda.

### Bossowie - rozpoznanie (noc 2026-11-12)

Wyniki w `docs\NOC_2026-11-12.md`: AI w Lua (dekompilacja + round-trip dziala), port animacji przeciwnika z ER (zablokowany na zapisie HKX 2015 - potrzebna zgoda na `toolsy\soulstruct-havok` + scipy), Asylum Demon vs Erdtree Avatar (rekomendacja: hybryda). Mod testowy: `dist\mods\boss_asylum_test\` (3 pliki .bat) - do testu w grze. Uwaga: DSR uzywa Havoka 2015 (`20150100`), nie 2016.

**Aktualizacja 2026-11-12 rano:** zgoda uzyskana, port animacji przeciwnika dziala poza gra. `tools\boss_anim_port.py` (ER hk2018 -> szkielet DSR -> HKX 2015 spline), `tools\boss_bone_map.py`, `tools\boss_anim_install.py` (podmiana w anibnd + przesuniecie zdarzen TAE). Pierwsza animacja: ER c4810 a3003 w slocie c2230 a00_3003, test: `dist\mods\boss_asylum_test\launch_boss_anim.bat` - NIE sprawdzone w grze. Uwaga: te same numery atakow w DSR i ER to nie te same ruchy; pary dobierac po ksztalcie (`tools\boss_attack_shapes.py`).

**SPROSTOWANIE 2026-11-12 (po testach w grze):** Asylum Demon to c2232 + AI `223200_battle.lua`; c2230 + `223000` to Stray Demon. Wszystkie wczesniejsze testy bossa (`launch_boss_*`) zmienialy zla postac i zostaly usuniete. Siedem atakow Erdtree Avatara to te same animacje co w c2232 (ER 3003 = DSR 3004), wiec tempo atakow juz jest jak w ER; nowe sa tylko ER 3008/3010/3011/3012/3015. Aktualny test: `launch_asylum_er3008.bat` (ER a3008 w slocie 3003, AI tylko 3003) i `launch_asylum_orig3003.bat` (odniesienie) - NIE sprawdzone w grze. Szczegoly: koniec `docs\NOC_2026-11-12.md`.

### Unik: brak reakcji i zawieszenie po uniku (zgloszone 2026-11-12)

Gracz (klawiatura): 1) czasem unik nie wychodzi, zwlaszcza przy krotkim, jednoczesnym wcisnieciu kierunku i uniku; 2) postac potrafi zawisnac w pozie po uniku w walce. Stan wiedzy: kod er_engine.dll nie ma logiki uniku, ALE unik jest przez nas zmieniony w danych (animacja i parametry/zdarzenia z ER, dluzszy przewrot) - to pierwszy podejrzany obok DSROmniRoll: okna przerwan/kolejnej akcji z ER i koncowka animacji. W ostatniej sesji 155 zadan uniku (+0x93) wobec 116 `commit-seq` w logu DSROmniRoll - poszlaka, nie dowod. DLL po V07 dostal WYLACZNIE diagnostyke (log): krawedzie klawiszy z czasem trzymania i osiami, kazde zlecenie animacji na warstwie 7 z ctx, F8 = znacznik + 2.5 s zrzutu fizyki. Zachowanie bez zmian; powrot do V07: `work\er_engine.JUMP_V07_STABLE.dll`. Czeka na test z F8 przy kazdym wystapieniu.

**Diagnoza z logu 2026-11-12 (klawiatura, unik = boczny przycisk myszy 0x06):**

1. Brak uniku: gra zglasza unik (+0x93) tylko, gdy w chwili wcisniecia klawisza uniku jest juz kierunek. W obu oznaczonych przypadkach klawisz uniku poszedl w dol 15-30 ms PRZED klawiszem kierunku (osie 0,0) - zero reakcji, takze przy puszczeniu z kierunkiem. Poprawka w DLL (ROLLBUF_V1): bufor 180 ms - klawisz uniku bez kierunku czeka na kierunek i wtedy DLL sam wstawia zadanie uniku (jak skok). Klawisz uniku uczony z udanych unikow, zapis w `bin\er_engine_rollkey.txt` (wpisane 6). F6 (diag) wlacza/wylacza bufor. NIE sprawdzone w grze; ryzyko: kierunek uniku z DSROmniRoll przy wstawionym zadaniu.
2. Zawieszenie po uniku: jedno zlapane wystapienie. Unik 710 normalnie konczy sie po 0.66-0.67 s (przerwanie ruchem; nasze TAE ma okna przerwan od 0.67 s zamiast 1.10 s) albo po ok. 1.08 / 1.65 s. W zawieszeniu: kierunek puszczony w 0.64 s, NOWY klawisz kierunku w 0.83 s -> natychmiast koniec animacji (anim -1) i postac stoi nieruchomo na ziemi (fizyka normalna, pozycja stala, kolejne klawisze kierunku bez efektu) az do trafienia. Hipoteza: przerwanie ruchem w ogonie uniku po chwili bez kierunku. Do potwierdzenia: unik, puscic kierunek przed koncem, nacisnac kierunek ok. 0.8 s po starcie. Podejrzane: przesuniete okna w TAE 710 lub ESD gracza z moda.
Migawki: `work\er_engine.V07_DIAG.*` (V07 + sam log), `work\er_engine.ROLLBUF_V1.*` (z buforem).

**Unik - stan po tescie ROLLBUF_V1 (2026-11-12):**

- Bufor dziala (15 zgloszen w sesji), ale: a) zglaszal unik 15-60 ms po klawiszu kierunku - DSROmniRoll nie przechwytuje wtedy kierunku (40 przechwycen na 41 naturalnych zadan, 0 dla zadan z bufora) i unik bywal na wprost; b) gra zglasza unik drugi raz przy puszczeniu klawisza. ROLLBUF_V2: okno 250 ms, zgloszenie dopiero gdy kierunek trwa 50 ms, kasowanie dubla do 400 ms po zgloszeniu. NIE sprawdzone w grze; czy 50 ms wystarczy na poprawny kierunek - nie wiem, to hipoteza.
- Zawieszenie: gracz potwierdzil wyzwalacz (inny kierunek pod koniec uniku) i ze kolejny unik z zawieszenia do niego wraca. W logu: w zawieszeniu kazde wcisniecie kierunku i kazde zadanie uniku konczy sie samym `anim=-1` na warstwie 7, bez startu 710. Mechanizm NIEZNANY. Dodane: log warstwy 23, F9 = wymuszone -1 na warstwach 7 i 23 (eksperyment), dwa warianty TAE 710 do testu: `launch_roll_testA.bat` (blokada obrotu JT7 do 2.33 s jak w oryginale; u nas 0.70 s) i `launch_roll_testB.bat` (ActivateJumpTableEarly 0.57-0.67 s zamiast 0.57-1.10 s). Narzedzie: `tools\roll_tae_variant.py`.
- Przy okazji: pliki animacji gracza w modzie maja naglowek SDKV 20160100 i gra je czyta (oryginalne pliki DSR maja 20150100).

**Unik - stan po testach ROLLBUF_V2 / wariantow A i B (2026-11-12):**

- Gracz: zawieszenie wystepuje TYLKO przy namierzeniu (lock-on); F9 (wymuszone -1 na warstwach 7 i 23) nie pomaga; wariant A (blokada obrotu JT7 do konca uniku) wyraznie utrudnia wywolanie, B nie pomaga. Wariant A przyjety jako domyslny (`files\chr\c0000.anibnd.dcx`; poprzedni: `work\c0000.anibnd.before_rollA.dcx`).
- Szczegolowy log DSROmniRoll (`toolsy\...DSROmniRoll\DSROmniRoll.log`: ROLL-ARM / ROLL-COMMIT / ROLL-TRAJECTORY): normalny unik `anim-exit frames=41 hold=40`; w zawieszeniu `reason=timeout frames=90` - gra uwaza, ze animacja 710 nadal trwa. Unik 'na wprost' = `reason=superseded` po kilku klatkach + nastepny wpis `committed=0`: drugie zadanie uniku przerywa trzymanie kierunku.
- Skad drugie zadanie (dekompilacja FUN_140398920, `work\ghidra\decomp\FUN_140398E4F.c`): w trybie 'unik przy wcisnieciu' (DAT_141c78add == 0) gra przy wcisnieciu ustawia +0x329 i przy puszczeniu klawisza zglasza +0x93 drugi raz. Inne pola: +0x260 czas trzymania klawisza, +0x324/+0x328 odskok, prog DAT_141a2c0a0. ROLLBUF_V3: po zgloszeniu uniku przy wcisnietym klawiszu DLL gasi +0x329 (takze przy zgloszeniu z bufora). NIE sprawdzone w grze.
- Zawieszenie: mechanizm nadal nieznany; podejrzany DSROmniRoll (dziala tylko przy namierzeniu, trzyma kierunek przez `direction-lease-frames=96`). Test rozstrzygajacy: `launch_no_omniroll.bat` (ten sam mod bez DSROmniRoll) - czy przy namierzeniu da sie wywolac zawieszenie.

**Sprostowanie (2026-11-12):** oznaczony F8 nieudany unik NIE byl w stanie zawieszenia (gracz: zawieszenie nie blokuje uniku i nie bylo go tam). Surowy log: klawisz uniku + kierunek w 0.86 s poprzedniego uniku, kierunek przerwal poprzedni unik (-1 na warstwach 7 i 23), zadanie z bufora 46 ms pozniej zostalo przyjete (flaga skonsumowana), ale 710 nie wystartowala; 235 ms pozniej animacja 6052 na warstwach 11/26. Przyczyna NIEZNANA; kandydaci: wytrzymalosc po 5 unikach w 3.7 s, zadanie tuz po przerwaniu ruchem, trafienie. Dodany log `unik-stan` (pole +0x3F8, namierzenie, czas trzymania, flagi odskoku) przy kazdym klawiszu i zadaniu uniku.

**Unik - ROLLBUF_V4 (2026-11-12):**

- Potwierdzone logiem: pole `p3+0x10 -> +0x3F8` to wytrzymalosc (95 -> 70 -> 55 -> 30 -> 0 -> -15 przy kolejnych unikach; unik kosztuje ok. 25-30). Nieudane uniki przy szybkich seriach = brak wytrzymalosci.
- Unik 'na wprost' przy jednoczesnym kliknieciu kierunku i uniku: wszystkie trzy oznaczone przypadki to uniki zgloszone przez bufor (flaga +0x93 wstawiona po handlerze). DSROmniRoll nie mial dla nich zadnego wpisu ROLL-ARM (uzbraja sie w sciezce gry przy wcisnieciu, w FUN_140398920), wiec kierunku nikt nie ustawil i postac rolowala tam, gdzie patrzyla.
- V4: bufor nie wstawia juz flagi. Hook FUN_1401a46b0 (RVA 0x1A46B0, akcja 0x5C = 'klawisz uniku wlasnie wcisniety'; 0x1A4610 / akcja 0x5B = 'trzymany') zwraca jednorazowo 'wcisniety' w klatce, w ktorej kierunek trwa juz 20 ms, do 250 ms po prawdziwym wcisnieciu bez kierunku. Gra przechodzi wtedy wlasna sciezke uniku razem z hookami DSROmniRoll. NIE sprawdzone w grze; niewiadoma: czy DSROmniRoll uzbraja sie przy takim wcisnieciu (w jego logu powinien byc ROLL-ARM + ROLL-COMMIT dla kazdego uniku z bufora).

### Unik v4 - ZATWIERDZONY przez gracza (2026-11-12)

Test na `launch_er_engine.bat` (z DSROmniRoll): unik 'na wprost' nie wystapil, zawieszenia przy namierzeniu nie udalo sie wywolac mimo prob, jednoczesne klikniecie kierunku i uniku dziala; za dlugi odstep = odskok (normalne). Sesja: 27 wcisniec podanych przez bufor, 58 unikow. Co weszlo: bufor przez hook FUN_1401a46b0, gaszenie +0x329 (brak drugiego zadania uniku przy puszczeniu klawisza), TAE 710 z blokada obrotu do konca (wariant A). Dlaczego zniknelo zawieszenie - NIE ustalone wprost; najbardziej prawdopodobne: drugie zadanie uniku + DSROmniRoll (ROLL-TRAJECTORY superseded) w polaczeniu z wariantem A. Migawka: `work\er_engine.ROLL_V4_STABLE.cpp/.dll`, `work\c0000.anibnd.ROLL_V4_STABLE.dcx`, `work\c0000_a00_lo.ROLL_V4_STABLE.dcx`. DLL nadal ma wlaczona diagnostyke (log klawiszy i animacji). `launch_no_omniroll.bat` po poprawce startu nie byl jeszcze uruchomiony.

**Log er_engine od 2026-11-12:** start gry idzie do pliku, potem wpisy trafiaja do bufora w pamieci (ostatnie 6000 linii) i nie sa zapisywane. F8 zrzuca bufor do `er_engine.log` (historia sprzed znacznika) i przez 3 s pisze dalej wprost. Stary log (5 MB) przeniesiony do `bin\er_engine.before_ringlog.log`. Migawka ROLL_V4_STABLE zaktualizowana o te zmiane (zachowanie postaci bez zmian). NIE sprawdzone w grze.

### V08 - migawka (2026-11-12)

Skok v0.7 + unik v4 (bufor uniku, brak drugiego zadania uniku, TAE 710 wariant A) + log w pamieci zrzucany po F8. Pliki: `work\er_engine.V08_STABLE.cpp/.dll`, `work\c0000.anibnd.V08_STABLE.dcx`, `work\c0000_a00_lo.V08_STABLE.dcx`. Uwaga: gracz testowal wersje bez zmiany logowania (= `work\er_engine.ROLLBUF_V4.dll`); sama zmiana logowania nie byla uruchomiona w grze. Otwarte z listy gracza: lekkie slizganie po skoku, przeskok rak 1550->906, blok w sprincie. Nastepny temat: bossowie (Asylum Demon = c2232).

### Asylum Demon z atakami ER (2026-11-12)

AI Erdtree Avatara (`nuxe\script\481000_battle.luabnd.dcx`) dekompiluje sie tym samym DSLuaDecompiler -> `work\boss_ai\er_481000\481000_battle.dec.lua`.

Uklad combo w ER (efekty 17302/17303/17304 nadawane przez TAE pierwszego ataku, warunek: gracz z przodu, 2-15 m): 3000 -> 3010, 3001 -> 3010, 3002 -> 3011, 3005 -> 3011, 3003 (= DSR 3004) -> 3012, 3011 -> 3012. DSR ma pod 3010/3011/3012 WLASNE, inne kontynuacje (krotszy doskok: 3.8 / 2.2 / 0.3 m wobec 9.1 / 5.9 / 6.4 m w ER) i uklad 3000 -> 3010, 3002 -> 3011 -> 3012, 3003 -> 3013.

Zrobione (NIE sprawdzone w grze), `dist\mods\boss_asylum_test\`:
- `files_c2232_er`: ER a3008, a3010, a3011, a3012 w slotach DSR o tych samych numerach; zdarzenia DSR przesuniete na czasy ER (trafienia 3010: 1.57-1.73, 3011: 1.23-1.43, 3012: 1.07-1.30; okna AI 3.53 / 3.27 / 4.17 s), zachowania trafien DSR bez zmian; dodane okna combo (JT23) w 3001 (od 3.00 s), 3004 (od 1.60 s), 3005 (od 2.27 s).
- `files_c2232_er_ai`: AI 223200 + polaczenia z ER: Act07 3001 -> 3010, Act08 3004 -> 3012, Act09 3005 -> 3011 (70 %, inaczej pojedynczy atak jak dotad). Zrodlo: `work\boss_ai\223200_battle.er_combos.lua`.
- Uruchamianie: `launch_asylum_er.bat` (animacje + AI), `launch_asylum_er_anim_only.bat` (same animacje).
- Narzedzie: `tools\boss_anim_install.py` ma teraz `--base` (laczenie podmian) i `--combo-window ANIM:START`.

Nie zrobione: ER a3015 (tupniecie w bok - w ER obrazenia zadaje tylko pocisk/fala, w DSR trzeba by ja dorobic), ER a3016 (AI uzywa zamiennie z 3008; pliku nie ma w c4810.anibnd), fala uderzeniowa przy 3008.

**Test `launch_asylum_er.bat` w grze (2026-11-12):** dziala - gracz widzial kontynuacje z ER (przeciagniecie po ziemi), AI dziala; nie wszystkie trafienia sprawdzone. Zgloszony problem (takze w oryginale DSR): ataki z uderzeniem w ziemie maja dwa trafienia - glowne (zachowanie N) i fale (N+1) - a fala zaczyna sie dopiero po koncu glownego, wiec nie da sie tego przejsc jednym unikiem. Poprawka: `tools\boss_tae_sync_hits.py` - fala startuje razem z trafieniem glownym i zachowuje swoja dlugosc; zastosowane w `files_c2232_er` dla 3000, 3001, 3006, 3007, 3008, 3010, 3012, 3013 (3023 pominiete: tam trafienia dzieli 0.9 s, to dwa osobne ciosy). Kopia sprzed zmiany: `work\boss_port\c2232.anibnd.er_before_sync.dcx`. NIE sprawdzone w grze. Do zrobienia pozniej (zgloszone przez gracza): ataki z wyskoku gracza sa slabe.


### Ataki z wyskoku v2 (2026-11-12) - NIE sprawdzone w grze

**Uwagi gracza do wersji z V08:** brak ladowania (dlugie przyklekniecie, nieresponsywne, zwlaszcza lekkie bronie); atak zaczyna sie za pozno i z przeskokiem (koniec dosuwania, poczatek spadania); trafienie nie jest zgrane z ziemia - zalezy od tego, na co sie skacze.

**Jak to dziala w ER (TAE `nuxe\chr\c0000.anibnd.dcx` + nazwy stanow z `c0000.hks`; dekompilacja hks nie dziala - 'Unimplemented opcode'):**
- Skok (202000/202020/202030): przerwanie atakiem od 0.20 s (u nas bylo 0.33 s).
- Zamach w powietrzu 31030 / 31230 / 33030 / 33230 (stan `JumpAttack_Start_Falling`): bez wlasnego ruchu postaci, bez okien przerwan; trafienie np. 0.37-0.50 s (miecz prosty).
- Ladowanie = ID zamachu + 40 (31070 itd., stan `Jump_LandAttack_Normal/Hard`): ten sam ruch na ziemi + wstawanie, trafienie w tym samym czasie co w zamachu, okna przerwan (miecz prosty: atak 0.83 s, unik 0.93 s, ruch 1.03 s). WNIOSEK (nie dowod): ladowanie wchodzi w tym samym czasie animacji, w ktorym byl zamach.
- Sa tez 31060 (petla spadania) i 31071/31072/31081/31082 (ladowania po petli) - NIE przeniesione.

**Zmiany:**
- `tools\open_air_attack.py`: JT4 (przerwanie atakiem) w skokach 900/901/902 od 0.25 s, JT1 (przyjmowanie klawisza) od 0.00 s.
- `tools\add_jump_attacks.py`: zamach GG3700/3710/4700/4710 bez okien przerwan i bez ActivateJumpTableEarly; nowe animacje ladowania ID+1 (z trafieniem) i ID+2 (bez trafienia; ten sam HKX ER xx070) z oknami przerwan w czasach ER. Tabela `jump_attack_table.h` ma nowy uklad (hitMs, swingEndMs, landHit, landFollow, landEndMs). 52 ataki, grupy 20, 23, 25-30, 32, 33, 35, 36, 38, 43. Nadal brak: R1 w grupie 30, R2 w grupie 33.
- `er_engine.cpp`: (1) okno podmiany od 230 ms skoku; (2) od chwili ataku lot balistyczny z wektorem ostatniej klatki skoku (`g_jumpV`), pion ograniczony do szczytu zwyklego skoku (`kJumpApex` 1.16 m), grawitacja `kAirAtkGravity` 16 m/s^2 trzymana przez DLL do ladowania; (3) `AirAttackTick`: ladowanie (`+0x32` = 1, `+0x1F3` = 0, grawitacja wlaczona) -> animacja ladowania zlecana przez DLL na warstwach 7 i 23 i przewijana predkoscia 4.5x do czasu zamachu (`kLandSync`, `kLandSyncSpeed`); przed trafieniem -> ID+1, po trafieniu -> ID+2; zamach skonczony w powietrzu -> koniec animacji i zwykle spadanie gry; bez inputu koniec ladowania w `landEndMs`. `AirAttackAutoEnd` usuniete.

**Sprawdzone poza gra:** DLL sie buduje; TAE a23 3700/3701/3702 ma oczekiwane zdarzenia; kontenery a2x/a3x/a4x maja 84/60/12 nowych wpisow HKX bez duplikatow ID; oryginalna gra nie uzywa ID 37xx/47xx w grupach broni.

**Niewiadome do testu:** czy `+0x1F3` jest ustawione juz przy ataku w 0.25 s (inaczej ladowanie zostanie wykryte od razu); czy przewijanie 4.5x wyglada dobrze i czy silnik je przyjmuje; czy gra sama konczy animacje ladowania na koncu HKX; czy ESD nie gubi stanu po zleceniu ladowania przez DLL; czy luk po wczesnym ataku jest naturalny.

**Powrot do V08:** `work\er_engine.V08_STABLE.cpp/.dll` (DLL takze jako `dinput8.dll`), `work\c0000.anibnd.V08_STABLE.dcx`, `work\c0000_a00_lo.V08_STABLE.dcx`, dopisane do migawki: `work\c0000_a2x/a3x/a4x.anibnd.V08_STABLE.dcx` -> `files\chr\`, `work\jump_attack_table.V08_STABLE.h` -> `native\er_engine\jump_attack_table.h`. Skrypty `tools\add_jump_attacks.py` i `tools\open_air_attack.py` sa juz w wersji v2 (stara wersja nie ma kopii).


---

## B. docs/compact.txt (bez zmian)

# Ustalenia techniczne: ds1-elden-port (port ruchu i walki z ER do DSR)

## Formaty i narzędzia
- **Kontenery i narzędzia:** BND3/DCX i TAE obsługuje SoulsFormats przez pythonnet (`tools/sfbridge.py`). Pliki moda nadpisuje ModEngine2 z folderu `dist/mods/c0000_er_engine/files`.
- **ID animacji:** `group*10000 + id`. ID wpisu HKX w binderze to ID animacji.
- **Gdzie leżą animacje:**
  - skok i spadanie a00: `c0000_a00_lo`;
  - estus: `c0000_a00_md`;
  - grupy broni: `c0000_a2x`, `c0000_a3x`, `c0000_a4x`.
- **JumpTables w TAE:**

  | JT | Działanie |
  |---|---|
  | JT1 | klawisz ataku prawą ręką |
  | JT4 | przerwanie atakiem prawą ręką |
  | JT11 | przerwanie ruchem |
  | JT26 | przewrót |
  | JT51 | Disable Fall Motion |
  | JT66 | Special Transition (po ok. 0,7 s gra zamienia skok w spadanie) |
  | JT27 | Ignore Gravity |
  | JT7 | (usunięty z animacji skoku) |

## Offsety (`DarkSoulsRemastered.exe`, SHA-256 `A45AAA36…`)
- **Hooki:**
  - PlayAnim: `base+0x37A040`;
  - obsługa wejścia: `base+0x396860`.
- **PlayerIns:** `[base+0x1C77E50]+0x68`.
- **PlayerIns+0x68 → ChrMapData.** Offset `+0x48` z DSR-Gadget dla tego exe jest błędny.
- **ChrMapData+0x18 → AnimData:**
  - `AnimData+0xA8` = prędkość animacji (float).
- **ChrMapData+0x28 → pozycja:**
  - `+0x4` = kąt;
  - `+0x10`, `+0x14`, `+0x18` = X, Y, Z.
- **ChrMapData+0x104:** bit `0x10` = DisableMapHit (wyłączenie kolizji z mapą).
- **Kierunek „przód” postaci:** `(-sin(kąt), -cos(kąt))`.

## Tempo ataków ER (`er_engine.dll`)
- **Metoda:** DLL zmienia prędkość animacji odcinkami według `attack_speed_table.h`. Tabelę generuje `tools/gen_attack_speed_table.py`.
- **Limity:**
  - zamach do trafienia: maks. ×1,35;
  - końcówka do okna następnej akcji: maks. ×2;
  - grupy ciężkie a32 i a35: końcówka maks. ×1,5;
  - nigdy nie zwalnia.
- **Zakres:** R1, R2 (tylko końcówka), atak z biegu i z backstepu (3500/4500), atak z przewrotu (3900/4900). W DSR atak z backstepu to ta sama animacja co atak z biegu.
- **Odrzucone:** przesuwanie okien w TAE dawało tylko 30–80 ms.

## Skok ER (stan JUMP_STABLE)
- **Animacje:** 900/901/902 ← ER 202030/202000/202020, z oryginalnym root motion w osi Y.
- **TAE:**
  - JT27 (Ignore Gravity) do końca wybicia;
  - JT7 usunięty.
- **DLL:**
  - kolizja z mapą wyłączona przez pierwsze 350 ms;
  - dosuwanie i obrót w locie;
  - lądowanie wykrywane na wysokości startu, potem cancel przez PlayAnim `-1`.
- **Snapshoty w `work/`:**
  - `c0000.anibnd.JUMP_STABLE.dcx`;
  - `c0000_a00_lo.JUMP_STABLE.dcx`;
  - `er_engine.JUMP_STABLE.cpp`.
- **Nie powtarzać (psuło fizykę, cofnięte):**
  - pętla w powietrzu 906;
  - animacje lądowania;
  - przenoszenie rozpędu;
  - dopisywanie JT51/JT66 do skoku;
  - podmiana spadania 1550.
- **Znane ograniczenia:**
  - skok na niższą półkę kończy się pionowym spadaniem;
  - z bronią ręce przeskakują do pozy z biegu;
  - lekki poślizg po skoku ze sprintu.

## Ataki z wyskoku (najnowsze, test w grze w toku)
- **Generator `tools/add_jump_attacks.py --groups …`:**
  - klonuje TAE DSR 3000/3300/4000/4300 do 3700/3710/4700/4710;
  - przesuwa je tak, żeby trafienie wypadało jak w ER (ER `0a0GG_031030`, `031230`, `033030`, `033230`);
  - dodaje JT51 na całą animację;
  - okna przerwań zaczynają się od końca trafienia ER + `RECOVERY_AFTER_HIT = 0.2` (wcześniej 0.35).
- **Zakres:** 52 ataki w 14 grupach (a20 a23 a25 a26 a27 a28 a29 a30 a32 a33 a35 a36 a38 a43).
  - Brak plików ER: R1 w a30, R2 w a33 i cała grupa a42 (pięści).
- **Tabela `native/er_engine/jump_attack_table.h`:** generowana, format `{anim, endMs}`. Przykłady:

  | Animacja | endMs |
  |---|---|
  | 233700 | 700 |
  | 263700 | 867 |
  | 263710 | 1367 |
  | 353700 | 1300 |

- **DLL, `AirAttackSubstitute()` na początku PlayAnimDetour:**
  - działa w oknie lotu 300–1100 ms;
  - mapowanie: 3000/3001/3002/3500 → 3700, 4000/4001/4002/4500 → 4700, 3300/3310 → 3710, 4300/4310 → 4710;
  - podmienia tylko ID obecne w tabeli; bez wpisu leci zwykły atak DSR (bez T-pozy);
  - warstwa 23 powtarza podmianę z warstwy 7, jeśli przyjdzie w ciągu 100 ms.
- **Automatyczne zakończenie, `AirAttackAutoEnd()`:**
  - wywoływane w InputDetour po `AirControlTick`;
  - po `endMs` wysyła PlayAnim `-1` na warstwy 7 i 23;
  - kasuje się, gdy na warstwie 7 ruszy nowa animacja.
- **`tools/open_air_attack.py`:** okno ataku w skokach 900–902 zaczyna się od 0.33 (już zastosowane).
- **Snapshot przed atakami z wyskoku:** `work/c0000.anibnd.before_jump_attacks.dcx`.

## Kamera
- **Plik:** `tools/port_er_lockcam.py` zapisuje do `files/param/GameParam/GameParam.parambnd.dcx` moda. LockCamParam w DSR ma 6 pól.
- **Wartości:**

  | Pole | DSR | ER |
  |---|---|---|
  | `camDistTarget` (odległość) | 4.0 | 3.8 |
  | `camFovY` | 43 | 48 |
  | `chrOrgOffset_Y` (wysokość punktu patrzenia) | 1.42 | 1.45 |
  | `lockRotXShiftRatio` (pochylenie przy locku) | 0.6 | 0.45 |

- **Pozostałe wiersze** (bossowie, ciasne miejsca) dostają tę samą zmianę względną: FOV i wysokość przez przesunięcie, odległość i pochylenie przez skalę.
- **Uwaga:** skrypt nie uruchomi się, jeśli plik moda już istnieje (uruchamiać tylko raz).

## Estus
- **Animacje:** z ER, 7585–7589 w `c0000_a00_md`.
- **Problem:** broń zostaje w ręce. ER chowa ją eventem TAE 710 HideEquippedWeapon, a DSR robi to w samej animacji (kość `R_Weapon`).
  - Zaparkowane. Możliwa droga: DSAS SoulsAssetPipeline + Havoc.dll/TagTools albo flaga w pamięci przez DLL.
- **Pusta flaszka (7588):** blokada ruchu, prawdopodobnie była już wcześniej.

## Inne
- **Szybkie wyjście:** przytrzymanie `Ctrl+Q` przez 1 s wywołuje `TerminateProcess`.
- **Build:** `cmd /c build.bat` w `native/er_engine`. Gra musi być zamknięta, inaczej DLL się nie skopiuje.
- **PowerShell:** wieloliniowy `.Replace` z "`n" zawodzi przez CRLF. Używać Edit albo `[IO.File]` z `[Environment]::NewLine`.
- **Wydanie v0.5:** `dist/release/BetterMovementAndEstus_v0.5.zip` (skok ER, tempo ataków z R2, Ctrl+Q).
  - W `build_release.ps1` poprawione czytanie README jako UTF-8.
- **Narzędzia, których nie uruchamiać na ślepo:**
  - `tools/set_jump_gravity.py`: zawiera cofnięte edycje JT51/JT66 i okien przerwań;
  - `fix_er_jump_height.py`, `add_land_anims.py`: eksperymenty, cofnięte.

## Pliki zmienione w wątku
- `native/er_engine/er_engine.cpp`, `jump_attack_table.h`, `attack_speed_table.h`, `README_release.md`, `build.bat`
- `tools/add_jump_attacks.py`, `open_air_attack.py`, `gen_attack_speed_table.py`, `port_er_lockcam.py`, `port_er_anims.py` (+ `anim_map_movement.json`), `set_jump_gravity.py`
- W `dist/mods/c0000_er_engine/files/`: `chr/c0000.anibnd.dcx`, `chr/c0000_a00_lo.anibnd.dcx`, `chr/c0000_a00_md.anibnd.dcx`, `chr/c0000_a2x/a3x/a4x.anibnd.dcx`, `param/GameParam/GameParam.parambnd.dcx`
- `docs/PLAN_PROJEKTU.md`, `build_release.ps1`

## Następne kroki
- Przetestować ataki z wyskoku (Zweihander i lekka broń, R1/R2). Jeśli będą dobre, zrobić snapshot `work/*.JUMPATK_STABLE.*`.
- Ewentualnie zamiast cancela `-1` dać animację lądowania po ataku z ER (031071).
- Później: chowanie broni przy estusie, fizyka skoku na niższą półkę, zatrzymania chodu 804–807, trzymanie R2 jak w ER, wydanie v0.6.





_________________


## Skok (v0.7, zatwierdzony, bez zmian w tej sesji)
- Animacje 900 (sprint), 901 (z miejsca), 902 (w ruchu) na warstwie 7. DLL wstrzykuje skok przez ctx+0xAE.
- Mechanizmy w `er_engine.cpp`: `AirMomentumTick` (przejęcie rozpędu w spadaniu po ok. 0,65–0,77 s), `AirControlTick`, `SetMapHit`.
- Otwarte uwagi kosmetyczne: lekkie ślizganie, przeskok rąk 1550→906, blok w sprincie.
- Ataki z wyskoku oceniono jako „bardzo kiepskie”. Nie zbadano ich, bo to osobna sesja (`docs\PROMPT_ATAKI_Z_WYSKOKU.md`).

## Unik gracza (v4, zatwierdzony)
**Offsety i funkcje**
- Handler wejścia: RVA 0x396860. DSROmniRoll hookuje go też, nasz hook jest na wierzchu.
- `FUN_140398920(ctx, dt, p3)`, dekompilacja w `work\ghidra\decomp\FUN_140398E4F.c`.
- ctx+0x93..0x96: żądanie uniku (przód/tył/lewo/prawo).
- ctx+0x8E: odskok. ctx+0xAE: skok. ctx+0x1C4: bit „jest żądanie”.
- Licznik czasu żądania (float): ctx+0xF0 + 4·(flaga−0x84).
- ctx+0x260: czas trzymania klawisza uniku.
- ctx+0x324 / +0x328: timer i flaga odskoku (DAT_141a2c0b4 ≈ 0,103 s).
- ctx+0x329: „unik także przy puszczeniu”. Próg trzymania: DAT_141a2c0a0. DAT_141c78add == 0 oznacza unik przy wciśnięciu.
- RVA 0x1A46B0 (`FUN_1401a46b0`): akcja 0x5C „klawisz uniku właśnie wciśnięty”. `FUN_1401a4610`: akcja 0x5B „trzymany”.
- Wytrzymałość: `*(int*)(*(p3+0x10)+0x3F8)`. Log: 95→70→55→30→0→−15, unik kosztuje ok. 25–30.
- p3+0x21D: namierzenie (lock-on).
- PlayAnim: RVA 0x37A040 `(ctx, out, anim, layer, a5, a6, a7)`. Warstwy 7 i 23 to całe ciało. Unik to animacja 710.

**Przyczyny**
- Krótkie jednoczesne kliknięcie kierunek+unik nie działało, bo gra nie widziała „wciśnięcia” bez kierunku.
- Unik „na wprost” wynikał z podwójnego żądania uniku: przy puszczeniu klawisza gra zgłasza +0x93 drugi raz (+0x329). DSROmniRoll loguje wtedy `reason=superseded`.
- Nieudane uniki to brak wytrzymałości. Potwierdził to log +0x3F8, nie zawieszenie.
- Zbyt długi odstęp między klawiszem uniku a kierunkiem daje odskok. To zachowanie normalne.

**Rozwiązanie w `er_engine.cpp`**
- Stałe: `kRollFlag=0x93`, `kRollBufferMs=250`, `kRollAxisHoldMs=20`.
- `RollPressDetour` (hook 0x1A46B0) zwraca „wciśnięty”, gdy `g_fakeRollPress`.
- `RollBufferPre` jest wołane przed `g_origInput`. Podaje wciśnięcie, jeśli klawisz uniku był wciśnięty bez kierunku ≤250 ms temu, a kierunek trwa ≥20 ms.
- `RollBufferTick` jest wołane po handlerze. Gasi ctx[0x329] po zgłoszeniu uniku z wciśniętym klawiszem (koniec dubla). Uczy się klawisza uniku przez głosowanie i zapisuje go w `bin\er_engine_rollkey.txt` (obecnie `6` = XBUTTON2).
- Wersje V1/V2 wstawiały flagę po handlerze, więc DSROmniRoll nie uzbrajał kierunku. V4 przepuszcza całą ścieżkę gry przez hook akcji 0x5C.
- Klawisze diagnostyczne: F6 bufor wł./wył., F7 rozpęd wł./wył., F8 znacznik i zrzut logu, F9 `ForceEndPlayerAnim()` (eksperyment, nie pomaga).
- Wariant A TAE 710 (`c0000.anibnd.dcx`): JT7 „Disable Turning” 0,07–2,33 s jak w oryginale, reszta okien skrócona z ER (przerwania od 0,67 s). Wyraźnie utrudnia zawieszenie.
- Zawieszenie po uniku występowało tylko przy lock-onie. Log DSROmniRoll pokazał `reason=timeout frames=90` (gra uważała, że 710 trwa). Nie udało się go wywołać w V4. Przyczyna nie została ustalona wprost.

## DSROmniRoll (ModEngine2 v1.01)
- Uzbraja kierunek w ścieżce gry przy wciśnięciu. `direction-lease-frames=96`.
- Logi: `toolsy\...\dllMods\DSROmniRoll\DSROmniRoll.log` (ROLL-ARM / ROLL-COMMIT / ROLL-TRAJECTORY) i `<gra>\DSROmniRoll_v1.01_Bridge.log`.
- Normalny unik: `anim-exit frames=41 hold=40`.

## Log `er_engine`
- Po pierwszej klatce gry `Log()` pisze do bufora pierścieniowego 6000×240 znaków (CRITICAL_SECTION).
- F8 zrzuca bufor do pliku i przez 3 s pisze wprost, plus 2,5 s sondy fizyki.
- Czytać tylko fragment wokół znacznika.
- `InitThread` bez DSROmniRoll czeka na okno gry + 8 s przed hookami. Poprawka nieprzetestowana (`launch_no_omniroll.bat`).

## Migawki w `work\`
- Aktualna: `er_engine.V08_STABLE.cpp/.dll`, `c0000.anibnd.V08_STABLE.dcx`, `c0000_a00_lo.V08_STABLE.dcx` (skok v0.7 + unik v4 + log w pamięci).
- Wcześniejsze: `JUMP_V07_STABLE`, `V07_DIAG`, `ROLLBUF_V1..V4`, `ROLL_V4_STABLE`, `c0000.anibnd.before_rollA.dcx`.

## Port animacji przeciwnika ER→DSR
- Narzędzie: soulstruct-havok z `toolsy\soulstruct-havok\src` (bez pip). Czyta ER hk2018 z compendium i zapisuje DSR hk2015. Kompresja spline przez `CompressAnim.exe`.
- Pliki animacji gracza w modzie mają nagłówek SDKV 20160100, którego soulstruct-havok nie czyta. Oryginalne DSR mają 20150100.
- Retarget: obrót_DSR(t) = obrót_ER(t) · ER_spocz⁻¹ · DSR_spocz w przestrzeni modelu. Pozycje przez „rodzica logicznego”. Skala S = 3,23/2,80. Kość Master niesie pozycję i obrót miednicy.
- Narzędzia w `tools\`:
  - `havokbridge.py`, `boss_bone_map.py`, `boss_anim_port.py` (obsługuje animacje bez `extractedMotion`)
  - `boss_anim_install.py` (`--base`, `--combo-window ANIM:START`)
  - `boss_attack_shapes.py`, `boss_attack_timing.py`
  - `boss_tae_sync_hits.py`, `ai_lua.py`, `make_boss_test_configs.py`
  - `roll_tae_variant.py`, `lua_decompile_invariant.ps1`

## Asylum Demon (c2232, AI 223200)
**Identyfikacja**
- c2232 = Asylum Demon, AI `223200_battle.lua` (funkcje `MiniGreaterDemon223200_*`).
- c2230 / AI 223000 = Stray Demon. Cała noc i pierwsze testy celowały błędnie w c2230. Wszystko przerobiono na c2232.
- Erdtree Avatar c4810 ma ten sam szkielet (×1/1,154, inne nazwy kości, 114/142 zmapowane).

**Zgodność ataków**
- Identyczne w ER i DSR: 3000, 3001, 3002, 3005, 3006, 3007. ER 3003 = DSR 3004.
- Różne: ER 3008 (szybszy skok z siadem: trafienie 2,60–2,87 s vs 3,70–4,10 s w DSR, atak ciałem, zachowania 180/181), ER 3010/3011/3012 (doskoki 9,1/5,9/6,4 m vs 3,8/2,2/0,3 m), ER 3015 (tupnięcie, tylko pocisk), ER 3016 (brak pliku w c4810).
- „Dosuwania” w skoku bossa nie ma w danych. Użytkownik potwierdził to na czystej grze.

**AI i combo**
- Lua 5.0. DSLuaDecompiler dekompiluje też AI ER (`nuxe\script\481000_battle.luabnd.dcx`). Przy `verify` liczby z przecinkiem to artefakt kultury PL.
- Combo w ER (efekty 17302/3/4 z TAE): 3000→3010, 3001→3010, 3002→3011, 3005→3011, 3003(=DSR 3004)→3012, 3011→3012.
- Combo w DSR: 3000→3010, 3002→3011→3012, 3003→3013.
- Okno combo to JumpTable 23. Okna AI to JT 78/79/86. Trafienie to zdarzenie TAE typu 1 (InvokeAttackBehavior, id zachowania w 3. incie). Pary zachowań: N (główne) i N+1 (fala).
- Podmiany AI: Act07 3001→3010, Act08 3004→3012, Act09 3005→3011 (po 70%). Źródło: `work\boss_ai\223200_battle.er_combos.lua`.

**Pliki w `dist\mods\boss_asylum_test\`**
- `files_c2232_er\chr\c2232.anibnd.dcx`: ER a3008, a3010, a3011, a3012 w slotach DSR. Zdarzenia na czasy ER. JT23 dodane w 3001 (od 3,00 s), 3004 (od 1,60 s), 3005 (od 2,27 s).
- `files_c2232_er_ai\script\m18_01_00_00.luabnd.dcx`: AI z combo ER.
- `files_c2232_anim3008`, `files_c2232_ai3008`: warianty testowe samego 3008.
- Launchery: `launch_asylum_er.bat`, `launch_asylum_er_anim_only.bat`, `launch_asylum_hip_er.bat`, `launch_asylum_hip_orig.bat`.
- Kopia sprzed synchronizacji fali: `work\boss_port\c2232.anibnd.er_before_sync.dcx`.
- Katalogi `files_ai`, `files_ai_combo`, `files_anim`, `files_attack`, `files_c2232_anim`, `files_c2232_ai` dotyczą c2230 i starych testów.

**Fala uderzeniowa**
- Problem: fala (N+1) startowała po końcu trafienia głównego (N), więc okno było za długie na jeden unik.
- Poprawka (`boss_tae_sync_hits.py`): fala startuje razem z trafieniem głównym i zachowuje swoją długość. Obrażenia bez zmian: blisko trafiają oba, dalej tylko fala.
- Zastosowana w 3000, 3001, 3006, 3007, 3008, 3010, 3012, 3013.

## Stan testów
- Potwierdzone w grze: port animacji ER→DSR, podmiana AI, `launch_asylum_er.bat` („działa”, widziany follow-up z ER).
- **Niesprawdzone w grze:** synchronizacja fali z trafieniem, nowy log z bufora + F8, `launch_no_omniroll.bat`.
- Niezrobione: ER 3015 (wymaga dorobienia fali/pocisku), fala przy 3008, ER 3016, porównanie okien AI i tempa na c2232.

## Zasady i pamięć
- Nic do katalogu gry. Pobieranie tylko z GitHuba do `toolsy\`, bez instalatorów. Zasoby ER tylko jako referencja lub przez skrypty działające na własnych plikach.
- Migawkuj dobre stany i wracaj do nich zamiast dokładać poprawki.
- Skrypty Pythona zapisuj do plików i uruchamiaj stamtąd. Heredoc w bashu psuje apostrofy i ukośniki.
- Pamięć: `reference-dsr-asylum-demon-ids.md`, `feedback-stable-snapshots.md`.
- Prompt dla osobnej sesji o atakach z wyskoku: `docs\PROMPT_ATAKI_Z_WYSKOKU.md`.