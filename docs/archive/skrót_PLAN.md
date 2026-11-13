### KONTEKST TECHNICZNY I ARCHITEKTURA

* **Środowisko i zasady:** Mod działa w DSR offline przez ModEngine2, korzystając z hooków ładowanych przez wstrzykiwany DLL (zlokalizowany w `test\bin`). Skrypty Pythona (i biblioteka SoulsFormats) służą wyłącznie jako narzędzia budujące I/O dla plików gry; bezpośrednie modyfikacje plików wykonujemy tylko przez ten pipeline.


* Obiekt Gracza i Fizyka:


* Obiekt gracza to `[base+0x1C77E50]` (`PlayerIns`). Ścieżka do danych animacji to `PlayerIns+0x68 -> +0x18 -> +0xA8` (prędkość animacji).


* Kontroler fizyki (`hkpCharacterProxy`) jest pod `PlayerIns+0x68 -> +0x28`.


* Kluczowe flagi fizyki kontrolera: `+0x32` (kontakt z ziemią), `+0x1F3` (stan od wybicia do lądowania), `+0x6D` (zachowanie prędkości w powietrzu).




* Obsługa wejścia (ctx): Żądanie uniku to flaga `ctx+0x93..0x96`, czas trzymania klawisza: `ctx+0x260`. Gra w domyślnej logice zgłasza unik (`+0x93`) tylko, gdy wciśnięty jest kierunek.



### STAN V08 (Aktualny, wdrożony i przetestowany w grze)



* **Skok:** Aktywowany wstrzyknięciem żądania (`ctx+0xAE`). Trzy warianty animacji z ER (zależne od wektora ruchu). Używa JT27 (Ignore Gravity) do szczytu wybicia. Kolizja z mapą tymczasowo wyłączona na 350 ms.


* **Unik z buforem (V4):** Hook na RVA `0x1A46B0`. Ponieważ DSR wymaga jednoczesnego wciśnięcia kierunku, DLL buforuje wcisk klawisza uniku przez 250 ms, czekając na kierunek. Zapobiega to gubieniu wejścia.


* **Picie Estusa w ruchu:** Działa w ESD z wyłączoną blokadą. Skrypt DLL ogranicza osie ruchu gracza (`0x1A3700`/`0x1A3750`) do 0,45 na czas animacji.


* **Tempo ataków:** DLL kontroluje i modyfikuje prędkość animacji (w locie) dla ataków z biegu/przewrotu, z zachowaniem górnych limitów (np. 1.35x od zamachu do trafienia).



### ATAKI Z WYSKOKU (Aktywna Praca - V2.1/V2.2, do weryfikacji)



* **Mechanika ER vs DSR:** W DSR atak w skoku to zlecane na bieżąco 3900 (1H) lub 4900 (2H). DLL musi je przechwycić i podmienić na ataki w stylu ER (31030/31230 itd., zmapowane w skryptach jako 3700/4700).


* **Logika wstrzykiwania (DLL w `test\bin`):**
* `AirAttackSubstitute()`: W oknie 230-1100 ms skoku przechwytuje żądania 3900/4900 i podmienia na nasze ataki 3700/4700 (warstwy 7 i 23).


* `AirAttackBuffer()`: Odzyskuje "wczesne" kliknięcia ataków (do 255 ms po skoku) i odtwarza je na etapie 255-310 ms.


* `AirMomentumTick()` i grawitacja: Po starcie ataku z wyskoku DLL wymusza własny lot balistyczny, podtrzymując grawitację 16 m/s² do momentu lądowania, blokując zerowanie `+0x1F3` przy niskich wysokościach.


* `AirAttackTick()`: Ręczne zarządzanie lądowaniem po wykryciu `+0x32 == 1`. DLL zleca animacje lądowania (ID+1 / ID+2) przewijane sztucznie w tempie x4.5 aż do momentu trafienia.




* **Do weryfikacji w grze:** Lądowania z ER, łuk/momentum po wczesnym ataku, stabilność podmiany ID, potencjalnie krótsze recovery dla broni lekkich (katana).


### ROZPOZNANY PROBLEM 

1 **Konflikt sprintu i uniku przy namierzaniu (lock-on):** Aktualnie nie da się zainicjować sprintu w trakcie lock-ona, ponieważ gra zawsze priorytetyzuje wykonanie przewrotu (roll, animacja 710) po wciśnięciu klawisza. Wymaga to modyfikacji w logice obsługi wejścia (np. w hooku handlera wejścia na RVA `0x396860` lub obsłudze uniku w `FUN_140398920`).

 2. **Zawieszenie postaci po uniku kończącym się na ścianie:**
     - Wystąpiło również na czystym naszym kodzie bez `DSROmniRoll.dll`, co jednoznacznie wyklucza `DSROmniRoll` jako przyczynę — źródło leży w animacji/TAE uniku ER
      (`700/710`) lub interakcji kontrolera fizyki ze ścianą pod koniec uniku (por. wcześniejsze testy `roll_tae_variant.py` i `F9`).
     - Uwaga pomocnicza: `OmniRollOnPlayAnim` zapisuje już `g_rollCtx` także dla lekkiego uniku `700` (wcześniej tylko `710`), więc diagnostyczne `F9` (`ForceEndPlayerAnim`)
      zadziała niezależnie od wagi ekwipunku.



### POZOSTAŁE ZADANIA (Backlog / Niedociągnięcia do poprawy)



1. **Skok (Fizyka i Wizualia):** Postać ślizga się przy lądowaniu (trzeba wygaszać rozpęd), przeskok modelu rąk z bronią 900 -> 1550 (wymaga włączenia podmiany na animację 906 na warstwach 8/24), lekkie zwolnienie z półki w sprincie.


2. **Garda w sprincie:** Postać blokując tarczą w sprincie zachowuje się nienaturalnie. Należy sprawdzić stan vanilla i rozstrzygnąć, czy zablokowanie ma ignorować gardę, przerywać sprint, czy wymagać nowej animacji górnej części ciała.


3. **Estus (Kwestie wizualne):** Zablokowanie mignięcia broni w marszu. Chowanie broni jest realizowane w DSR przez kość (`R_Weapon`), a w ER przez event TAE 710; trzeba to zunifikować (np. przez SoulsAssetPipeline).


4. **Boss (Asylum Demon - c2232):** Implementacja obrażeń dla ataku bocznego z falą uderzeniową (3015) oraz brakującej animacji (3016). Synchronizacja startu fali głównej i pomocniczej (N+1).# PLAN_PROJEKTU — Movement z Elden Ringa w Dark Souls Remastered