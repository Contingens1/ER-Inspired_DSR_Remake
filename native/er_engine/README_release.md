# ER-Inspired DSR Remake v{VERSION} — Dark Souls Remastered

Ruch, uniki, skok i picie estusa w stylu Elden Ringa w Dark Souls Remastered. Od 1.3 także pierwszy przerobiony boss: Rycerz Artorias z drugą fazą i atakami z Nightreign.

## Wymagania

> **Do działania moda WYMAGANY jest Mod Engine 2 w wersji wspierającej Dark Souls Remastered.**
> Bez niego mod się nie uruchomi. Mod Engine 2 nie jest dołączony do paczki.

- **Mod Engine 2 z obsługą Dark Souls Remastered** — wydanie, które w swoim folderze ma plik `launchmod_darksoulsremastered.bat` (launcher przyjmuje `-t dsr`). Starsze wydania, tylko dla Dark Souls 3 / Elden Ring, nie zadziałają. Projekt: <https://github.com/soulsmods/ModEngine2>. Rozpakuj go w dowolne miejsce (nie musi być w katalogu gry).
- **Dark Souls Remastered** (Steam), wersja exe z SHA-256 `A45AAA36…` (aktualna w chwili wydania moda). Narzędzie konfiguracji sprawdza to samo i ostrzega, jeśli masz inną.
- Windows 10 / 11.

## Uruchomienie (bez instalacji)

Mod niczego nie instaluje: nie zmienia plików gry ani Mod Engine 2. Wystarczy rozpakować folder i raz wskazać, gdzie leży Mod Engine 2.

1. Rozpakuj **całe** archiwum do zwykłego folderu, np. `Dokumenty\ER-Inspired_DSR_Remake_v{VERSION}`. **Nie rozpakowuj do katalogu gry.**
2. Uruchom **`Setup.bat`** (dwuklik). Otworzy się okno „konfiguracja”.
3. Narzędzie samo poszuka Mod Engine 2 na dyskach. Jeśli go nie znajdzie albo znajdzie nie ten, kliknij **Przeglądaj...** i wskaż folder, w którym leży `modengine2_launcher.exe`.
4. Zielony komunikat oznacza poprawny Mod Engine 2 z obsługą DSR. Kliknij **Utwórz launcher**.
5. Grę z modem uruchamiasz plikiem **`Launch_ER-Inspired_DSR_Remake.bat`** albo skrótem na pulpicie (jeśli zostawisz zaznaczone tworzenie skrótu).

**Co robi `Setup.bat`:** zapisuje ścieżkę do Mod Engine 2 i tworzy w folderze moda dwa pliki (`ER-Inspired_DSR_Remake.toml` i `Launch_ER-Inspired_DSR_Remake.bat`) oraz opcjonalny skrót na pulpicie. Nic więcej: niczego nie kopiuje do gry ani do Mod Engine 2 i niczego nie rejestruje w systemie.

Jeśli przeniesiesz folder Mod Engine 2 w inne miejsce, uruchom `Setup.bat` jeszcze raz. Folder moda możesz przenosić dowolnie; skrót na pulpicie trzeba wtedy utworzyć ponownie (znów `Setup.bat`).

**Usunięcie moda:** usuń folder moda i skrót. Pliki gry nie są modyfikowane — gra uruchomiona ze Steama działa zawsze bez moda.

## Aktualizacje *(nowe w 1.2)*

Launcher przed każdym uruchomieniem gry sprawdza na GitHubie, czy jest nowsza wersja moda (trwa to najwyżej kilka sekund; bez internetu gra startuje normalnie). Jeśli jest, pyta, czy ją pobrać i zainstalować:
- **Tak** — pobiera paczkę, wymienia pliki w folderze moda i uruchamia grę już na nowej wersji. Twoje ustawienia z `bin\er_engine.ini` zostają, launcher i ścieżka do Mod Engine 2 też. Poprzednia wersja trafia do `_backup\v<wersja>` (cofnięcie = skopiować jej zawartość z powrotem do folderu moda).
- **Nie** — gra startuje na obecnej wersji, pytanie wróci przy następnym uruchomieniu.

Aktualizacja zmienia wyłącznie pliki w folderze moda — nie dotyka gry ani Mod Engine 2. Wyłączenie sprawdzania: `CheckForUpdates=0` w `bin\er_engine.ini`. Ręczne sprawdzenie: `powershell -ExecutionPolicy Bypass -File setup\Update.ps1 -Manual`.

**Przejście z 1.0 / 1.1:** te wersje nie mają aktualizacji. Rozpakuj 1.2 do nowego folderu i uruchom `Setup.bat` jeszcze raz (nowy launcher zawiera sprawdzanie aktualizacji). Ustawienia z `bin\er_engine.ini` przenieś ręcznie, jeśli je zmieniałeś.

**Konfiguracja bez okna** (dla zaawansowanych): `Setup.bat -Silent -ModEngine2Path "D:\ścieżka\do\ModEngine2" [-Shortcut]`. Ręcznie, bez `Setup.bat`: `modengine2_launcher.exe -t dsr -c "<folder moda>\ER-Inspired_DSR_Remake.toml"`.

## WAŻNE

- **Graj wyłącznie offline.** Mod zmienia działanie gry w pamięci — gra online grozi banem. Mod nie ma własnej blokady sieci; przed uruchomieniem przełącz Steama w tryb offline albo ustaw w grze start w trybie offline.
- Na innej wersji `DarkSoulsRemastered.exe` hooki się nie założą i mechaniki z DLL nie będą działać (log: `bin\er_engine.log`).

## Nowe w 1.3

- **Rycerz Artorias — przerobiona walka z drugą fazą** (sekcja „Artorias”). Wczesna wersja: efekty drugiej fazy (dym na mieczu, iskry przed uderzeniem, wybuch przy lądowaniu skoków) są jeszcze do sprawdzenia i dopracowania.
- **Darmowy sprint:** wróg, który już walczy z graczem (goni go albo atakuje) w promieniu 40 m, też wyłącza darmowy sprint — nawet bez namierzenia i bez trafienia.
- **Zawieszenie po przewrocie:** gdy postać po przewrocie stoi w miejscu mimo wciśniętego kierunku, mod przywraca jej swobodny ruch (`HangRepair`, sekcja „Ustawienia”). Naprawa na podstawie dwóch zarejestrowanych przypadków — jeszcze nie sprawdzona na prawdziwym zawieszeniu.

## Artorias *(nowe w 1.3, wczesna wersja)*

- **Faza 1** — tylko ataki z Dark Souls, bez wzmocnienia; krótsza niż oryginalna walka.
- **Przejście** — gdy pasek HP spadnie do zera, Artorias nie ginie: klęka w animacji wzmocnienia (nie da się jej przerwać ani zadać obrażeń), odnawia całe HP i kończy wybuchem oraz dwoma pierścieniami mrocznych kul.
- **Faza 2** — wzmocnienie na stałe (mocniejsze ciosy) i nowe ataki przeniesione z Elden Ring Nightreign: długie combo, szarże z cięciem, dwa wielkie skoki pod rząd, salta zakończone skokiem z ciosem z góry; skoki kończą się małym mrocznym wybuchem przy uderzeniu w ziemię.
- Obie fazy mają razem ok. 1,2× HP oryginalnego Artoriasa. Po zabiciu w fazie 2 Artorias daje swoją duszę bossa; dusze pojawiają się z kilkusekundowym opóźnieniem.
- Wyłączenie drugiej fazy: `ArtoriasPhase2=0` w `bin\er_engine.ini` (ataki z Nightreign zostają w plikach, ale bez przejścia Artorias ginie przy 0 HP).

## Nowe w 1.2

- **Aktualizacje z poziomu launchera** (sekcja „Aktualizacje”).
- **Sprint poza walką nie zużywa wytrzymałości** (jak w ER). Przewroty, skoki i ataki kosztują zawsze.
- **Trafienie przerywa picie i użycie przedmiotu** — flaszka nie zostaje już w ręce przy powaleniu.
- **Dusze i człowieczeństwo w ruchu** — przy ich użyciu postać zwalnia do chodu jak przy estusie (wcześniej mogła biec i miała zablokowany kierunek).
- **Estus:** limit prędkości nie wyłącza się już przy długim ciągu łyków.
- **Przewroty przy namierzeniu:** przewrót skolejkowany w trakcie innej animacji (np. reakcji na trafienie) zachowuje wybrany kierunek, zamiast iść w przód; przewrót przy puszczeniu klawisza działa też przy gałce po skosie (przód–bok).
- **Halabardy:** atak z rozbiegu nie jest już nienaturalnie szybki.

## Co zmienia

| Mechanika | Opis |
|---|---|
| **Skok z ER** | Animacje wybicia z Elden Ringa (z miejsca, w marszu, ze sprintu) z przysiadem i wysokością ok. 1,15 m. Sterowanie w locie: obrót i dosuwanie gałką/WASD. Osobny przycisk skoku z miejsca i w marszu. Skok z półki w dół zachowuje rozpęd. Bez przewrotu po lądowaniu. |
| **Ataki z wyskoku z ER** *(wczesna wersja)* | Atak w trakcie skoku (R1 i R2, jedną ręką i oburącz) używa animacji ataków z wyskoku z Elden Ringa: zamach w locie, cios dokończony na ziemi, recovery w czasach ER. Kliknięcie tuż po skoku jest kolejkowane. 14 grup broni białej. |
| **Przewrót we wszystkie strony** | Przy namierzonym celu przewrót w dowolnym kierunku względem kamery zamiast 4 kierunków (własna implementacja w `er_engine.dll`). Bufor klawisza uniku: unik wciśnięty tuż przed kierunkiem nie przepada. |
| **Sprint przy namierzeniu** *(nowe w 1.1)* | Przy namierzonym celu przewrót wychodzi przy puszczeniu klawisza (jak w ER i jak w DSR bez namierzenia), więc przytrzymanie klawisza nie robi już przewrotu w bok ani w tył. Sprint przy namierzeniu działa na razie tylko w przód, jak w DSR. |
| **Przewroty i backstepy z ER** | Animacje przewrotów (4 progi obciążenia × 4 kierunki) i backstepów z Elden Ringa, z czasami ER: szybsze wyjście z przewrotu, nietykalność 13 klatek. Od 1.1 każda akcja po przewrocie ma własny czas z ER (atak najwcześniej, potem przedmiot i kolejny unik, ruch, garda) — ciężkiego przewrotu nie da się już spamować. |
| **Chód, bieg i sprint z ER** | Animacje ruchu z Elden Ringa we wszystkich 9 zestawach postaw broni (bez broni, jedną ręką, oburącz, łuk, kusza, tarcza oburącz) i 3 progach obciążenia. |
| **Tempo ataków z ER** | Ataki zostają z DSR, ale są odtwarzane szybciej w tych fragmentach, gdzie ER jest szybszy: wejście w cios do trafienia (maks. ×1,35) i końcówka do okna następnej akcji (maks. ×2). Nigdy nie zwalnia. Obejmuje R1 jedną ręką i oburącz, atak z biegu i z przewrotu dla 14 grup broni białej (bez pięści, tarcz, łuków, kusz i katalizatorów). R2: przyspieszona końcówka po trafieniu. Ciężkie bronie (wielkie młoty, wielkie topory) mają łagodniejsze przyspieszenie końcówki (maks. ×1,5). |
| **Estus w ruchu** | Picie w marszu, ze skręcaniem (także z pustej flaszki); na czas picia postać zwalnia do wolnego chodu i nie sprintuje (jak w ER). Od 1.1 czasy po łyku jak w ER: atak, unik i garda 0,2 s po rozpoczęciu odkładania flaszki, pełny ruch po 0,3 s. |
| **Kamera przy namierzeniu** | Odległość, pole widzenia i wysokość kamery przy namierzonym celu jak w Elden Ringu. |

## Sterowanie

- **Skok:** `J` (klawiatura) lub **L3** (wciśnięcie lewej gałki). Skok ze sprintu jak w DSR (przycisk przewrotu w sprincie).
- **Atak z wyskoku:** zwykły przycisk ataku (R1 / R2) w trakcie skoku.
- **Szybkie wyjście do pulpitu:** przytrzymaj `Ctrl+Q` przez 1 s (jak Alt+F4 — nie w trakcie zapisu).

## Ustawienia

`bin\er_engine.ini`:
- `OmniRoll=1` — przewrót we wszystkie strony przy namierzeniu (`0` = 4 kierunki jak w DSR),
- `RollBuffer=1` — bufor klawisza uniku (`0` = wyłączony),
- `LockOnSprint=1` — przy namierzeniu przewrót przy puszczeniu klawisza (`0` = jak w DSR: przewrót w bok i w tył od razu przy wciśnięciu),
- `FreeOutOfCombat=1` (sekcja `[Stamina]`) — poza walką sprint nie zużywa wytrzymałości; przewroty, skoki i ataki kosztują zawsze (`0` = jak w DSR). „Walka" = namierzony cel, utrata HP w ostatnich 8 s albo atak bronią w ostatnich 5 s.
- `HitCancelsItem=1` (sekcja `[Items]`) — reakcja na trafienie przerywa picie estusa / użycie przedmiotu (`0` = wyłączone; flaszka potrafi wtedy zostać w ręce przy powaleniu),
- `HangRepair=1` (sekcja `[Fixes]`) — naprawa zawieszenia po przewrocie (`0` = wyłączona),
- `ArtoriasPhase2=2` (sekcja `[Bosses]`) — druga faza Artoriasa: `2` = automatycznie (włączona, gdy w paczce są pliki bossa), `1` = włączona, `0` = wyłączona,
- `CheckForUpdates=1` (sekcja `[Update]`) — sprawdzanie nowej wersji przy uruchomieniu (`0` = wyłączone).

## Znane ograniczenia

- Ataki z wyskoku: przy dotknięciu ziemi widać lekkie szarpnięcie postaci i mały przeskok animacji. Katana używa animacji miecza zakrzywionego, a zwykły atak toporem — animacji młota (brak przeliczonych animacji ER dla tych grup). Młoty nie mają R2 z wyskoku, pięści nie mają ataków z wyskoku wcale. Przy bardzo długim upadku zamach kończy się w powietrzu i dalej leci zwykłe spadanie.
- Sprint przy namierzonym celu działa tylko w przód (jak w DSR); w bok i w tył postać idzie krokiem.
- Przy piciu w marszu broń w ręce chwilę miga. Kosmetyczne.
- Sporadycznie postać potrafi „zawisnąć” bez animacji (stoi mimo wciśniętego kierunku) do następnego trafienia lub akcji. Od 1.3 przypadek po przewrocie jest naprawiany automatycznie (`HangRepair`); jeśli zawieszenie nadal się zdarza, zgłoś je.
- Artorias (wczesna wersja): efekty drugiej fazy do sprawdzenia — dym na mieczu może być słabo widoczny, wielkość wybuchu przy skokach jeszcze strojona. Przejście do drugiej fazy potrafi ruszyć z opóźnieniem do ok. 3 s, jeśli Artorias jest w środku serii ciosów. Balans sprawdzany tylko na NG+.
- Lekkie ślizganie przy lądowaniu po skoku; z bronią ręce przeskakują do innej pozy przy przejściu skok → spadanie.
- Blok tarczą w sprincie wygląda nienaturalnie (animacja sprintu z ER).
- Unik kończący się na ścianie przy namierzeniu potrafi sporadycznie zawiesić postać w pozie do następnej akcji.

## Podziękowania

- **Player Animations Repository** (Nexus Mods, DSR #748) — animacje Elden Ringa przeniesione na szkielet DSR, użyte w plikach `files\chr\*.anibnd.dcx`. **Nie publikuj tej paczki dalej bez zgody autorów tego repozytorium.**
- **DSROmniRoll** (Nexus Mods, DSR #1378) i **Simple Estus Walking** — pomysły, na których wzorowane są własne implementacje przewrotu we wszystkie strony i picia w ruchu. Ich pliki nie są częścią tej paczki.
- **Elden Ring Nightreign** (FromSoftware) — animacje ataków Artoriasa drugiej fazy przeniesione na jego szkielet z DSR (`files\chr\c4100.anibnd.dcx`).
- **Mod Engine 2** (soulsmods) — ładowanie modów (nie jest dołączony).
- **MinHook** (Tsuda Kageyu) — biblioteka hooków wkompilowana w `er_engine.dll`.

Narzędzia: SoulsFormats, soulstruct, Ghidra, DS Anim Studio (szablon TAE).
