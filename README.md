\# ER-Inspired DSR Remake



Projekt modyfikacji rozgrywki i silnika dla \*\*Dark Souls: Remastered\*\*, przenoszący responsywność ruchu, mechanikę uników, skoki, picie estusa w ruchu oraz tempo walki z \*\*Elden Ringa\*\* do pierwszego Dark Souls.



\## Główne mechaniki



| Mechanika | Opis |

|---|---|

| \*\*Skok z Elden Ringa\*\* | Animacje wybicia z ER (z miejsca, w marszu, ze sprintu) z dedykowanym przyciskiem, sterowaniem w locie (obrót i dosuwanie), zachowaniem pędu przy skoku z półki oraz brakiem przewrotu po lądowaniu. |

| \*\*Ataki z wyskoku\*\* | Atak w trakcie skoku (R1 i R2, jedną ręką i oburącz) wykorzystujący animacje zamachu w locie i wykończenia na ziemi z ER wraz z kolejkowaniem wejść dla 14 grup broni białej. |

| \*\*Przewrót we wszystkie strony (Omni-Roll)\*\* | Własna implementacja w C++ (`er\_engine.dll`) umożliwiająca unik w dowolnym kierunku względem kamery przy namierzonym celu oraz buforowanie klawisza uniku. |

| \*\*Sprint przy namierzeniu\*\* | Wyzwalanie przewrotu przy puszczeniu klawisza (jak w ER), eliminujące przypadkowe uniki w bok i w tył przy próbie wejścia w sprint. |

| \*\*Przewroty i backstepy z ER\*\* | Pełny zestaw animacji uników (4 progi obciążenia × 4 kierunki) i backstepów z klatkami nietykalności i oknami wyjścia (recovery) odwzorowanymi z Elden Ringa. |

| \*\*Chód, bieg i sprint z ER\*\* | Animacje poruszania się we wszystkich 9 postawach broni i 3 progach obciążenia. |

| \*\*Tempo ataków z ER\*\* | Dynamiczne skalowanie szybkości wybranych faz ataków DSR (wejście w cios i okno recovery) pod czasy z Elden Ringa dla 14 grup broni białej. |

| \*\*Estus w ruchu\*\* | Możliwość picia i skręcania w marszu (również z pustej flaszki) z oknami wyjścia w atak, unik i gardę odwzorowanymi z ER. |

| \*\*Kamera przy namierzeniu\*\* | Dostosowana odległość, pole widzenia (FOV) oraz wysokość kamery podczas namierzania celu. |



\## Architektura repozytorium



\* `native/er\_engine/` — Kod źródłowy biblioteki hooków (`er\_engine.dll` opartej na MinHook), tabele prędkości ataków i skoków oraz skrypty budujące paczki wydań.

\* `native/ghidra\_scripts/` — Skrypty automatyzujące statyczną analizę i dekompilację funkcji silnika gry w Ghidrze.

\* `tools/` — Zestaw narzędzi w Pythonie i C# do rozpakowywania kontenerów (`.dcx`, `.bnd`), synchronizacji zdarzeń `.tae`, mapowania animacji oraz modyfikacji parametrów i stanów ESD.

\* `docs/` — Dokumentacja techniczna, mapy ID animacji oraz referencje offsetów pamięci.



\## Pobieranie i instalacja



Gotowe do uruchomienia paczki dla testerów (niewymagające kompilacji kodu) znajdują się w zakładce \*\*\[Releases](../../releases)\*\*. Szczegółowa instrukcja uruchomienia przez \*\*Mod Engine 2\*\* jest dołączona wewnątrz każdego archiwum (`README\_release.md`).



\## Podziękowania i wykorzystane zasoby



\* \*\*Player Animations Repository\*\* (Nexus Mods, DSR #748) — animacje z \*Elden Ringa\* przeniesione na szkielet DSR (wykorzystane w plikach `.anibnd.dcx`). \*\*Zabrania się dalszej redystrybucji tych plików bez zgody autorów repozytorium.\*\*

\* \*\*DSROmniRoll\*\* (Nexus Mods, DSR #1378) oraz \*\*Simple Estus Walking\*\* — inspiracje koncepcyjne dla własnych implementacji przewrotu we wszystkie strony i picia w ruchu (ich pliki nie są częścią projektu).

\* \*\*Mod Engine 2\*\* (`soulsmods`) — środowisko ładowania modyfikacji dla Dark Souls: Remastered.

\* \*\*MinHook\*\* (`Tsuda Kageyu`) — biblioteka hooków wykorzystana w `er\_engine.dll`.

\* \*\*Narzędzia społecznościowe:\*\* SoulsFormats, soulstruct, Ghidra, DS Anim Studio.



\## Disclaimer



This is an unofficial, non-commercial, fan-made modification created for educational and personal use.  

All original game assets, animations, names, and trademarks belong to \*\*FromSoftware, Inc.\*\* and \*\*Bandai Namco Entertainment Inc.\*\*  

To use this mod, you must legally own copies of the respective games (\*Dark Souls: Remastered\* and \*Elden Ring\*). Do not monetize, re-upload, or redistribute these files commercially.

