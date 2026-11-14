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
- **W trakcie spadania (860–938 ms) pozycja w poziomie prawie stoi** (x 1023.84 → 1023.87), choć `v_proxy` pokazuje 4,88 m/s.
  - Postać mogła uderzyć w przeszkodę (próba w ciasnym miejscu), więc to nie jest jeszcze dowód „zwolnienia z półki”.
  - Do powtórzenia na otwartej przestrzeni.
- **Pomysł z planu „1550 → 906”: odrzucony.**
  - W `c0000.anibnd` (TAE) w zakresie 900–999 są tylko 900, 901 i 902; animacji 906 nie ma.
  - Podmiana na nieistniejące ID dałaby pozę T albo nic.
  - Kod podmiany napisany i **wycofany** przed kompilacją do testu.
- **Warianty naprawy przeskoku rąk:**
  1. Dodać nowy klip lotu (906) do `c0000.anibnd` z końcówki 902: pętla ostatnich klatek; przez `tools\add_jump_anims.py`, SoulsFormats.
  2. Potem w `PlayAnimDetour`: 1550 na warstwach 8/24 w ciągu 1,5 s od skoku → 906.
  3. Alternatywa: zatrzymać ostatnią klatkę 902 na warstwach 8/24 do lądowania. Wymaga ustawiania czasu animacji (pole w AnimData; ta sama droga, co przy atakach z wyskoku).
