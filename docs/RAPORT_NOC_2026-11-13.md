# Raport z nocy 2026-11-13 (do wklejenia do PLAN_PROJEKTU.md)

Wszystko poniżej jest **NIE testowane w grze**. Główny mod (`dist\mods\c0000_er_engine`), wydanie v1.1 i gałąź `main` są nietknięte. Kod i skrypty leżą na lokalnej gałęzi `night-2026-11-13` (2 commity, bez pusha). Folder Nightreign nie został zmieniony (lista plików i daty przed i po wypakowaniu identyczne).

## 1. Co zostało zrobione

### 1.1 Poprawki gracza — paczka `dist\mods\c0000_er_engine_night\`
Kopia `files\` głównego moda + nowy DLL (dev, `ER_DIAG=1`) + własny config i launcher. Główny mod służy jako punkt powrotu (nic w nim nie zmieniono).

- **Cap prędkości wyłączał się po 5–6 łykach estusa.** Przyczyna: kolejne łyki powtarzają animację 7586 z tym samym ID, więc licznik etapu się nie zerował i po 3 s bezpiecznik „picie przerwane" zdejmował cap. Poprawka w `er_engine.cpp` (`DrinkActive`, `ItemPartMaxMs`, `TrackItemBreak`): limit dla 7586 = 22 s; przerwane picie wykrywane wprost — pełna animacja gracza na warstwie 7 (trafienie, unik, atak) kończy cap od razu. W logu z 12.11 w trakcie picia nie ma żadnych zleceń na warstwie 7, więc sygnał jest czysty; nie sprawdzone tylko, czy reakcja na trafienie idzie przez warstwę 7 (jeśli nie — po trafieniu w trakcie łyka cap potrwa do 22 s zamiast 3 s).
- **Dusze / człowieczeństwo (7500 / 7501): bieg, sprint i zablokowany kierunek.** Łatany ESD gra je na górnej części ciała (stany 1 i 15), ale TAE miało nadal JT7 i brak JT37, a DLL ich nie obejmował. Poprawka: `tools\apply_estus_walk.py` obejmuje 7500 i 7501 (zastosowane tylko do kopii w paczce nocnej), DLL traktuje je jak picie (cap 0,45, gaszenie sprintu i odskoku). Bezpiecznik: 2,6 s dla 7500, 4,7 s dla 7501 (długość TAE 2,10 / 4,13 s).
- **Halabarda, R1 z rozbiegu.** Przyczyna: w DSR cios pada już w 0,07–0,17 s (ER: 0,50 s), a generator dopasowywał długości odcinków, więc recovery 0,17 → 0,80 s było ściskane ×1,73 (jedną ręką) i ×2,0 (oburącz) — atak kończył się ok. 0,5 s zamiast 1,0 s jak w ER. Poprawka w `tools\gen_attack_speed_table.py`: reguła „nigdy wcześniej niż ER" (odcinek nie może skończyć się przed czasem ER), włączona tylko dla grupy a38 (`CUMULATIVE_GROUPS`). Skutek: 383500 / 384500 wracają do tempa DSR (×1,0); osiem innych wierszy halabard lekko zwolnione (383000, 383001, 384000, 384002, 383900, 384900, 383300, 384300).
  - Ta sama reguła zmieniłaby 63 wiersze w pozostałych grupach (głównie zamach ×1,33–1,35 → ×1,0 tam, gdzie cios DSR i tak pada wcześniej niż w ER). **Nie zastosowane** — te tempa gracz już zaakceptował. Lista: `python tools\gen_attack_speed_table.py` (wypisuje `cap … (not applied)`). Decyzja gracza.
  - Uwaga: `native\er_engine\attack_speed_table.h` na gałęzi nocnej jest już z regułą dla a38.
- `native\er_engine\build.bat` przyjmuje opcjonalny katalog wyjściowy (build testowy nie nadpisuje głównego moda).

### 1.2 Nightreign — wypakowanie i zgodność
- **Nuxe 1.2.1** (zakładka Advanced → Unpack, osobny katalog, filtr regex, typ „Elden Ring Nightreign (PC)"), sterowany przez UI Automation z PowerShella. Wynik: `nuxe_nr\` — 807 plików, 224 MB: `chr\` (anibnd / chrbnd / behbnd 46 postaci, których nie ma w ER), `script\` (377), `action\` (274). Bez tekstur. `nuxe*/` jest w `.gitignore`.
- **Zgodność z potokiem: pełna.** Wszystkie 46 anibnd czyta SoulsFormats (BND4, DCX KRAK); HKX i szkielety czyta soulstruct-havok klasami `eldenring` (z plikiem compendium; anibnd dzielone na `_divNN` mają osobne compendium na część — obsłużone); TAE czyta się jak ER; AI dekompiluje `tools\ai_lua.py dump` (0 błędów na 5 skryptach).
- **Identyfikacja (z dowodów, nie z nazw):**

| Boss | DSR | Nightreign | Dowód |
|---|---|---|---|
| Artorias | c4100 | **c7720**, AI 772000 | 130/130 kości DSR ma odpowiednik o tej samej nazwie; goal AI nazywa się `Artorius772000_Battle` |
| Gaping Dragon | c5260 | **c7700**, AI 770000 | 497/497 kości zmapowanych po nazwie |
| Centipede Demon | c5200 | **c7710**, AI 771000 (+ c7711 / c7712, AI 771100 / 771200 — osobne części) | 347/347 kości |
| Capra Demon | c2240 | **brak w plikach** | żaden szkielet nie pasuje (najlepszy wynik to zwykłe nazwy dwunożne) |

  - DLC nie jest zainstalowane (`dlc01.bhd` brak): modeli c4641, c7610, c7620, c7650, c7651, c7660 nie ma, choć ich AI (761000, 762000, 765000, 766000) leży w plikach bazowych. Jeśli Capra jest w DLC, to tam.
  - Skala szkieletów 1,000 we wszystkich trzech parach (ta sama wysokość miednicy).

### 1.3 Nightreign — co naprawdę się zmieniło w animacjach
Narzędzie `tools\nr_boss_port.py` (uogólnienie `boss_anim_port.py`: mapa kości po nazwie, skala z miednicy, konwencja kości Master wykrywana z animacji DSR) przenosi klip NR na szkielet DSR i porównuje go z oryginałem DSR.

- **Artorias: ataki 3000–3014 i 3023 to te same klipy co w DS1.** Długość i root motion identyczne, czasy trafień w TAE identyczne; średnia różnica pozycji stawów po porcie 0,1 cm w 10 z 16 animacji (to zarazem sprawdzian narzędzia). 3003, 3005, 3006, 3008, 3010, 3013 mają tę samą długość, ale różnicę 10–50 cm (poprawione pozy). **Nowe** są ataki fazy drugiej w zestawie a001: 3026, 3027, 3028, 3030, 3031, 3032, 3033 (+3034 bez zdarzeń TAE) — AI łączy 3030 → 3031 → 3032 w combo, 3028 / 3033 / 3034 to zakończenia. Klipy a000 o tych numerach to kopie starych ataków (a000 3027 = 3005).
- **Centipede Demon: 3000–3009 przerobione.** Te same ID i root motion, inne pozy (8–150 cm), 3002 i 3003 dłuższe (4,90 → 5,50 s; 5,90 → 6,53 s), 3009 krótszy (9,97 → 7,33 s). Czasy trafień prawie te same; NR ma krótsze okna obrażeń.
- **Gaping Dragon: 3000–3010 przerobione.** Różnice póz 42–264 cm, 3003 krótszy (9,83 → 7,83 s), szarża 3004 krótsza (16,00 → 11,87 s) przy tym samym dystansie 25 m.
- Raporty liczbowe: `analysis\nr_inventory.txt`; porównanie klipów (długość, root motion, różnica pozy): `analysis\nr_port_c4100.txt`, `analysis\nr_port_c5200_metrics.txt`, `analysis\nr_port_c5260_metrics.txt`, `analysis\nr_port_c4100_nr_new_metrics.txt`; kotwice TAE użyte przy instalacji: `analysis\nr_port_c5200.txt`, `analysis\nr_port_c5260.txt`, `analysis\nr_port_c4100_nr_new.txt`. AI: `work\boss_ai\nr_770000`, `nr_771000`, `nr_771100`, `nr_771200`, `nr_772000` (`*.lua`).

### 1.4 Paczka testowa bossów — `dist\mods\bossy_nightreign\`
Tylko animacje i czasy zdarzeń TAE; AI, parametry ataków i hitboxy są oryginalne z DSR. Gracz = główny mod v1.1 z `..\c0000_er_engine` (nie paczka nocna).

- `files_c5200\` — Centipede Demon, ataki 3000–3009 z animacjami NR; zdarzenia TAE przesunięte kotwicami z okien trafień obu gier.
- `files_c5260\` — Gaping Dragon, ataki 3000–3010, tak samo. DSR ma tu po 2–4 okna obrażeń na atak, NR jedno; kotwicą jest okno DSR najbliższe w czasie, pozostałe okna DSR zostają (przesunięte razem z resztą zdarzeń) — w 3003, 3005, 3006, 3010 mogą nie pasować do nowej animacji.
- `files_c4100_nr_new\` — Artorias: 7 nowych ataków NR wstawionych **na stare sloty** (pokaz, nie docelowy układ): 3028 → 3000, 3030 → 3001, 3032 → 3004, 3027 → 3005, 3026 → 3007, 3031 → 3011, 3033 → 3014. Boss używa ich wtedy, kiedy oryginalne AI wybrałoby stary atak. Ataki dwuciosowe (3026, 3031, 3032) mają obrażenia tylko w pierwszym ciosie (slot DSR ma jedno okno). Klipy 3030 i 3033 trwają 9,3 s i niosą bossa 20–25 m — zdarzenia kończą się ok. 4,4 s.
- Ported HKX: `work\boss_port\nr_ported\<chr>\`. Rozpakowane źródła: `work\boss_port\nr_c77xx\`, `work\boss_port\dsr_c4100|c5200|c5260\`.

### 1.5 Nowe narzędzia (`tools\`)
`nr_inventory.py` (inwentarz NR, dopasowanie szkieletów, `--unpack`), `nr_boss_port.py` (port wsadowy + `--install` + `--pair NR:DSR` + `--tag`), `make_nr_boss_configs.py` (configi i launchery), `tae_dump_anim.py` (zdarzenia wybranej animacji, BND3 / `--bnd4`).

## 2. Testy na rano (po kolei)

1. **`dist\mods\c0000_er_engine_night\launch_er_engine_night.bat`** — poprawki gracza.
   - Estus: wypić ciągiem 8–10 łyków, trzymając kierunek i sprint. Oczekiwane: wolny chód do końca. Potem łyk przerwany unikiem i atakiem — cap ma zniknąć od razu. Jeśli się da: dać się trafić w trakcie łyka i sprawdzić, czy po trafieniu postać nie chodzi wolno (F8, w logu `drink stage`).
   - Dusza i człowieczeństwo: użyć w marszu. Oczekiwane: wolny chód, skręcanie działa, brak biegu i sprintu, po animacji normalny ruch. Zwrócić uwagę, czy cap nie zostaje po zakończeniu.
   - Halabarda (np. Black Knight Halberd), R1 z rozbiegu jedną ręką i oburącz: recovery ma być wyraźnie dłuższe niż w v1.1. Przy okazji R1 / R2 z miejsca i atak z przewrotu — lekko wolniejsze końcówki.
   - Regresja: zwykłe picie, pusta flaszka, przewroty, sprint przy namierzeniu — bez zmian względem v1.1.
2. **`dist\mods\bossy_nightreign\launch_nr_centipede.bat`** — Centipede Demon (Demon Ruins). Patrzeć: czy model się nie rozpada, czy stopy / ogon nie pływają, czy obrażenia padają w chwili ciosu, czy boss nie zastyga po ataku (3002, 3003, 3009 mają inną długość).
3. **`dist\mods\bossy_nightreign\launch_nr_gaping.bat`** — Gaping Dragon (Depths). To samo; osobno szarża (3004, o 4 s krótsza) i 3003.
4. **`dist\mods\bossy_nightreign\launch_nr_artorias_new.bat`** — Artorias (DLC). Patrzeć: wygląd nowych ataków, czy długie doskoki 3030 / 3033 nie wynoszą go w ścianę areny, czy po ataku wraca do AI. Obrażenia i hitboxy będą niedopasowane — to znane.
5. `launch_nr_all.bat` — wszystkie trzy naraz (dla wygody, gdy pojedyncze działają).

Przy każdym błędzie bossa: F8 i numer animacji z logu (`er_engine.log` głównego moda).

## 3. Otwarte / zablokowane

- **Capra Demon** — nie ma go w wypakowanych plikach bazowych; do sprawdzenia po zainstalowaniu DLC Nightreign (albo nie ma go w NR wcale).
- **Artorias docelowo:** nowe ataki powinny dostać własne ID (nowe wpisy HKX + nowe animacje w TAE z hitboxami dla drugiego ciosu) i AI przepisane z `772000_battle.lua` (combo 3030 → 3031 → 3032, zakończenia 3028 / 3033 / 3034, czasy odnowienia). Nie zaczęte — dodawanie nowych wpisów do BND3 / TAE nie było dotąd robione w projekcie.
- **AI Centipede / Gaping** z NR (771000, 770000) — zdekompilowane, nieprzenoszone. NR ma też animacje 9100–9171 i 4100–4123 (nowe reakcje / fazy), których DSR nie ma.
- **Części Centipede c7711 / c7712** — niezbadane (prawdopodobnie odcięte części).
- **Reguła „nigdy wcześniej niż ER" dla pozostałych grup broni** — decyzja gracza (63 wiersze).
- **Brak animacji ataków z wyskoku dla lekkich broni i R2 w grupie 33** — nie ruszane (wymaga przeliczenia klipów ER z 42 ścieżkami na szkielet DSR).
- **Stamina poza walką, recovery po obaleniu, mnożniki obrażeń ataków z wyskoku, kurz przy Asylum Demonie, auto-aktualizacja** — nie zaczęte (wymagają badania w Ghidrze albo decyzji projektowych).
- **Blok w sprincie, sekcja „do rozważenia"** — pominięte zgodnie z poleceniem.
- Po akceptacji testu 1: skopiować `bin\er_engine.dll` + `dinput8.dll` i `files\chr\c0000.anibnd.dcx` z paczki nocnej do głównego moda, migawka `work\V12_…`, merge gałęzi `night-2026-11-13` do `main`, ewentualnie wydanie v1.2.
