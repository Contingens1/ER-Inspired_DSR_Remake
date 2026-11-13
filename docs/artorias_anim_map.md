# Mapa animacji Artoriasa (DSR c4100 + Nightreign c7720)

Stan 2026-11-13. Dotyczy paczki `dist\mods\bossy_nightreign\files_c4100_v2` (`launch_nr_artorias_v2.bat`). Zmiany w paczce lub AI → poprawić tę mapę.

**Jak czytać:** „oglądane" = obejrzane jako arkusz póz szkieletu (`work\boss_views\*.png`); „z liczb" = opis wywnioskowany z ruchu postaci, czasów trafień i AI, bez oglądania. Gracz rozpoznaje ruchy po wyglądzie, nie po numerach — w rozmowie zawsze podawać opis obok ID.

**Podgląd:** `python work\boss_views\render_anim.py dsr a00_3008.hkx out.png 12` (jedna animacja), `python work\boss_views\anim_rows.py sheet out.png 3000 3001 …` (wiersz na animację), `python work\boss_views\anim_rows.py table [ID…]` (tabela liczb niżej). Pliki: DSR `work\boss_port\dsr_c4100\anibnd\`, przeniesione z NR `work\boss_port\nr_ported\c4100_v2\`, NR `work\boss_port\nr_c7720\anibnd\` (zestaw a001 = faza 2 w NR, włączany SpEffectem 5401). Miecz = oś −Z kości `R_weapon` (skalibrowane na 3000), 1,4 m.

## Ruchy

| ID | co to jest | skąd | AI / łańcuch (nasze AI) | uwagi |
|---|---|---|---|---|
| 3000 | cięcie z krokiem ~3 m w przód („cięcie 1") | DS1 | zwykły | z liczb |
| 3001 | cięcie z krokiem ~2,5 m („cięcie 2") | DS1 | zwykły | z liczb |
| 3002 | cięcie w dół z doskokiem ~5,5 m, ostrze przy ziemi („cięcie 3") | DS1 | zwykły | z liczb |
| 3003 | **salto w przód z cięciem** ~10 m, uderzenie w ziemię (miednica 2,5 m nad ziemią); dwa trafienia naraz (drugie „na przebicie nietykalności") | DS1 | 3003 → 3009 (0–2 razy); w NR fazie 2 na końcu 3026 | z liczb; skoki DS1 mają stałą długość, celuje obrót |
| 3004 | **szarża z pchnięciem** ~11 m prosto (2 trafienia) | DS1 | → 3024 (60%); okno combo z NR 2,07 s | z liczb |
| 3005 | **wielki skok** (miednica do 5,8 m) ~15 m w przód z uderzeniem przy lądowaniu; drugie trafienie to już w DS1 **obszar 3 m wokół miecza** (`410180`, niewidoczny) | DS1 | zwykła szarża; w fazie 2 zastępuje ją 3027 | z liczb; „pierwszy skok" z pary skoków |
| 3006 | warknięcie w miejscu, bez trafień | DS1 | zwykły | gracz: „warknięcie"; w NR fazie 2 z warknięcia startuje łańcuch 3030 → 3031 → 3032 (nasze 3017 → 3018 → 3019) |
| 3007 | **doskok z zamachem poziomym** ~9,5 m | DS1 | → 3025 (55%); okno combo z NR 2,43 s | z liczb |
| 3008 | **obrót z cięciem i salto do tyłu**: szybki obrót z cięciem (0,50 s), wysoki skok z obrotem w powietrzu (miednica 3,9 m), lądowanie ~5,5 m dalej nisko z mieczem przy ziemi | DS1 | akcja 10 (gracz za plecami) i 15 (gracz blisko z przodu) | oglądane; ulubiony ruch gracza |
| 3009 | kolejne salto z cięciem ~5,4 m, uderzenie w ziemię (2 trafienia naraz) | DS1 | po 3003 | z liczb |
| 3010 | **salto w tył z cięciem** ~6,5 m | DS1 | zwykły | z liczb |
| 3011 | **cięcie z obrotem** (1 lub 2 trafienia) prawie w miejscu | DS1 | czasem po 3007 | z liczb |
| 3012 | **pchnięcie lewą ręką** — z lewej dłoni wylatuje wachlarz 18 krótkich (3 m) ciemnych pocisków (`41500`) | DS1 | — | z parametrów |
| 3013 | **buff**: przysiad z mieczem nad ramieniem, ~5 s ładowania, przy 5,40 s wyprostowanie i ciemny wybuch (pocisk `41510`, promień 7 m), powrót do postawy | DS1 | od etapu 1 wyłączony (akcja 12) | oglądane. Mechanika: zdarzenie TAE 401 przy 0,07 s daje 5511 (4,8 s: przyjmuje 50% obrażeń, odporność na przerwanie −40 — dlatego da się go przerwać); wybuch nakłada 5510 (60 s: ataki ×1,5, obrażenia wytrzymałości ×1,35). Log 13.11: przerwany po 5,97 s z 8,0 |
| 3014 | cięcie w dół z krokiem ~2,5 m (zachowanie „cięcie 3") | DS1 | zwykły | z liczb |
| 3016 | **przejście do fazy 2** = ruch buffa 3013 (ta sama animacja): na starcie SpEffect 5512 (0% obrażeń, leczenie do pełna), odporność na przerwanie przez całą animację, przy 5,40 s wybuch `41520` nakłada 5513 (faza 2) i TAE 401 daje 5514 + zdarzenie typu 100 (dym 13910 na mieczu), przy 5,43 i 5,70 s dwa pierścienie po 12 kul Dark Bead (41540 / 41541) z dummypoly 8 | nasz (`tools\artorias_phase2.py`) | akcja 16 / przerwanie przy HP ≤ 1% | od etapu 1; kule i aura od etapu 2 (NIE testowane) |
| 3020 / 3021 | obrót w miejscu w lewo / prawo | DS1 | — | brak własnego HKX w `dsr_c4100` |
| 3023 | **pchnięcie** z krokiem ~3 m | DS1 | akcja 13 | z liczb |
| 3017 | **szarża** ~11,5 m prosto na gracza z cięciem na końcu (1,77 s) | NR 3030 | akcja 14: 3017 → 3018 → 3019 („najdłuższe combo", ~13 s) | skrócone ×0,45, wyprostowane, celuje obrót |
| 3018 | doskok ~5,5 m z dwoma szybkimi, niskimi cięciami (0,63 i 1,33 s) | NR 3031 | środek łańcucha | wyprostowane |
| 3019 | uderzenie z góry (0,53 s), przysiad, długi wypad ~8–10 m z mieczem przy ziemi z obrotem o 180°, trafienie 2,00–2,37 s | NR 3032 | koniec łańcucha | oglądane; ×0,6, okno trafienia od 2,00 s |
| 3024 | szarża ~11 m z cięciem (1,77 s) | NR 3033 | po 3004 | ×0,5, wyprostowane |
| 3025 | doskok ~6 m z dwoma cięciami | NR 3034 | po 3007 | wyprostowane |
| 3026 | **cięcie → wysoki skok w bok (~10 m w bok, 7,5 m w przód) → skok na gracza z ciosem z góry i mieczem w ziemi** (3,13 s) | NR 3026 | w NR fazie 2: 3003 → [3009] → 3026 | od 2026-11-13 **włączony w fazie 2**, skok na gracza wydłużony z ~3,6 do ~9,5 m (`--rm-scale-window 1003026:2.83:3.17:2.65`; w NR rozciągany do celu 2,5–15 m); test 2026-11-13: dolatuje (6–7 m przed skokiem → 1,25 m przy uderzeniu); od etapu 2: iskry z końca ostrza 1,90–3,20 s, mały wybuch 41530 przy 3,20 s; w NR pocisk-wybuch 465 przy lądowaniu |
| 3027 | **pierwszy z dwóch wielkich skoków** (NR-owa wersja 3005, miednica do 5,9 m, ~15 m) z uderzeniem przy lądowaniu | NR 3027 | zamiast 3005 → 3028 | w NR + wybuch 475 przy lądowaniu + atak chwytu `(70, 6, 940)`; u nas od etapu 2: iskry z końca ostrza 0,50–2,43 s i mały wybuch 41530 (2,5 m) przy 2,43 s zamiast niewidocznego obszaru 180; chwytu brak |
| 3028 | **drugi wielki skok** (miednica do 5,9 m, ~6,7 m) z uderzeniem przy lądowaniu | NR 3028 | po 3027 | ×0,6; w NR + wybuch 485 + atak chwytu `(70, 6, 940)`; u nas od etapu 2: iskry 0,13–1,83 s, mały wybuch 41530 przy 1,83 s |

### Tylko w NR (nieprzeniesione)

| ID NR | co to jest | uwagi |
|---|---|---|
| 3016 (a001) | buff fazy 2 = ruch 3013 (bez własnego HKX) z innymi efektami na mieczu, 5 pociskami przy 5,40 s (420, 421, 950, 425, 427) i znacznikiem fazy 5401 | w NR przejście fazy: AI akcja 21 przy HP < 65% |
| 4100 (a001) | **chwyt (udany)**: boss ląduje ze skoku, gracz nabity na miecz wbity pionowo w ziemię, boss klęczy na mieczu i wstaje, przy 3,4 s ponowny przysiad z wybuchem (pocisk 605), wyrwanie miecza, zamachy, niski wypad, powrót do postawy (8,7 s) | oglądane (`work\boss_views\nr_4100_przejscie.png`); rozpoznanie gracza 2026-11-13: odpala się, gdy trafi skok 3027 / 3028 w fazie 2 |
| 4101 (a001) | krótka (18 zdarzeń) | nieznane — może koniec / chybienie chwytu |
| 3022 | HKX bez wpisu w TAE | nieznane |
| 3005, 3026, 3027, 3028 (a001) | wersje fazy 2 z pociskiem-wybuchem przy lądowaniu (355, 465, 475, 485) | w nich zmiana AOE z fazy 2 |

Pozostałe animacje NR (2000–2003, 2100, 5000–5003, 6000–6003, 7000, 7400, 8040–8143, 8700, 9000, 9500, 10000, 10001, 11060–11072, 20026, 30026, 40000) — nieoglądane; prawdopodobnie reakcje na trafienie, śmierć, chodzenie.

## Liczby (z HKX i TAE paczki `c4100_v2`)

`*` = klip przeniesiony z NR (z naszymi skalowaniami). Droga = długość ścieżki miednicy; netto = przesunięcie końcowe względem kierunku startu (przód / bok, + = prawo); miednica max = najwyższy punkt (skok, gdy > ~2 m; stojąc ~1,4 m); ostrze min < 0 = miecz w ziemi. Trafienia = zdarzenia TAE typu 1 (w nawiasie zachowanie ataku), pociski = typ 2, JT23 = start okna combo.

| anim | s | droga m | netto przód / bok m | obrót ° | miednica max m (t) | głowa min m | ostrze min m (t) | trafienia (zachowanie) | pociski | JT23 |
|---|---|---|---|---|---|---|---|---|---|---|
| 3000 | 3.33 | 5.0 | +3.0 / +0.0 | +0 | 1.49 (2.77) | 1.38 | 0.51 (1.93) | 0.87–1.00 (100) | — | 1.57 |
| 3001 | 3.00 | 4.1 | +2.5 / -0.0 | +0 | 1.39 (0.80) | 1.73 | 0.47 (1.83) | 0.73–0.90 (110) | — | 1.43 |
| 3002 | 3.33 | 6.9 | +5.5 / +0.0 | +0 | 1.49 (0.97) | 1.17 | 0.17 (1.23) | 1.17–1.30 (120) | — | 2.33 |
| 3003 | 2.90 | 11.9 | +10.0 / +0.0 | +0 | 2.50 (0.90) | 1.19 | -0.11 (1.33) | 1.23–1.33 (130), 1.23–1.33 (141) | — | 2.13 |
| 3004 | 3.33 | 12.8 | +11.0 / +0.0 | +0 | 1.44 (3.03) | 1.38 | 1.30 (1.37) | 0.97–1.37 (150), 1.37–1.50 (160) | — | 2.07 |
| 3005 | 5.00 | 16.2 | +15.0 / +0.0 | +0 | 5.83 (1.93) | 0.90 | -0.13 (4.10) | 2.37–2.47 (170), 2.47–2.57 (180) | — | 4.40 |
| 3006 | 2.73 | 0.7 | -0.0 / +0.0 | +0 | 1.49 (0.67) | 1.59 | 1.44 (1.23) | — | — | 2.07 |
| 3007 | 3.83 | 11.1 | +9.5 / +0.0 | +0 | 1.47 (3.53) | 1.78 | 0.64 (2.57) | 1.40–1.60 (190) | — | 2.43 |
| 3008 | 3.83 | 10.6 | +5.5 / -0.0 | +540 | 3.90 (1.10) | 0.82 | 0.02 (2.13) | 0.50–0.67 (200) | — | 2.60 |
| 3009 | 2.47 | 7.2 | +5.4 / -0.0 | +0 | 2.50 (0.47) | 1.17 | 0.04 (1.60) | 0.80–0.90 (140), 0.80–0.90 (141) | — | 1.77 |
| 3010 | 2.00 | 8.2 | -6.5 / -0.0 | +0 | 1.98 (1.10) | 0.03 | -0.68 (1.27) | 0.87–0.97 (210) | — | 1.73 |
| 3011 | 2.50 | 4.9 | -0.0 / +0.0 | +0 | 1.44 (2.27) | 1.20 | 0.85 (0.77) | 0.87–1.17 (220), 1.17–1.33 (230) | — | 1.63 |
| 3012 | 2.43 | 1.9 | -0.0 / +0.0 | +0 | 1.38 (0.00) | 1.83 | 2.27 (2.07) | — | 0.93 (500) | 1.53 |
| 3013 | 8.00 | 2.5 | -0.0 / +0.0 | +0 | 1.71 (5.27) | 1.62 | 1.76 (5.03) | — | 5.40 (510) | 7.43 |
| 3014 | 3.27 | 3.4 | +2.5 / +0.0 | +0 | 1.47 (0.83) | 1.41 | 0.14 (0.93) | 0.83–0.97 (120) | — | 2.20 |
| 3017* | 4.67 | 12.2 | +11.5 / +0.0 | -0 | 1.44 (3.73) | 1.13 | 1.17 (1.83) | 1.77–1.90 (110) | — | 2.40 |
| 3018* | 3.83 | 7.2 | +5.5 / +0.0 | -0 | 1.46 (2.77) | 1.26 | 0.99 (1.07) | 0.63–0.73 (220), 0.73–0.77 (230), 1.33–1.50 (220) | — | 1.80 |
| 3019* | 5.33 | 15.8 | +10.5 / +0.0 | -180 | 1.65 (0.37) | 0.78 | 0.05 (2.83) | 0.53–0.63 (150), 0.63–0.67 (160), 2.00–2.37 (150) | — | 4.57 |
| 3023 | 2.33 | 4.2 | +2.9 / +0.0 | +0 | 1.38 (0.00) | 1.59 | 1.32 (1.03) | 0.70–0.87 (240) | — | 1.53 |
| 3024* | 4.67 | 11.8 | +11.0 / +0.0 | +0 | 1.44 (3.73) | 1.13 | 1.17 (1.83) | 1.77–1.90 (120) | — | 4.07 |
| 3025* | 3.83 | 7.8 | +6.0 / +0.0 | +0 | 1.46 (2.73) | 1.26 | 0.99 (1.07) | 0.63–0.73 (220), 0.73–0.77 (230), 1.33–1.50 (220) | — | 3.07 |
| 3026* | 6.33 | 24.7 | +12.9 / -10.2 | -0 | 5.69 (1.93) | 0.63 | -0.23 (3.30) | 0.87–1.10 (190), 3.13–3.23 (190) | — | 5.90 |
| 3027* | 5.00 | 16.3 | +15.0 / +0.0 | +0 | 5.91 (1.97) | 0.90 | -0.13 (4.10) | 2.37–2.47 (170), 2.47–2.53 (180) | — | 2.77 |
| 3028* | 4.33 | 7.6 | +6.7 / -0.0 | +0 | 5.93 (1.33) | 0.61 | -0.54 (0.40) | 1.77–1.93 (100) | — | 2.17 |

## Zachowania ataków (BehaviorParam `2410000xx` → AtkParam_Npc `410xxx`, nazwy z gry)

100 / 110 / 120 cięcie 1 / 2 / 3; 130 salto w przód z cięciem; 140 salto „ciągłe" (3009); 141 to samo „na przebicie nietykalności"; 150 / 160 szarża z pchnięciem 1. / 2. trafienie; 170 wielki skok (miecz, dummypoly 11–12, 250 fiz.); **180 wielki skok — obszar** (promień 3 m na dummypolu 12, 210 fiz.); 190 doskok z zamachem; 200 obrót z cięciem w tył (3008); 210 salto w tył z cięciem; 220 / 230 cięcie z obrotem 1 / 2; 240 pchnięcie; 500 lewa ręka → pocisk `41500` (wachlarz 18, 3 m, FFX 13915 / 13916, przy uderzeniu `41501` FFX 13917); 510 buff → pocisk `41510` (promień 7 m, 220 magii, FFX 13908 / 13909, nakłada 5510); 600 tułów. Ostrze = dummypoly 11–12 (punkty na mieczu do efektów). FFX Artoriasa: 13901–13917 (13906 = aura ładowania buffa na dummypolu 210, 13904 = smuga miecza, typ TAE 118).

Uwagi do liczb: 3017 i 3024 oraz 3018 i 3025 to te same klipy (różne zdarzenia TAE). Przeniesione ataki mają zachowania ataku z szablonów DSR (stąd np. 190 w 3026), nie z NR. Obrót w 3008 (+540°) i 3019 (−180°) jest w root motion; w pozostałych celuje obrót postaci (`SetTurnSpeed`).
