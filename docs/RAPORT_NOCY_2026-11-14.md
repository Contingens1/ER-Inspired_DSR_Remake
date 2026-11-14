# Raport nocy 2026-11-14

Gałąź `night-2026-11-14`. Bez commitów na `main` i bez wydań. Nocna DLL: `dist\mods\c0000_er_engine_night\bin\` (start: `dist\mods\bossy_nightreign\launch_nr_artorias_test.bat`).

## Testy na rano (w kolejności)

**Uwaga o zapisie:** przy pomiarze skoku (03:4x) postać spadła z urwiska w Darkroot Garden i zginęła. Dusze 0, nic nie przepadło, ale gra zapisała odrodzenie przy ognisku. Jeśli chcesz wrócić do miejsca sprzed nocy, przywróć zapis z Save Organizera.

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
5. **Stray Demon (§7):** `dist\mods\boss_stray_night\launch_stray_night.bat`. Ocenić ciosy 3002 i 3003 z Avatara: wygląd (skrzydła), trafienia, tempo.
6. **Decyzje bez gry:**
   - Gaping Dragon: czy rework AI na wzór NR (§6);
   - Capra → Omen Killer: czy robić port, i potwierdzenie, że Omen Killer to ten z tasakiem (§8);
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
    - Capra walczy dwoma tasakami, a Omen Killer jednym;
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
