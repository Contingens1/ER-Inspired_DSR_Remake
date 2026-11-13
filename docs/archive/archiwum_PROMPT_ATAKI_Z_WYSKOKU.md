# Prompt startowy: ataki z wyskoku gracza

Wklej poniższy tekst jako pierwszą wiadomość w nowej sesji uruchomionej w katalogu `C:\Users\nemos\workspace\ds1-elden-port`.

---

Pracujemy nad modem do Dark Souls Remastered (DSR), który przenosi mechaniki ruchu z Elden Ring (ER). Odpowiadaj po polsku. Zadanie na tę sesję: **poprawić ataki z wyskoku gracza**. Gracz ocenił je po testach jako „bardzo kiepskie", ale nie opisał jeszcze, co dokładnie jest źle.

## Od czego zacząć

1. Zapytaj mnie, co konkretnie jest złe w atakach z wyskoku (wygląd, moment trafienia, zasięg, obrażenia, brak reakcji na przycisk, lądowanie po ataku, różnice między R1 i R2 albo między broniami). Nie zgaduj i nie zaczynaj od zmian.
2. Przeczytaj tylko to, co wymieniam w sekcji „Co przeczytać". `docs\PLAN_PROJEKTU.md` jest długi; nie czytaj go w całości.
3. Zanim cokolwiek zmienisz w `er_engine.cpp`, sprawdź, że migawka V08 istnieje (lista niżej). Po każdej wersji, którą uznam za dobrą, zapisz nową migawkę w `work\`. Po regresji wracaj do migawki zamiast dokładać poprawki.

## Jak działa atak z wyskoku teraz

- **Skok** to animacje 900 (ze sprintu), 901 (z miejsca) i 902 (w ruchu) na warstwie 7. Skok z miejsca i w ruchu wstrzykuje DLL (klawisz J albo L3).
- **Okno ataku w locie:** `tools\open_air_attack.py` otwiera w TAE skoków wejście ataku prawą ręką od oderwania od ziemi (ok. 0,33 s). Gra sama wybiera wtedy zwykły atak broni (R1/R2, jedna ręka/oburącz).
- **Podmiana na atak z ER:** `AirAttackSubstitute` w `native\er_engine\er_engine.cpp` zamienia ten atak na animację ataku z wyskoku z ER, jeśli od startu skoku minęło 300–1100 ms:
  - R1 jedną ręką (3000, 3001, 3002, 3500) → 3700,
  - R2 jedną ręką (3300, 3310) → 3710,
  - R1 oburącz (4000, 4001, 4002, 4500) → 4700,
  - R2 oburącz (4300, 4310) → 4710.
  Numer pełny to grupa broni × 10000 + numer, np. 233700.
- **Animacje i zdarzenia:** `tools\add_jump_attacks.py` dodaje animacje ER jako nowe wpisy grup broni i klonuje zdarzenia ataku DSR, przesunięte tak, żeby początek trafienia wypadł jak w ER. Dodaje też blokadę przerwania ataku spadaniem.
- **Koniec bez inputu:** `AirAttackAutoEnd` kończy atak po czasie z tabeli `native\er_engine\jump_attack_table.h` (generuje ją `add_jump_attacks.py`; nie edytuj ręcznie).
- **Fizyka skoku:** po ok. 0,65–0,77 s skoku DLL przejmuje rozpęd w spadaniu (`AirMomentumTick`). Atak z wyskoku przerywa animację skoku, więc może wchodzić w interakcję z tym kodem.

## Co przeczytać

- `native\er_engine\er_engine.cpp`: sekcje „Ataki z wyskoku (ER)", „Sterowanie w locie", „Rozped w spadaniu po skoku" oraz `PlayAnimDetour`.
- `tools\add_jump_attacks.py` i `tools\open_air_attack.py` (nagłówki opisują założenia).
- W `docs\PLAN_PROJEKTU.md` tylko sekcje: „Skok z ER - stan v0.5", „Skok v0.7 - ZATWIERDZONY", „V08 - migawka" i „Log er_engine od 2026-11-12".

## Stan i migawki

- Aktualny stan to V08: skok v0.7 + unik v4. Pliki: `work\er_engine.V08_STABLE.cpp/.dll`, `work\c0000.anibnd.V08_STABLE.dcx`, `work\c0000_a00_lo.V08_STABLE.dcx`.
- Mod gracza: `dist\mods\c0000_er_engine\` (DLL w `bin\`, dane w `files\chr\`). Uruchamianie: `launch_er_engine.bat`.
- Build: `native\er_engine\build.bat` (gra musi być zamknięta).

## Jak diagnozować

- Log `dist\mods\c0000_er_engine\bin\er_engine.log` nie rośnie w trakcie gry. Wpisy są w pamięci (ostatnie 6000 linii), a **F8** zapisuje je do pliku razem z kolejnymi 3 sekundami. Poproś mnie o F8 zaraz po problemie i czytaj tylko fragment wokół znacznika, nie cały plik.
- W logu są: klawisze i przyciski myszy z czasem trzymania, każde zlecenie animacji na warstwach 7 i 23 (z oznaczeniem gracza), wpisy „atak z wyskoku: … -> …" oraz stan fizyki przez 2,5 s po skoku i po F8.
- Gram na klawiaturze i myszy.
- Dekompilacja funkcji gry: `native\ghidra_scripts\run_decompile.ps1 -Project DSR_dec -Program DSR_decrypted.exe <adres>`; wyniki w `work\ghidra\decomp\`.

## Zasady

- Niczego nie zapisuj do katalogu gry (`F:\SteamLibrary\steamapps\common\DARK SOULS REMASTERED`); stamtąd tylko czytaj.
- Narzędzia są w `tools\` i `C:\Users\nemos\workspace\toolsy\`. Pobierać wolno tylko z GitHuba do `toolsy\`, bez instalatorów.
- Zasoby ER (`C:\Users\nemos\workspace\nuxe\`) służą jako źródło dla skryptów działających na moich plikach.
- Nie mów, że coś działa, dopóki nie przetestuję tego w grze. Podawaj wprost, co sprawdziłeś poza grą, a czego nie.
- Skrypty Pythona zapisuj do plików i uruchamiaj; wklejanie ich przez heredoc w bashu psuje apostrofy i ukośniki.
- Ważne zmiany i wyniki testów dopisuj krótko na końcu `docs\PLAN_PROJEKTU.md`.
- Bossami (katalog `dist\mods\boss_asylum_test\`, narzędzia `tools\boss_*.py`) zajmuje się inna sesja; nie ruszaj tych plików.
