# Mapa animacji Gwyna (DSR c5370)

Stan 2026-11-14 (noc). Źródła danych:
- TAE `c5370` (czasy trafień);
- nazwy wierszy BehaviorParam (oryginalne japońskie, przetłumaczone);
- długość i root motion z HKX;
- AI `537000` (`FirewoodKing537000`, `work\boss_ai\dsr_m18_00\537000_battle.lua`).

Narzędzia: `tools\dsr_anim_map.py --chr c5370 --variation 53700`, `tools\boss_clip_summary.py --dsr c5370`, `tools\ai_act_chains.py`. Opisy są „z nazw i liczb”; żadnej animacji nie oglądałem.

**Dane walki:** HP 1550, wytrzymałość postawy (`superArmorDurability`) 100. Każde trafienie miecza ma dwa dodatkowe zachowania „płomień miecza: czubek” i „płomień miecza: całość”, czyli obrażenia od ognia z ostrza.

Długość = długość klipu HKX (wszystkie TAE Gwyna mają zdarzenie do 10 s, więc długość z TAE nie mówi nic). Przesunięcie = o ile metrów animacja przesuwa Gwyna w przód.

| ID | długość | trafienie | przesunięcie | co robi | AI |
|---|---|---|---|---|---|
| 3000 | 2,17 s | 0,37 s | 2,4 m | cięcie jedną ręką (1) | otwiera combo jednoręczne (Act01) |
| 3001 | 2,17 s | 0,40 s | 2,6 m | cięcie jedną ręką (2) | 2. cios |
| 3002 | 2,33 s | 0,47 s | 2,5 m | cięcie jedną ręką (3) | 3. cios |
| 3003 | 2,33 s | 0,63 s | 3,3 m | cios oburącz z góry | koniec 3000 > 3001 > 3002 > 3003 |
| 3004 | 2,50 s | 0,60 s | 2,6 m | silne cięcie jedną ręką (w combo) | koniec combo albo przed 3005 |
| 3005 | 2,50 s | 0,63 s | 3,7 m | zamach poziomy jedną ręką | koniec 3000 > 3001 > 3004 > 3005 |
| 3006 | 3,33 s | 1,23 s | 4,8 m | **chwyt lewą ręką** (doskok z łapaniem) | Act02: 3006, potem 3023 |
| 3008 | 2,33 s | 0,80 s | 5,9 m | pchnięcie jedną ręką z wypadem | Act03: 3008 > 3009 |
| 3009 | 2,33 s | 0,57 s | 2,6 m | zamach po pchnięciu | po 3008 |
| 3010 | 2,17 s | 0,73 s | **9,2 m** | cięcie jedną ręką z długim wypadem | Act04: 3010 > 3011 |
| 3011 | 2,83 s | 0,90 s | 3,3 m | silne cięcie oburącz po wypadzie | po 3010 |
| 3012 | 2,50 s | 0,87 s | 3,0 m | cięcie oburącz (1) | otwiera combo oburęczne (Act05) |
| 3013 | 2,50 s | 0,50 s | 2,1 m | cięcie oburącz (2) | 2. cios |
| 3014 | 2,67 s | 1,00 s | 3,3 m | silne cięcie oburącz | koniec combo |
| 3015 | 2,17 s | 0,57 s | 3,2 m | pchnięcie oburącz | 3012 > 3015 |
| 3016 | 2,67 s | 0,67 s | 2,4 m | cios oburącz od dołu w górę | koniec combo |
| 3017 | 4,33 s | — | 2,2 m | bez trafień (prawdopodobnie nieużywany) | — |
| 3018 | 3,17 s | 0,87 s | **13,2 m** | cięcie oburącz z wypadem (bliższy cel) | Act06 |
| 3019 | 3,33 s | 1,03 s | **17,0 m** | cięcie oburącz z wypadem i wyskokiem (dalszy cel; miednica 3,3 m w górę) | Act07 |
| 3020 | 2,80 s | — | −5,0 m | odskok w tył | Act08 |
| 3021 | 2,83 s | 0,77 s | 2,6 m | kopnięcie w przód | Act09 |
| 3023 | — | 1,23 s | — | chwyt lewą ręką z przejściem do rzutu (wiersz „przejście do 5371”); własnego klipu nie ma | Act02 |
| 3300 | 8,67 s | 6,77 s | 7,6 m | dobicie po rzucie (1); miednica 2,4 m w górę | po udanym chwycie |
| 3310 | 8,67 s | 7,20 s | 7,0 m | dobicie po rzucie (2) | po udanym chwycie |
| 3500 | 1,67 s | — | −0,8 m | bez trafień (krok w tył albo reakcja) | — |

**Combo z AI:**
- Act01, jedną ręką: 3000 > 3001 | 3000 > 3001 > 3002 | 3000 > 3001 > 3004 | 3000 > 3001 > 3002 > 3003 | 3000 > 3001 > 3004 > 3005.
- Act05, oburącz: 3012 > 3013 > (3016 | 3014) | 3012 > 3015.
- Act03: 3008 > 3009. Act04: 3010 > 3011.
- Reakcja na akcję gracza (Interupt): combo jednoręczne albo pojedyncze 3010, 3008 lub 3012.

**Nieataki:**
- **2100** (oszołomienie po parowaniu; Gwyna da się sparować w DS1) i **2200** (ofiara riposty): baza pod posturę, raport nocy §9.
- 2000–2083: reakcje na trafienie; 2510/2511: śmierć.

## Pod rework (`nie_czytaj-na_pozniej.md`)
- Combo Gwyna mają do 4 ciosów. Trafienia są wcześnie (0,37–1,03 s), animacje krótkie (2,2–3,3 s). Jest już szybszy niż Artorias z DS1; „drewniany” jest raczej przez przewidywalne łańcuchy i brak opóźnień, nie przez tempo.
- Wypady 3010/3018/3019 (9–17 m) już zamykają dystans.
- Brakuje:
  - ataków obszarowych wymuszających skok (np. fala ognia przy 3003 albo 3014);
  - zamachów z opóźnieniem;
  - wieloetapowych combo z ER.
- Postura: 2100 i 2200 już są, więc droga 1 z §9 (DLL zleca 2100 po przełamaniu) powinna działać jak na Black Knighcie.
