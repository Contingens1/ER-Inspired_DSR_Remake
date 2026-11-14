# Mapa animacji Black Knighta (DSR c2790)

Stan 2026-11-14 (noc). Źródła danych:
- TAE `c2790` (czasy trafień);
- nazwy wierszy BehaviorParam/AtkParam (oryginalne japońskie, przetłumaczone niżej);
- root motion z HKX;
- AI `279000`–`279003` (`work\boss_ai\dsr_m18_00`).

Narzędzia: `tools\dsr_anim_map.py --chr c2790 --variation 27900 --ranges 3000-3999 13000-13999 23000-23999 33000-33999` i `tools\ai_act_chains.py`. Opisy są „z nazw i liczb”; żadnej animacji nie oglądałem.

**Jak czytać:**
- Black Knight ma cztery wersje z tym samym modelem, różniące się bronią i przesunięciem numerów animacji (`NpcParam.animIdOffset`).
- AI zawsze woła ataki 3000–3014, a gra dodaje przesunięcie (np. AI wielkiego miecza woła 3010, gra gra 13010).
- „Przesunięcie” = o ile metrów animacja przesuwa postać w przód (root motion).

| broń | AI | przesunięcie ID | wiersze NpcParam |
|---|---|---|---|
| miecz (`BlackKnight_Sword`) | 279000 | 0 → 3000–3007 | 279000, 279050, 279060, 279070 |
| wielki miecz (`BlackKnight_Lar_Sw`) | 279001 | 10000 → 13000–13014 | 279001, 279051, 279061 |
| topór (`BlackKnight_Ax`) | 279002 | 20000 → 23000–23011 | 279020, 279052, 279062 |
| halabarda (`BlackKnight_Spear`) | 279003 | 30000 → 33000–33013 | 279010, 279030, 279053, 279063 |

Wspólne dla wszystkich: HP 355, wytrzymałość postawy (`superArmorDurability`) 80. Animacje nieataków patrz [na końcu](#nieataki-wsp%C3%B3lne).

## Miecz (AI 279000)

| ID | trafienie | przesunięcie | co robi | AI |
|---|---|---|---|---|
| 3000 | 0,63 s | 2,3 m | cięcie skośne z góry od lewego ramienia | otwiera każde combo |
| 3001 | 0,67 s | 1,6 m | cięcie poziome z prawej | 2. cios combo |
| 3002 | 0,67 s | 0,3 m | pchnięcie | 3. cios combo albo osobno (Act04) |
| 3003 | 1,00 s | 1,4 m | cięcie z góry w dół | koniec najdłuższego combo |
| 3004 | 1,07 s | 2,6 m | cięcie z zamachem (wersja w combo) | koniec combo; Act06: 3004 → 3007 |
| 3005 | 1,00 s | 1,4 m | cięcie z zamachem (pojedyncze) | Act01, z obrotem do celu |
| 3006 | 0,80 s | 1,7 m | uderzenie tarczą | — |
| 3007 | 1,00 s | 4,9 m | szarża z pchnięciem | Act05; po 3004 |

**Combo (Act02):** 3000 > 3001 | 3000 > 3001 > 3002 | 3000 > 3001 > 3002 > 3004 | 3000 > 3001 > 3002 > 3003.

## Wielki miecz (AI 279001)

| ID | trafienie | przesunięcie | co robi | AI |
|---|---|---|---|---|
| 13000 | 0,67 s | 2,2 m | zamach poziomy z prawej (1) | otwiera combo |
| 13001 | 0,63 s | 1,4 m | zamach poziomy z lewej (1) | 2. cios |
| 13002 | 0,67 s | 1,7 m | zamach z prawej (2) | 3. cios |
| 13003 | 1,00 s | 1,8 m | obrót i cios z góry | koniec combo |
| 13004 | 0,93 s | 2,3 m | cios z góry (wersja w combo) | koniec combo |
| 13005 | 0,93 s | 2,3 m | cios z góry (pojedynczy) | otwiera combo Act06 |
| 13006 | 0,63 s | 1,4 m | zamach z lewej (3) | 2. cios Act06 |
| 13007 | 1,07 s | 2,1 m | pchnięcie (pojedyncze) | Act05 |
| 13008 | 0,93 s | 1,5 m | pchnięcie (w combo) | koniec combo |
| 13009 | 0,93 s | 1,8 m | obrót i pchnięcie | koniec combo |
| 13010 | 1,07 s | **6,8 m** | 2–3 kroki naprzód i cios z góry | Act01, z obrotem do celu |
| 13011 | 1,17 s | 4,0 m | 2–3 kroki naprzód i pchnięcie | — |
| 13012 | 0,80 s | 1,7 m | uderzenie tarczą | — |
| 13013 | 1,23 s | 2,0 m | „łowca smoków”: pchnięcie jedną ręką w górę | Act07 |
| 13014 | 0,87 i 1,50 s | 2,8 m | „łowca smoków”: zamach oburącz z dołu w górę (2 trafienia) | Act04, Act08 |

**Combo:**
- Act02: 13000 > 13001 > (13003 | 13009 | 13002 | 13004 | 13008), także w wersjach z 13002 przed końcówką;
- Act06: 13005 > 13006 > (13002 | 13004 | 13008).

## Topór (AI 279002)

| ID | trafienie | przesunięcie | co robi | AI |
|---|---|---|---|---|
| 23000 | 0,77 s | 2,2 m | ukośny zamach z prawej w dół | otwiera combo |
| 23001 | 0,90 s | 2,1 m | ukośny zamach z lewej w dół | 2. cios |
| 23002 | 0,63 s | 1,8 m | zamach z prawej od dołu w górę | 3. cios |
| 23003 | 1,20 s | **5,6 m** | uderzenie z prawej-góry w ziemię (wersja w combo) | koniec combo |
| 23004 | 1,00 s | 1,4 m | uderzenie z prawej-góry w ziemię (pojedyncze) | Act04, Act05 |
| 23005 | 0,63 s | 1,3 m | podcięcie od dołu w górę | — |
| 23007 | 0,77 s | 1,7 m | zamach z lewej + podcięcie (combo) | — |
| 23008 | 0,67 s | 4,2 m | 1–2 kroki naprzód i zamach | Act01, z obrotem do celu |
| 23009 | 1,20 s | 5,6 m | 2–3 kroki naprzód i uderzenie w ziemię | reakcja (Interupt) |
| 23010 | 1,23 s | 5,3 m | „łowca smoków”: wyskok i cios z góry | Act06 |
| 23011 | 0,60 i 1,40 s | 1,4 m | „łowca smoków”: zamach oburącz z dołu w górę (2 trafienia) | Act07 |
| 23040–23051 | — | 1,4–4,2 m | bez trafień (TAE bez ataku; prawdopodobnie nieużywane warianty) | — |

**Combo (Act02):** 23000 > 23001 | 23000 > 23001 > 23002 | 23000 > 23001 > 23003.

## Halabarda (AI 279003)

| ID | trafienie | przesunięcie | co robi | AI |
|---|---|---|---|---|
| 33000 | 0,67 s | 0 m | pchnięcie zza tarczy (1) | otwiera combo |
| 33001 | 0,60 s | 1,9 m | pchnięcie zza tarczy (2) | 2. cios |
| 33002 | 0,77 s | 2,5 m | pchnięcie zza tarczy (3) | 3. cios |
| 33003 | 1,20 s | 0,1 m | silny atak | reakcja (Interupt) |
| 33004 | 0,57 s | 3,4 m | pchnięcie z rozpędu po 2–3 krokach | — |
| 33005 | 1,27 s | **5,8 m** | szarża z tarczą przed sobą | Act05 |
| 33007 | 0,63 s | 2,0 m | zamach poziomy (w combo) | koniec combo |
| 33008 | 0,63 s | 0,7 m | zamach poziomy (pojedynczy) | — |
| 33009 | 0,77 s | 2,3 m | zamach poziomy (2) | — |
| 33010 | 0,83 s | 2,2 m | silny zamach poziomy | Act06, z obrotem do celu |
| 33011 | 0,77 s | 2,5 m | pchnięcie po zamachu | — |
| 33012 | 0,80 i 1,37 s | 3,5 m | atak jedną ręką wzięty od gracza (2 trafienia) | Act07 |
| 33013 | 1,30 s | 5,0 m | atak z wyskoku wzięty od gracza | Act08 |

**Combo (Act02):** 33000 > 33001 | 33000 > 33001 > 33002 | 33000 > 33001 > 33007.

## Nieataki (wspólne)
- **2100** (2,37 s): kandydat na oszołomienie po parowaniu.
  - JT41 i zdarzenie typu 67 przez całe 0–1,83 s.
  - Kandydat na stan „można wykonać ripostę”, raport nocy §9.
- **2200, 2202, 2204, 2207, 2209** (2,7–4,8 s): animacje ofiary ciosu krytycznego (ciosu w plecy i riposty).
- 2000–2083: reakcje na trafienie.
- 2500/2510 (9,6 s): śmierć.
- 3500, 13500 (2,03 s): bez trafień; przy halabardzie i toporze brak odpowiednika.

## Pod rework (Crucible Knight, `nie_czytaj-na_pozniej.md`)
- Najdłuższe combo DS1 ma 4 ciosy. Trafienia wypadają przy 0,6–1,3 s, a animacje trwają 2,9–4,1 s, czyli 2–3 s martwego czasu po ciosie.
  - Pierwszy krok reworku jak u Artoriasa: wcześniejsze okna przerwania i combo w TAE, krótsze końcówki.
- Ataki z doskokiem już są (13010 6,8 m, 23003/23009 5,6 m, 33005 5,8 m). Brakuje opóźnionych zamachów i fali wymuszającej skok.
- Ataki „łowcy smoków” (13013/13014, 23010/23011) to naturalne miejsce na zamach z opóźnieniem.
