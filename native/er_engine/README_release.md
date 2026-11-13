# ER-Inspired DSR Remake v{VERSION} — Dark Souls Remastered

Ruch, uniki, skok i picie estusa w stylu Elden Ringa w Dark Souls Remastered.

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

**Konfiguracja bez okna** (dla zaawansowanych): `Setup.bat -Silent -ModEngine2Path "D:\ścieżka\do\ModEngine2" [-Shortcut]`. Ręcznie, bez `Setup.bat`: `modengine2_launcher.exe -t dsr -c "<folder moda>\ER-Inspired_DSR_Remake.toml"`.

## WAŻNE

- **Graj wyłącznie offline.** Mod zmienia działanie gry w pamięci — gra online grozi banem. Mod nie ma własnej blokady sieci; przed uruchomieniem przełącz Steama w tryb offline albo ustaw w grze start w trybie offline.
- Na innej wersji `DarkSoulsRemastered.exe` hooki się nie założą i mechaniki z DLL nie będą działać (log: `bin\er_engine.log`).

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
- `LockOnSprint=1` — przy namierzeniu przewrót przy puszczeniu klawisza (`0` = jak w DSR: przewrót w bok i w tył od razu przy wciśnięciu).

## Znane ograniczenia

- Ataki z wyskoku: przy dotknięciu ziemi widać lekkie szarpnięcie postaci i mały przeskok animacji. Katana używa animacji miecza zakrzywionego, a zwykły atak toporem — animacji młota (brak przeliczonych animacji ER dla tych grup). Młoty nie mają R2 z wyskoku, pięści nie mają ataków z wyskoku wcale. Przy bardzo długim upadku zamach kończy się w powietrzu i dalej leci zwykłe spadanie.
- Sprint przy namierzonym celu działa tylko w przód (jak w DSR); w bok i w tył postać idzie krokiem.
- Przy piciu w marszu broń w ręce chwilę miga; po trafieniu w trakcie picia flaszka zostaje na moment w ręce. Kosmetyczne.
- Lekkie ślizganie przy lądowaniu po skoku; z bronią ręce przeskakują do innej pozy przy przejściu skok → spadanie.
- Blok tarczą w sprincie wygląda nienaturalnie (animacja sprintu z ER).
- Unik kończący się na ścianie przy namierzeniu potrafi sporadycznie zawiesić postać w pozie do następnej akcji.

## Podziękowania

- **Player Animations Repository** (Nexus Mods, DSR #748) — animacje Elden Ringa przeniesione na szkielet DSR, użyte w plikach `files\chr\*.anibnd.dcx`. **Nie publikuj tej paczki dalej bez zgody autorów tego repozytorium.**
- **DSROmniRoll** (Nexus Mods, DSR #1378) i **Simple Estus Walking** — pomysły, na których wzorowane są własne implementacje przewrotu we wszystkie strony i picia w ruchu. Ich pliki nie są częścią tej paczki.
- **Mod Engine 2** (soulsmods) — ładowanie modów (nie jest dołączony).
- **MinHook** (Tsuda Kageyu) — biblioteka hooków wkompilowana w `er_engine.dll`.

Narzędzia: SoulsFormats, soulstruct, Ghidra, DS Anim Studio (szablon TAE).
