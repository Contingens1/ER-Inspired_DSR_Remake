# Raport nocy 2026-11-14

Gałąź `night-2026-11-14`. Bez commitów na `main` i bez wydań. Nocna DLL: `dist\mods\c0000_er_engine_night\bin\` (start: `dist\mods\bossy_nightreign\launch_nr_artorias_test.bat`).

## Testy na rano (w kolejności)

1. **Zawieszenie, osłona po wczytaniu** (nocna DLL, `HangRepairV2=1`): wczytać grę i od razu trzymać W.
   - Postać nie powinna dostać fałszywej naprawy, a w logu ma być `move flag drop ignored (load guard ...)`.
   - Potem zwykła gra; po zawieszeniu F8 i zgłoszenie.
   - Sprawdzone przeze mnie raz (niżej). Ocena zachowania w normalnej grze należy do Ciebie.

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
