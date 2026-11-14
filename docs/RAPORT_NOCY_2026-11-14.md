# Raport nocy 2026-11-14

Gałąź `night-2026-11-14`. Bez commitów na `main` i bez wydań. Nocna DLL: `dist\mods\c0000_er_engine_night\bin\` (start: `dist\mods\bossy_nightreign\launch_nr_artorias_test.bat`).

## Testy na rano (w kolejności)

Wszystkie testy oprócz 4–6 startujesz z `dist\mods\bossy_nightreign\launch_nr_artorias_test.bat` (nocna DLL i paczka podnoszenia).

1. **Zawieszenie: osłona po wczytaniu** (`HangRepairV2=1`):
   - wczytać grę i od razu trzymać W;
   - w logu ma być `move flag drop ignored (load guard ...)` i nie ma być `hang repair:`;
   - potem zwykła gra; po zawieszeniu F8 i zgłoszenie.

   U mnie zadziałało w 2 sesjach (§1.1).
2. **Podnoszenie przedmiotu (§4):** podnieść przedmiot i od razu ruszyć gałką albo zrobić unik. Ruch powinien być możliwy po ok. 0,5 s, a przedmiot ma trafić do ekwipunku.
3. **Skok (§3):** sprint, skok, w locie puścić kierunek, lądowanie bez kierunku, F8 zaraz po lądowaniu. Z tego logu zrobię wygaszanie ślizgu.
4. **Centipede (§5):**
   - najpierw wariant A `launch_nr_centipede_night.bat`: czy plucie lub atak dystansowy nadal chowa model pod lawę, czy da się trafić przy mackach;
   - potem, jeśli trzeba, wariant B `launch_nr_centipede_night_b.bat`.
5. **Capra → Omen Killer (§10):** `dist\mods\bossy_nightreign\launch_nr_capra_omen.bat`. Ocenić wygląd (ogon, lewa ręka), trafienia, tempo. Poprawka 14.11: 3001 to teraz cios oboma tasakami (ER 3007).
6. **Stray Demon (§7):** `dist\mods\boss_stray_night\launch_stray_night.bat`. Ocenić ciosy 3002 i 3003 z Avatara: wygląd (skrzydła), trafienia, tempo.
7. **Gaping Dragon z AI na wzór NR (§12):** `dist\mods\bossy_nightreign\launch_nr_gaping_ai.bat`, walka w Depths.
8. **Ataki z wyskoku (§13):** `launch_nr_artorias_test.bat`.
   - skok w miejscu i ze sprintu + R1 i R2, najlepiej katana, pięści i młot. Czy lądowanie jest płynne (bez szarpnięcia i przeskoku pozy), czy katana wygląda dobrze, czy pięści i R2 młota mają atak z ER;
   - porównanie: `[Jump] LandStartTime=0` w `c0000_er_engine_night\bin\er_engine.ini` przywraca stare lądowanie.
9. **Sprint przy namierzeniu (§13):** ten sam launcher.
   - namierzyć wroga, trzymać klawisz uniku z gałką w bok, potem w tył (ponad 0,5 s). Postać powinna biec sprintem tam, gdzie gałka, z kamerą na wrogu;
   - potem F8 (w logu `lock-on sprint probe` i `free movement forced`);
   - krótkie wciśnięcie dalej ma dawać przewrót.
10. **Estus bez broni w ręce (§14):** `dist\mods\bossy_nightreign\launch_nr_estus_test.bat`. Picie w miejscu i w marszu, z bronią w prawej ręce: czy broń znika na czas picia i wraca po nim, czy w marszu nic nie miga.
11. **Po zamknięciu gry (§15), `launch_nr_estus_test.bat` albo `launch_nr_artorias_test.bat`:**
   - podnoszenie w marszu: czy postać idzie dalej, czy przedmiot trafia do ekwipunku, F8;
   - atak z wyskoku ze sprintu na płaskim i w dół: czy zniknął ślizg i dociągnięcie do ziemi, F8.
12. **Decyzje bez gry:**
   - postura: czy zaczynamy od Black Knighta (§9).

## 1. Zawieszenie postaci

### 1.1 Osłona po wczytaniu: zrobione, sprawdzone w grze
- **Kod:** `HangRepairTick` ignoruje cichy zanik bitu `0x100000` przez 2 s (`kLoadGuardMs`) po:
  - pierwszej klatce,
  - przerwie w klatkach > 1 s (wczytywanie, menu),
  - zmianie obiektu ActionCtrl (nowa postać po wczytaniu).

  W logu: `hang repair v2: move flag drop ignored (load guard, ...)`.
- **Dowód (14.11, 01:4x, sesja nocna):** `[32829 ms] hang repair v2: move flag drop ignored (load guard, 00100000 -> 00000000)`. Żadnej naprawy po wczytaniu. Wcześniej w tym samym miejscu była fałszywa naprawa przy 22 359 ms.
- Kompilacja release (`/DER_DIAG=0`): OK.

### 1.4 Sonda `HANG probe`: próg z 600 na 1200 ms (zrobione)

### 1.2 Kto zeruje bit `0x100000`: przyczyna NIE znaleziona
- **Analiza statyczna** (Ghidra `-readOnly`, wszystkie dostępy `+0x1DC`, `scratchpad\field_1dc.txt`):
  - Bit `0x100000` ustawia tylko `FUN_140387eb0`, czyli tworzenie dwóch instancji ESD dla ActionCtrl (pętla `FUN_140537e60`, potem `OR 0x100000`).
  - Żadna instrukcja w kodzie nie czyści tego bitu stałą maską.
  - Pozostałe zapisy całego słowa (`FUN_1402bc4d0`, `FUN_1402bdcd0`, `FUN_140256c90`, `FUN_14022d340`, `FUN_140390ed0`) to konstruktory albo inne klasy.
- **Logi:** przy zmianie stanu zmienia się całe słowo naraz, np. `00100000 -> 00002010` przy ataku, `-> 00000090` przy przedmiocie, `-> 00000000` przy mgle i zawieszeniu.
  - Wniosek: słowo jest przepisywane w całości (z tablicy stanu, ESD/TAE), a nie czyszczone pojedynczym bitem.
  - Zapisujący jest najpewniej w kodzie, którego statyczny skan nie widzi: wywołanie pośrednie (przez wskaźnik do pola) albo kod chroniony.
- **Próba dynamiczna:**
  - Sprzętowa pułapka zapisu (rejestr debug Dr0 na `ActionCtrl+0x1DC`, handler VEH) w nocnej DLL.
  - **Gra wywróciła się ok. 1 s po wczytaniu:** zdarzenie Windows: `BEX64`, `Exception code: 0xc0000005`, `Fault offset: 0x00000001803fd050`, moduł „unknown”.
  - Pasuje do zabezpieczenia gry przed debugowaniem (skok w losowe miejsce po wykryciu rejestrów debug).
  - Kod pułapki **usunięty**: niebezpieczny i nic nie dał.
- **Co dalej (propozycja):**
  1. Zamiast pułapki: hook na funkcjach, które gra woła przy zmianie stanu ESD (np. `FUN_140388dc0` przyjmuje słowo flag z ESD), z logiem argumentów, gdy znika `0x100000`.
  2. Albo szukanie w Ghidrze zapisów `[reg+0x1D8]` / `[reg+0x1E0]` w pobliżu pętli kopiujących struktury stanu.

## 3. Skok: ogony movementu

### Pomiar w grze (14.11, nocna DLL, skok z marszu, 2 próby)
- **Skok 902 (z marszu) kończy się po 656–657 ms**, a postać jest wtedy jeszcze w powietrzu.
  - Log: `rozped: koniec animacji skoku 902 po 657 ms`, potem `rozped: spadanie od +672 ms, poziom 4.76 m/s, pion -3.48`, lądowanie po 219–281 ms spadania.
- **W tej samej klatce gra włącza spadanie DSR 1550 na warstwach 8 i 24.** To jest przeskok rąk z bronią z punktu 3 („900 → 1550”).
  - Przyczyna: animacja skoku trwa krócej niż lot, bo DLL wydłuża lot rozpędem.
  - Gra przerywa skok przejściem JT66 około 0,66 s, zgodnie z archiwum.
- **„Zatrzymanie w locie” w tej sesji to kolizja, nie błąd.** We wszystkich trzech przypadkach pozycja X/Z stoi w tym samym punkcie (≈1024, 804, Darkroot Garden, drzewo przy ścianie), choć DLL dalej zapisuje prędkość 4,2–4,9 m/s.
- **Druga sesja (03:4x, otwarty teren, skok z marszu w bok, prędkość liczona z pozycji):**
  - wybicie ok. 5–6 m/s w poziomie;
  - spadanie po 902 utrzymuje ok. 5 m/s aż do lądowania (rozpęd DLL działa);
  - po lądowaniu z wciśniętym kierunkiem: 5,2 → 3,4 → 2,3 m/s przez ok. 150 ms, potem z powrotem do marszu 4–4,7 m/s.

  Przy skoku z marszu nie ma więc ślizgu, tylko krótki spadek prędkości.
  - Ślizg zgłaszany przez Ciebie dotyczy pewnie skoku ze sprintu (900) albo puszczenia gałki w locie. Tego nie zmierzyłem.
  - Przy próbie skoku w drugą stronę postać spadła z urwiska i zginęła (dusze 0, nic nie przepadło; gra odrodziła postać przy ognisku). Dalsze próby przerwałem, bo mapy nie widzę.
- **Do testu (Ty, ok. 2 min):**
  1. Sprint, skok, puścić kierunek w locie.
  2. Lądowanie bez wciśniętego kierunku.
  3. F8 zaraz po lądowaniu.

  Z tego logu zrobię wygaszanie rozpędu (np. 150 ms po lądowaniu bez wciśniętego kierunku).
- **Pomysł z planu „1550 → 906”: odrzucony.**
  - W `c0000.anibnd` (TAE) w zakresie 900–999 są tylko 900, 901 i 902; animacji 906 nie ma.
  - Podmiana na nieistniejące ID dałaby pozę T albo nic.
  - Kod podmiany napisany i **wycofany** przed kompilacją do testu.
- **Warianty naprawy przeskoku rąk:**
  1. Dodać nowy klip lotu (906) do `c0000.anibnd` z końcówki 902: pętla ostatnich klatek; przez `tools\add_jump_anims.py`, SoulsFormats.
  2. Potem w `PlayAnimDetour`: 1550 na warstwach 8/24 w ciągu 1,5 s od skoku → 906.
  3. Alternatywa: zatrzymać ostatnią klatkę 902 na warstwach 8/24 do lądowania. Wymaga ustawiania czasu animacji (pole w AnimData; ta sama droga, co przy atakach z wyskoku).

## 4. Podnoszenie przedmiotów (wariant gotowy do testu)
- **DSR 7412** (podniesienie z ziemi; warstwy 10/25, `a00.tae`):
  - JT8, JT27, JT7 i JT39 przez całe 2,30 s, JT19 od 0,23 s;
  - **żadnego okna przerwania** (brak JT11 ruch, JT26 unik, JT4 atak);
  - przedmiot trafia do ekwipunku przy 0,23–0,43 s (zdarzenia 112 `3100` i 128 `8`).

  Dlatego postać stoi do końca animacji.
- **Wariant:** `tools\apply_fast_pickup.py` dodaje do 7412 okna przerwania z końca picia Estusa 7587 (JT 4, 11, 16, 22, 26, 29, 31, 32) od 0,50 s.
  - Pisze do paczki nocnej `dist\mods\bossy_nightreign\files_c0000_night\chr\c0000.anibnd.dcx`; paczka deweloperska bez zmian.
  - Paczka dopisana na początek listy w `config_nr_artorias_test.toml` (kopia przed zmianą: `scratchpad\config_nr_artorias_test.toml.bak`).
  - Gra wczytuje się z nią normalnie (sprawdzone 03:4x). Samego podnoszenia nie testowałem: obok postaci nie było przedmiotu, a nie chciałem zmieniać ekwipunku w Twoim zapisie.
- **Test (Ty):**
  1. Podnieść przedmiot i od razu ruszyć gałką albo zrobić unik.
  2. Postać powinna ruszyć po ok. 0,5 s, a przedmiot ma trafić do ekwipunku.
  3. Ocenić wygląd przerwania.
  - Inny czas: `python tools\apply_fast_pickup.py --start 0.4`.
- **Odpowiednik w ER:** w `docs\er_anim_a000.md` nie ma czytelnej nazwy animacji podnoszenia (kandydaci `a000_0600xx` „Event…”), więc czasów z ER nie potwierdziłem. 0,5 s to wartość przyjęta na oko.

## 5. Centipede Demon: przyczyna „modelu pod lawą” znaleziona, dwa warianty do testu
- **Narzędzie:** `tools\boss_clip_compare.py` (tylko odczyt). Porównuje oryginalny klip DSR z przeniesionym klipem NR na tym samym szkielecie:
  - najniższy punkt ciała,
  - zakres wysokości korzenia,
  - kości o największej różnicy,
  - ścieżki przypięte do kości, których szkielet nie ma.
- **Przyczyna (dowód):**
  - W paczce `files_c5200` klip ataku **3003** to obcy plik: 4,67 s zamiast 6,53 s, 497 ścieżek, z czego **150 przypiętych do kości 347–496**, a szkielet Centipede ma 347 kości.
  - Plik nadpisany 13.11 o 02:56 (`work\boss_port\nr_ported\c5200\a00_3003.hkx`, md5 `3c0627da…`; to samo md5 w zainstalowanej paczce).
  - Gra czyta wtedy poza tablicą kości. W tym klipie najniższy punkt ciała to **−6,17 m** (DSR −1,14 m), a korzeń nie unosi się (DSR do +8,3 m).
  - To pasuje do „model wykręca się i chowa pod lawę”.
  - Poprawny port leżał w `a00_3003.hkx.bak` (6,53 s, tor korzenia jak w DSR, najniższy punkt −1,70 m).
  - Obcy plik zachowany jako `a00_3003.hkx.foreign_497tracks`.
- **„Nie da się go trafić przy mackach”:** w 3002, 3003 i 3009 kości ramion-paszcz (`L_hand*`, `R_hand*`, `*_Jaw`) odjeżdżają w NR o 15–29 m dalej niż w DSR.
  - Hitboxy i strefy obrażeń DSR jadą razem z tymi kośćami, więc są w zupełnie innym miejscu niż w oryginale.
  - Uwaga: na końcach długich łańcuchów różnice rosną z samego obrotu. U Gaping Dragona palce i skrzydła też dają 7–19 m, a tam gra działa poprawnie. To więc trop, nie dowód.
- **Paczki testowe** (paczka `files_c5200` bez zmian):
  - **A:** `launch_nr_centipede_night.bat` (`files_c5200_night`): wszystkie ataki NR, 3003 naprawiony.
  - **B:** `launch_nr_centipede_night_b.bat` (`files_c5200_night_b`): ataki NR, ale 3002, 3003 i 3009 zostają z DSR.
- **Test (Ty):**
  1. Wariant A: czy plucie albo atak dystansowy nadal chowa model; czy da się trafić przy mackach.
  2. Jeśli w A nie da się trafić: wariant B. Jeśli w B się da, winne są ramiona z klipów NR.

## 6. Gaping Dragon: wnioski (bez paczki)
- **AI NR 770000 i AI DSR 526000 używają tego samego zestawu ataków 3000–3010.**
  - Ruchy NR 9100–9171 i 4100–4123 nie są wywoływane przez skrypt walki NR, więc nie ma czego przenosić jako „nowych ataków”.
  - Klipy przeniesione wcześniej mają poprawne przypisania kości (sprawdzone narzędziem).
- **Różnice NR względem DSR w AI** (`work\boss_ai\nr_770000\770000_battle.lua` i `work\boss_ai\dsr_m10_00\526000_battle.lua`, zdekompilowane dziś):
  - Ataki NR to `ComboTunable_SuccessAngle180`: boss obraca się do celu w trakcie ataku. W DSR to głównie `NonspinningAttack` bez obrotu.
  - Czasy odnowienia: 3000/3010 15 s, 3001 20 s, 3002 10 s, 3003 35 s, 3005/3006 20 s, 3007/3009 20 s, 3008 40 s.
  - Strefy dystansu (do 5, 5–10, 10–20, 20–30 i ponad 30 m) i wybór ataku według strony, po której jest gracz.
  - Szarża 3004 powtarzana (`ComboRepeat`) po efekcie 46560 nałożonym w 3003.
  - Akcje podejścia, odejścia i obrotu (Act30–32).
- **Propozycja reworku** (decyzja Twoja, do zaplanowania):
  1. AI DSR przepisane na wzór NR: obrót w ataku, czasy odnowienia, strefy dystansu. Efekty 46550/46560 trzeba zastąpić licznikami albo wierszami SpEffect w paramach DSR.
  2. Krótsze klipy NR 3003 i 3004 zostają.
  3. Atak obszarowy wymuszający skok (np. fala przy lądowaniu 3007/3009), jak przy Artoriasie.

## 7. Stray Demon i Demon Firesage
- **Kto jest kim (z danych):** skrypty AI na mapach:
  - `c2230` = **Stray Demon** (AI 223000, Azyl `m18_01`);
  - `c2231` = **Demon Firesage** (AI 223100, Demon Ruins `m14_01`);
  - `c2232` = Asylum Demon (AI 223200).
- **Stray i Firesage mają ten sam zestaw ataków:** 3000–3007 i 3500, identyczne długości w TAE. Firesage ma 3 animacje więcej (nie ataki).
  - Asylum ma inny zestaw: 3000–3014 i 3020–3023.
  - Nazwy kości Straya i Asylum są identyczne.
- **Ataki Straya (TAE i ruch kości):**

  | ID | długość | co robi (z danych) |
  |---|---|---|
  | 3000 | 5,27 s | zamach młotem, trafienie 1,00–1,50 s, młot przed sobą na ~3,9 m wysokości |
  | 3001 | 6,17 s | zamach, trafienie 1,03–1,43 s, młot wysoko (5,6 m) |
  | 3002 | 5,77 s | zamach, trafienie 1,37–1,73 s |
  | 3003 | 6,57 s | uderzenie lewą ręką, trafienie 2,03–2,33 s |
  | 3004 | 5,43 s | zachowanie wspólne 20256 (1,20–1,70 s), potem trafienie 1,87–2,07 s; najszybszy zamach (76 m/s) |
  | 3005 | 7,70 s | **skok z uderzeniem:** miednica 3,2 m w górę, dwa trafienia 3,23–4,17 s |
  | 3006 | 5,70 s | **pocisk** (bullet 2) przy 1,67 s |
  | 3007 | 7,90 s | uderzenie 3,17 s, potem **wybuch obszarowy** (bullet 11) przy 3,50 s |

- **Archiwum 12.11:** ataki Straya 3000–3007 mają te same numery i identyfikatory trafień co Erdtree Avatar (`c4810`). Avatar robi 3003 i 3005 około dwa razy szybciej.
- **Paczka testowa:** `dist\mods\boss_stray_night\launch_stray_night.bat` (`files_c2230_night`, DLL deweloperska, bez DSROmniRoll).
  - **3002 i 3003 zamienione na klipy Avatara.**
  - Zdarzenia TAE przesunięte kotwicami: trafienie i okno następnego ataku AI.
    - 3002: trafienie 1,37–1,73 → 1,17–1,43 s, okno AI 4,73 → 4,17 s, długość 5,77 → 4,93 s;
    - 3003: trafienie 2,03–2,33 → 1,10–1,33 s, okno AI 5,43 → 3,13 s, długość 6,57 → 3,20 s.
  - **3005 zostaje z DSR:** ER 3005 to nie skok (korzeń Avatara się nie unosi, u Straya miednica idzie 3,2 m w górę).
  - AI oryginalne.
- **Ryzyko:** Avatar nie ma skrzydeł, więc skrzydła Straya stoją w 3002 i 3003 nieruchomo w pozie spoczynkowej.
- **Test (Ty, Stray w Azylu po powrocie):** wygląd 3002 i 3003 (skrzydła), czy trafienia pasują do ciosu, tempo.
- **Firesage:** te same dane, więc ta sama droga (`--dsr-chr c2231`). Najpierw trzeba sprawdzić jego szkielet, bo plik ma inne bajty niż Stray.

## 8. Capra Demon → Omen Killer (analiza wykonalności)
- **ER:** Omen Killer to najpewniej **`c3070`**:
  - AI 307000, wewnętrzna nazwa `EaterAnOldWoman_Nata` („nata” po japońsku to tasak);
  - warianty 307010–307040 z innymi brońmi.
  - Do potwierdzenia przez Ciebie: kojarzysz Omen Killera z Village of the Albinaurics z tasakiem?
- **Capra DSR `c2240`:** humanoid, ataki 3000–3005 (3,57–5,43 s) i 3500/3501.
- **Szkielety pasują bardzo dobrze:** 219 z 231 kości Capry ma odpowiednik po nazwie (po ujednoliceniu pisowni: `L Thigh` = `L_Thigh`).
  - Brakuje kości broni (zostają przy dłoni w pozie spoczynkowej, co jest w porządku), skrętu przedramion (do ręcznej mapy `ForeTwist` → `ForeArmTwist`) i ogona Capry (Omen Killer go nie ma; ogon zostanie nieruchomy).
- **ER `c3070`:** 13 ataków 3000–3015 (2,3–5,6 s), wiele z kilkoma trafieniami (do 12 w 3004). Klipy są w `c3070_div00…05.anibnd`; do rozpakowania przed portem (tylko TAE i szkielet są w głównym pliku).
- **Wniosek: wykonalne tą samą drogą co Artorias** (`tools\nr_boss_port.py` dopasowuje kości po nazwie; trzeba dodać ręczne pary dla skrętów).
  - Ryzyka:
    - ~~Capra walczy dwoma tasakami, a Omen Killer jednym~~ (błąd: Omen Killer też ma dwa tasaki, poprawka w §10);
    - ciasna arena z psami;
    - pociski i zachowania ER trzeba odtworzyć w paramach DSR.
  - Paczki nie robiłem.

## 9. Postura i cios krytyczny po przełamaniu (wstępna analiza, bez kodu)
**Cel:** jak w ER i u Artoriasa w NR. Obrażenia w posturę → przełamanie → przeciwnik oszołomiony → cios krytyczny z większymi obrażeniami.

**Co ma DSR (z danych):**
- Black Knight `c2790` ma pełny zestaw animacji ofiary i oszołomienia:
  - **2100** (2,37 s): kandydat na oszołomienie po parowaniu;
  - **2200, 2202, 2204, 2207, 2209** (2,7–4,8 s): kandydaci na animacje ofiary ciosu w plecy i riposty;
  - 2500/2510: śmierć.

  To przeciwnik, którego da się sparować w DS1, więc łańcuch „oszołomienie → riposta” (wiersze `ThrowParam` dla jego typu) już istnieje.
- Bossowie DS1 w większości nie mają animacji ofiary ani wierszy `ThrowParam` (Artorias w DSR nie ma 2100).

**Co ma Artorias w NR (`c7720`, z TAE):** animacje, których nie ma w DSR:
- **2100** (2,33 s): nowe oszołomienie, czyli NR dorobił mu stan do krytyka;
- 2000–2003: reakcje na trafienie;
- 8040–8057 i 8140–8143 (1,6–2,7 s): kandydaci na reakcje na mocne trafienia z kierunków;
- **8060** (3,23 s) i **8700** (4,87 s): kandydaci na przełamanie postury (długie, bez trafień);
- 4100/4101: chwyt;
- 5000–6003, 7000, 7400, 9000, 9500.

Znaczenie numerów 8060/8700 do potwierdzenia podglądem animacji (`render_anim.py`, jak przy 4100).

**Możliwe drogi (od najtańszej):**
1. **Przeciwnicy, których DS1 już pozwala sparować** (Black Knight i inni humanoidzi):
   - DLL liczy posturę wroga: suma obrażeń od gracza (spadek HP wroga, który DLL już umie czytać), zanikająca z czasem; próg zależny od typu wroga.
   - Po przekroczeniu progu DLL zleca wrogowi animację oszołomienia po parowaniu (2100) przez `PlayAnim`, tak jak dziś DLL zleca animacje.
   - Jeśli to ta sama animacja, której TAE otwiera okno riposty, istniejąca riposta DS1 zadziała bez nowych danych.
   - **Do sprawdzenia w pierwszej kolejności:** czy okno riposty otwiera samo zdarzenie TAE w 2100, czy dodatkowy stan ustawiany przez grę przy parowaniu (wtedy DLL musi go ustawić; szukanie w Ghidrze `-readOnly`).
2. **Bossowie bez riposty** (Artorias, Gwyn):
   - nowe animacje ofiary (z NR dla Artoriasa: 2100 + krytyk);
   - wiersze `ThrowParam` łączące animację gracza z animacją ofiary;
   - ta sama logika postury w DLL.

   Średni nakład; zależy od tego, czy portowane animacje ofiary zgrają się z animacją riposty gracza.
3. **Tylko dane:** wytrzymałość postawy w `NpcParam` daje w DS1 wyłącznie zwykłe zachwianie, bez okna krytyka. Za mało na mechanikę z ER.

**Rekomendacja na start:** droga 1 na Black Knighcie: mały przeciwnik i gotowe animacje z ripostą.
- Krok 1 (bez gry): ustalić w TAE 2100 i w Ghidrze, co otwiera okno riposty.
- Krok 2 (z grą): przełącznik w ini nocnej DLL, test na Black Knighcie.

**Krok 1, wynik (TAE Black Knighta `c2790`, 2100):**
- 2100 ma przez cały czas oszołomienia (0–1,83 s) dwa zdarzenia: JumpTable **41** i zdarzenie typu **67** (parametr 30).
- W zwykłych animacjach te zdarzenia nie występują.
- Animacje 2200 i 2202 mają zdarzenia ofiary (typ 96/109 z `15024–15026`, typ 193 i dźwięki `279003100`), czyli to ciosy krytyczne od strony ofiary.

Hipoteza: JT41 albo typ 67 to „można wykonać ripostę”. Jeśli tak, wystarczy, że DLL zleci wrogowi 2100, a ripostę DS1 obsłuży sama. To trzeba sprawdzić jednym testem w grze: przełącznik w nocnej DLL, który po np. 3 trafieniach zleca 2100 najbliższemu Black Knightowi.

## 10. Capra → Omen Killer: paczka testowa (14.11, rano, na prośbę gracza)
- **Capra w danych** to „ナタデーモン”, czyli „demon z tasakiem”. Nazwy ataków z BehaviorParam:
  - 3000 cios z góry z prawej;
  - 3001 cios z góry z lewej;
  - 3002 cios z góry z zamachem;
  - 3003 zamach poziomy z lewej;
  - 3004 cios z góry z wypadem (5 m);
  - 3005 podwójne cięcie.

  AI 224000 bez zmian.
- **ER `c3070`, zestaw `a000`:** rozpakowany przez `tools\nr_inventory.py --src ..\nuxe\chr --only c3070 --unpack c3070` (nowe opcje `--src` i `--only`). Długości i przesunięcia: `tools\er_clip_summary.py`.
- **Pary** (dobrane z liczb: kierunek ciosu, wypad, liczba trafień; animacji nie oglądałem):

  | Capra | Omen Killer ER | długość DSR → nowa | przesunięcie |
  |---|---|---|---|
  | 3000 cios z góry (prawa) | 3000 | 3,33 → 2,00 s | 2,7 → 3,3 m |
  | 3001 cios z góry (lewa) | 3007: cios oboma tasakami naraz (poprawka 14.11, wcześniej 3001, czyli cios prawą ręką) | 3,50 → 2,17 s | 2,4 → 3,5 m |
  | 3002 cios z zamachem | 3003 | 5,00 → 2,50 s | 3,5 → 4,4 m |
  | 3003 zamach poziomy | 3006 | 4,50 → 2,23 s | 2,1 → 3,4 m |
  | 3004 cios z wypadem | 3002 | 4,00 → 2,33 s | 5,0 → 6,4 m |
  | 3005 podwójne cięcie | 3004: seria 3 ciosów, trzecie trafienie dodane (`--extra-hits`) | 5,33 → 4,00 s | 3,3 → 4,8 m (wypad ER skrócony ×0,6, bez tego 8 m) |

  Okna obrotu z ER (`--nr-turn`): Capra celuje w trakcie ataku, blokady obrotu JT7 zdjęte.
- **Sprawdzone narzędziem:** wszystkie ścieżki przypięte do istniejących kości (58 zmapowanych; poza mapą końcówki, bronie, skręty przedramion i ogon).
- **Ryzyka:**
  1. Ataki są ok. 2 razy szybsze niż w DS1. To zamierzone tempo ER, ale walka będzie dużo trudniejsza.
  2. Ogon zostaje w pozie spoczynkowej (Omen Killer go nie ma), a przy pochyleniu tułowia koniec ciała schodzi 0,5–0,8 m poniżej pozy spoczynkowej. Ogon może wchodzić w podłogę.
  3. ~~Omen Killer walczy jedną bronią~~: to był błąd (założenie, nie dane). Omen Killer ma dwa tasaki; szkielet `c3070` ma kości `L_Weapon` i `R_Weapon`.
     - Pomiar rąk (`tools\er_hand_activity.py c3070 …`):
       - 3000, 3001 i 3002 to cios prawym tasakiem;
       - 3003, 3006 i 3007 to cios oboma naraz;
       - 3004 to seria, w której prowadzi prawy;
       - 3005 prowadzi lewa ręka, ale klip nie ma trafień (prawdopodobnie chwyt);
       - 3010 i 3011 są bez ruchu rąk i bez trafień;
       - 3015 to pocisk przy 2,33 s (prawdopodobnie plucie ogniem).
     - Capra 3001 (cios lewym tasakiem) dostał przez to zły klip; poprawione na 3007.
     - Plucia ogniem (3015) i 3005, 3010, 3011 nie przenoszę.
     - Zestawy `a001`–`a004` w `c3070` to warianty z innymi brońmi (AI 307010–307040: `lanthanum`, sierp, młot, `Mulberry`).
  4. Psy i arena bez zmian.
- **Test (Ty):** `dist\mods\bossy_nightreign\launch_nr_capra_omen.bat`. Ocenić wygląd każdego ataku (ogon, lewa ręka), czy trafienia pasują do ciosów i tempo. Jeśli coś wygląda źle, podaj, jak wyglądał ruch, a dobiorę inny klip.

## 11. Mapy animacji
- `docs\black_knight_anim_map.md`: wszystkie 4 bronie (miecz, wielki miecz, topór, halabarda) z nazwami ataków, czasami, przesunięciem i combo z AI.
- `docs\gwyn_anim_map.md`: 22 ataki, chwyt i dobicie, combo z AI.
- Generator: `tools\dsr_anim_map.py` (TAE + nazwy z BehaviorParam + root motion), łańcuchy AI: `tools\ai_act_chains.py`.

## 12. Gaping Dragon: AI na wzór Nightreign (14.11, decyzja gracza: tak)
- **Paczka testowa:** `dist\mods\bossy_nightreign\launch_nr_gaping_ai.bat` (`files_c5260_ai`, DLL deweloperska).
  - `chr\c5260.anibnd.dcx`: animacje NR 3000–3010 jak w `files_c5260`, teraz z oknami obrotu z NR (`nr_boss_port.py --nr c7700 --dsr c5260 --install --nr-turn --tag _ai --reuse`). Obrót w trakcie ataku mają 3001, 3002, 3007 i 3009.
  - `script\m10_00_00_00.luabnd.dcx`: nowy skrypt 526000 z `tools\make_gaping_ai.py` (tekst: `work\boss_ai\526000_battle.nr_ai.lua`). Pozostałe skrypty mapy bez zmian.
- **Ataki (z nazw BehaviorParam):**
  - 3000 chwyt prawą ręką, 3010 chwyt lewą;
  - 3001 kilka uderzeń lewą łapą;
  - 3002 zamach lewą łapą;
  - 3003 rzut brzuchem do przodu (5,8 m), zawsze przechodzi w szarżę 3004 (25 m);
  - 3005 smagnięcie ogonem (3006 po odcięciu ogona);
  - 3007 skok w miejscu i przygniecenie;
  - 3008 wielkie plucie kwasem;
  - 3009 skok do przodu z przygnieceniem (16,8 m).
- **Co jest z NR:**
  - wybór ataku według dystansu i strony, po której jesteś:
    - chwyt ręką od Twojej strony;
    - ogon i skoki, gdy jesteś za nim;
    - z daleka szarża, zamach albo skok;
  - czasy odnowienia ataków (po użyciu atak ma wagę 1 zamiast 50–100):
    - chwyt 15 s, uderzenia łapą 20 s, zamach 10 s;
    - szarża 35 s, ogon 20 s, skoki 20 s, plucie 40 s;
  - poniżej 70% HP pierwsza akcja to zawsze plucie kwasem 3008, potem plucie ma dużą wagę z bliska i z boku;
  - po udanym chwycie odchodzi na 10 m, zamiast stać;
  - akcje bez ataku: podejście, odejście, obrót o 90°.
- **Zmiany względem NR (DS1 nie ma potrzebnych funkcji):**
  - odnowienia: timery AI 0–4 (DS1 używa tylko tych); chwyt i zamach liczone w akcjach (2 i 1 akcja zamiast 15 i 10 s);
  - efekty NR 46599 (plucie zrobione), 46550 (ogon odcięty) i 46560 (szarża po 3003) zastąpione numerem AI, stanem części ciała i combo 3003 → 3004;
  - dystans w DS1 liczy się między krawędziami ciał, więc strefy NR 5 i 10 m to tu 3 i 8 m; zasięgi ataków są z oryginalnego skryptu DS1 (chwyt do 0,5 m, łapa 1,5 m, zamach 4 m);
  - skok 3009 leci zawsze 16,8 m (NR dopasowuje go do celu), więc bliżej niż 8 m zamiast niego jest skok w miejscu 3007;
  - ataki do przodu (łapa, zamach, rzut brzuchem, plucie, skok): najpierw obrót do Ciebie (do 1,5 s), potem atak; chwyty, ogon i skok w miejscu od razu, jak w NR.
- **Sprawdzone:** skrypt kompiluje się kompilatorem DSR i po dekompilacji z paczki ma tę samą treść.
- **Niesprawdzone w grze.** Jeśli skrypt ma błąd wykonania, boss będzie stał bez ataków; wtedy zgłoś.
- **Test (Ty):** `launch_nr_gaping_ai.bat`, walka w Depths. Ocenić:
  - czy boss atakuje i się nie zacina;
  - czy chwyty biorą rękę od Twojej strony;
  - czy rzadziej powtarza te same ataki;
  - czy przy 70% HP pluje kwasem;
  - czy po szarży i skokach nie ląduje w dziwnych miejscach.

## 13. Ataki z wyskoku i sprint przy namierzeniu (14.11, dzień, zgłoszenie z planu §3)
Wszystko w paczce nocnej: DLL `c0000_er_engine_night\bin`, animacje `bossy_nightreign\files_c0000_night\chr` (`c0000.anibnd.dcx` z szybkim podnoszeniem + `c0000_a2x/a3x/a4x.anibnd.dcx`). Główny mod bez zmian.

**Przyczyny z danych:**
- **Pięści (grupa 42):** ciosy pięścią zadają obrażenia zdarzeniem `InvokePCBehavior` (typ 307), a generator szukał tylko `InvokeAttackBehavior` (typ 1) i pominął grupę. Pliki z repozytorium są dobre.
- **R2 młota (grupa 33):** DSR 3300 i 4300 to tylko odnośniki do animacji 3600 i 4600, które mają trafienie. Generator teraz bierze zdarzenia stamtąd.
- **Katana (grupa 29):** pliki repozytorium są przypięte do 42 kości szkieletu ER (model się rozpada). Dotąd katana dostawała zastępczo klipy miecza zakrzywionego.
- **Topór (grupa 30), R1:** w samym ER topór nie ma własnego R1 z wyskoku. Jego TAE odtwarza klipy młota `a033_031030` i `033030`. Klip „zastępczy” to więc dokładnie to, co robi ER; nic nie zmieniam.
- **Szarpnięcie przy lądowaniu:** DLL zaczynała lądowanie od początku i przyspieszała animację w jednej klatce do czasu zamachu (do 90×), stąd przeskok pozy i przesunięcie.
- **Sprint przy namierzeniu:** kod wejścia gry (`FUN_140398920`) włącza sprint (`+0x1E4`) po 0,4 s trzymania w każdym kierunku. DLL od v0.3.0 odkłada przewrót w bok do puszczenia. Blokada jest dalej, w ruchu przy namierzeniu (tryb kroku bokiem, `p3+0x21D` = 0).

**Zrobione:**
- `tools\add_jump_attacks.py`:
  - typ 307 jako trafienie;
  - odnośniki 3300 → 3600 i 4300 → 4600;
  - własne klipy z `work\jump_port\` mają pierwszeństwo;
  - `--chr DIR` (zapis do paczki testowej).

  Tabela `jump_attack_table.h`: +R2 młota (333710, 334710), +pięści R1 i R2 (423700, 423710; oburącz DSR nie ma ataków pięścią), katana z nowymi czasami. Pozostałe wiersze bez zmian.
- `tools\er_player_port.py` (nowe): klipy gracza z ER na szkielet gracza DSR tą samą drogą co bossy (`nr_boss_port.py`, kości po nazwach, 48 z 61). Katana: 8 klipów (R1 i R2, jedną ręką i oburącz, zamach i lądowanie).
  - Podgląd renderem: postać spójna, miecz idzie znad głowy w dół i do przodu, nogi podkulone.
  - `nr_boss_port.py`: wyjście awaryjne dla kości, których przodek w ER leży w DSR dalej w kolejności (`L_Shield` i `R_Shield`). Bossów to nie dotyczy.
- **Czas animacji (Ghidra tylko do odczytu + test w grze):** PlayAnim (`0x37A040`) → `FUN_140439c90` wypełnia rekord warstwy `*(ctx+0x20) + warstwa × 0xA8`:
  - `+0x00` animacja;
  - `+0x28` czas przejścia;
  - `+0x5C` **czas startu**;
  - `+0xA4` **bieżący czas animacji** (rośnie o 1/60 s na klatkę).

  `[Jump] LandStartTime=1`: lądowanie dostaje czas zamachu w `+0x5C` warstw 7 i 23, bez przyspieszania.
  - Test (14.11, ok. 09:10, sam, Darkroot, wielki młot oburącz, 3 skoki w miejscu z R1): lądowanie startowało od 0,30 i 0,45 s (`+0xA4` 0,433 → 0,470 → 0,486…).
  - Żadnego jednoklatkowego przeskoku pozycji. Postać przesuwa się płynnie o ok. 0,4 m w ciągu 0,15 s, bo tak porusza się klip lądowania z ER.
  - Wyglądu nie oceniałem.
- **Sprint przy namierzeniu, `[Roll] LockOnSprintFree=1`** (eksperyment): gdy klawisz jest trzymany ponad próg sprintu z namierzonym wrogiem i wychyloną gałką, DLL ustawia przed kodem wejścia gry `+0x21D` = 1 (swobodny ruch) i przywraca poprzednią wartość po puszczeniu.
  - Wersja diagnostyczna loguje co 250 ms: `lock-on sprint probe` (flaga sprintu, `+0x21D` gry, osie, prędkość, kierunek).
  - Log pokaże, czy gra nadpisuje `+0x21D` co klatkę i czy prędkość dochodzi do sprintu.
  - **Niesprawdzone:** przy ognisku nie było wroga do namierzenia.
- Kompilacja release (`/DER_DIAG=0`): OK.

**Uwaga do scalenia z main:** `jump_attack_table.h` ma teraz wiersze pięści, R2 młota i nowe czasy katany. DLL zbudowana z tej gałęzi wymaga animacji z `files_c0000_night`. Przy scalaniu trzeba puścić `add_jump_attacks.py` (wszystkie grupy) na `dist\mods\c0000_er_engine\files\chr`.

## 14. Estus: broń w ręce przy piciu (14.11, dzień)
- **Przyczyna (z danych):** w głównym modzie klipy picia 7585–7589 to animacje ER 050110–050114 z Player Animations Repository.
  - Vanilla DSR chowa broń w samej animacji: skala kości `R_Weapon` = 0 (7585 od 0,2 s, 7586 całe, 7587 do 0,8 s; tak samo 7000–7113).
  - ER chowa broń zdarzeniem TAE 710 `HideEquippedWeapon`, którego DS1 nie ma. Klipy z repozytorium mają więc skalę 1 i broń zostaje w ręce.
- **Poprawka (paczka testowa, główny mod bez zmian):**
  - `tools\er_player_port.py --group 0 --clips 50110:7585 50111:7586 50112:7587 50113:7588 50114:7589 --hide-weapon --out work/estus_port --dsr-names`:
    - te same ruchy ER przeniesione na szkielet DSR;
    - `R_Weapon` ma skalę 0 w oknach 710 z TAE ER: 7585 0,20–0,83 s, 7586 całe, 7587 0–0,67 s, 7588 0–1,87 s, 7589 0,17–2,33 s.
  - `tools\apply_estus_hide.py`: `c0000_a00_md.anibnd.dcx` głównego moda z tymi 5 klipami → `bossy_nightreign\files_c0000_estus\chr`.
  - Launcher `launch_nr_estus_test.bat` = paczka nocna + ten folder.
  - `nr_boss_port.py`: nowa opcja `--scale-zero NR:KOŚĆ:T0:T1`.
- **Sprawdzone narzędziem:** skala w plikach zgodna z oknami; podgląd 7586: ręka z flaszką na wysokości twarzy.
- **Niesprawdzone w grze:**
  - czy gra stosuje skalę kości z warstwy górnej części ciała (5), na której mod odtwarza picie;
  - czy „mignięcie w marszu” znika. Jeśli nie, jego przyczyną jest coś innego, np. przejście między warstwami przy ruszaniu i zatrzymaniu.

## 15. Po teście gracza 14.11 (rano): lądowanie ataku z wyskoku i podnoszenie w ruchu
**Lądowanie (log, 11 ataków z wyskoku ze sprintu, wielki młot oburącz):**
- Lądowanie startuje od czasu zamachu (`+0x5C`).
- Po każdym lądowaniu ze sprintu prędkość pozioma rośnie lawinowo przez ok. 90 ms: 2,6 → 4 → 6,5 → 13 → 39 m/s. Rośnie z prędkości z poprzedniej klatki (`+0xD0`).
- Strażnik cofał dopiero ostatni krok (0,51–0,67 m, 78–110 ms po dotknięciu), a wcześniej postać ześlizgiwała się o ok. 0,4 m.
- Przy skoku w miejscu tego nie było.
- Przejście z pozy zamachu w pozę lądowania trwa 0,03 s (`+0x28`). To pasuje do zgłoszenia: na płaskim i w dół widać dociągnięcie do ziemi, pod górę mniej.
- **Poprawki (paczka nocna):**
  - `[Jump] LandBlend=150`: przejście 150 ms;
  - `[Jump] LandSpeedCap=5`: przez 0,4 s po dotknięciu prędkość pozioma (pośrednik `+0x60/+0x68` i `+0xD0/+0xD8`) najwyżej 5 m/s, log `landing speed … capped`.

**Podnoszenie (log):**
- 7412 (kucnięcie) skończyło się po 0,67 s, czyli okna od 0,5 s działają.
- Zaraz po nim gra zagrała 7410: drugie podniesienie z błyskiem przedmiotu, 3,3 s, blokada do 2,77 s. To był pozostały „freeze”.
- Podnoszenie nie przechodzi przez skrypt stanów gracza (ESD), tylko przez warstwy 10/25 (animacje zdarzeń). Ruch blokuje akcja gry. JT8 = nietykalność, JT27 = wyłączona grawitacja, JT7 = blokada obrotu.
- **Poprawki (paczka nocna):**
  - `tools\apply_fast_pickup.py --anims 7410 7411 7412 --walk-clone 30`: okna przerwania od 0,5 s także w 7410 i 7411. Nowe 7440–7442 to kopie do chodzenia: JT37 „ruch możliwy”, bez JT7/8/27/39, ten sam HKX.
  - `[Items] PickupWhileMoving=1`: DLL gra 7440–7442 na warstwach górnej części ciała 5/17 zamiast 7410–7412 na 10/25.
  - Zakończenie kopii: gdy gra kończy podnoszenie (nie wcześniej niż po 0,9 s), przy ataku, przewrocie albo trafieniu, najpóźniej po 2,3 s.
  - Log: `pickup: …`.
  - **Niewiadome:** czy akcja gry zwolni ruch, skoro na 10/25 nic nie gra, i czy przedmiot trafi do ekwipunku.
- Nowa DLL czekała w `work\dll_staging\bin` (gra była uruchomiona). Kopiuje się do `c0000_er_engine_night\bin` po zamknięciu gry.

## 16. Estus po teście gracza 14.11: T-pose ręki i mignięcie broni
- **Zgłoszenie:** broń znika, ale miga w połowie picia. Ręka od łokcia prosta, flaszka nie dochodzi do ust, po wypiciu chwila T-pose.
- **Przyczyna T-pose (z danych):** DSR skóruje przedramię także do `L/R_ForeTwist`. To dziecko ramienia, w łokciu. ER ma tę kość pod nazwą `L/R_ForeArmTwist`, więc przy przenoszeniu nie została dopasowana i stała w pozie spoczynkowej, w linii ramienia.
  - Kąt między przedramieniem a tą kością: w starej katanie średnio 15–35°, do 53°; po poprawce 0°.
  - Ten sam błąd był w paczce Capry (`L ForeTwist`, `R ForeTwist`).
- **Przyczyna mignięcia (log):** łatany ESD kończy etap picia (-1 na warstwach 6/18) i w tej samej klatce zaczyna następny (7585 → 7586 → 7587). Nowy etap wchodzi płynnym przejściem z warstwy pod spodem, a tam broń jest w ręce.
- **Poprawki:**
  - `nr_boss_port.py --bone-alias DSR=ER`; `er_player_port.py` zawsze podaje `L/R_ForeTwist=L/R_ForeArmTwist`.
  - Estus przeniesiony ponownie (`files_c0000_estus`), katana też: ataki z wyskoku w `files_c0000_night`; tabela bez zmian.
  - Capra przeniesiona ponownie z aliasami: `files_c2240_omen`, kopia sprzed w `work\c2240.anibnd.omen_PRE_TWIST.dcx`.
  - DLL `[Items] DrinkStageBlend=0`: etapy 7586, 7587 i 7588 dostają czas przejścia 0 w rekordzie warstwy (`+0x28`). Klipy ER są ciągłe między etapami, więc przejście nie jest potrzebne. Log `drink: stage … blend`.
- DLL czeka w `work\dll_staging\bin` i kopiuje się do `c0000_er_engine_night\bin` po zamknięciu gry.
- **Test:** `launch_nr_estus_test.bat`, picie w miejscu i w marszu. Ręka i flaszka przy ustach, bez T-pose, broń bez mignięcia. Przy okazji: atak z wyskoku katana, jeśli jest pod ręką.
