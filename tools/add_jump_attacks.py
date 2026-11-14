"""
add_jump_attacks.py - ataki z wyskoku z ER jako nowe animacje grup broni DSR.

Dla grupy aGG (np. a26) i par (zrodlo DSR, nowe ID, animacja ER):
    3000 -> 3700 <- a0GG_031030 (JumpAttack_N_Normal_Right, R1 jedna reka)
    3300 -> 3710 <- a0GG_031230 (JumpAttack_N_Hard_Right,   R2 jedna reka)
    4000 -> 4700 <- a0GG_033030 (JumpAttack_N_Normal_Both,  R1 oburacz)
    4300 -> 4710 <- a0GG_033230 (JumpAttack_N_Hard_Both,    R2 oburacz)
TAE zamachu: klon zdarzen ataku DSR (obrazenia/zachowanie broni DSR) przesuniety tak, zeby poczatek
trafienia wypadl jak w ER; bez okien przerwan; dodane JT51 "Disable Fall Motion" (gra nie przerywa
go spadaniem).
Ladowanie (ER: ID zamachu + 40, np. 31070 - ten sam ruch na ziemi + wstawanie): nowe ID + 1 (z
trafieniem) i + 2 (bez trafienia, ten sam HKX), okna przerwan w czasach ER. DLL przelacza na nie
zamach w chwili ladowania i przewija do czasu, w ktorym byl zamach.
HKX: plik ER jako aGG_NNNN.hkx (ID wpisu = ID animacji GG*10000+NNNN) w c0000_aNx.anibnd.dcx moda.
Podmiana ataku w locie na te animacje, wykrycie ladowania i tabela jump_attack_table.h: er_engine.dll.

Uzycie (CMD): python tools\\add_jump_attacks.py --groups a26
Every run rewrites jump_attack_table.h from the groups given, so always pass all groups:
  python tools\\add_jump_attacks.py --groups a20 a23 a25 a26 a27 a28 a29 a30 a32 a33 a35 a36 a38 a42 a43
  --chr DIR writes the anibnd files to DIR (test package) instead of the main mod's files\\chr.
"""
from __future__ import annotations

import argparse
import glob
import ntpath
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from sfbridge import load_soulsformats, read_binder, read_file, to_memory  # noqa: E402
from tae_compare import DSAS, ER_ANI, template  # noqa: E402
from er_land_settle import settle_ms  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
CHR = ROOT / "dist/mods/c0000_er_engine/files/chr"
GAME_CHR = Path(r"F:\SteamLibrary\steamapps\common\DARK SOULS REMASTERED\chr")
REPO = Path(r"C:\Users\nemos\workspace\toolsy\Player Animations Repository")
PAIRS = [(3000, 3700, 31030), (3300, 3710, 31230), (4000, 4700, 33030), (4300, 4710, 33230)]
JT_DISABLE_FALL = 51
CANCELS = {4, 11, 16, 22, 26, 29, 31, 32}  # okna przerwan: atak, ruch, blok, przewrot, czar, przedmiot, ogolne
SWING_AFTER_HIT = 0.5  # zamach w powietrzu trwa tyle po koncu trafienia ER (ER: 0.50 -> 1.00 s); potem zwykle spadanie
LAND_OFFSET = 40       # ER: zamach 31030 -> ladowanie 31070 (tak samo 31230, 33030, 33230)
DSR_TRACKS = 61        # szkielet gracza DSR; pliki repozytorium z inna liczba sciezek nie sa przeliczone
# Grupy ER brane w zastepstwie, gdy wlasna nie ma uzywalnego pliku (brak albo zly szkielet):
# katana 29 (wszystkie pliki 42 sciezki z numerami kosci ER - model sie rozpada), topor 30 (brak R1),
# mlot 33, miecz zakrzywiony 28 (ladowanie R2 oburacz ma 42 sciezki).
FALLBACK = {"29": ["28", "23"], "28": ["23"], "30": ["33", "23"], "33": ["30", "23"]}


def type_id(tpl, name):
    return next(i for i, (n, _) in tpl.items() if n == name)


def jt_of(e):
    """Numer JumpTable zdarzenia (typ 0) albo None."""
    pb = bytes(e.GetParameterBytes(False))
    return struct.unpack_from("<i", pb)[0] if int(e.Type) == 0 and len(pb) >= 4 else None


def jt_start(events, j):
    s = [e.StartTime for e in events if jt_of(e) == j]
    return min(s) if s else None


def _types(atk):
    return atk if isinstance(atk, (set, frozenset)) else {atk}


def hit_end(events, atk):
    s = [e.EndTime for e in events if int(e.Type) in _types(atk)]
    return max(s) if s else None


def first_hit(events, atk):
    s = [e.StartTime for e in events if int(e.Type) in _types(atk)]
    return min(s) if s else None


def er_hkx(gg: str, er_id: int) -> Path | None:
    own = ROOT / "work" / "jump_port" / f"a0{gg}_{er_id:06d}.hkx"  # tools/er_player_port.py (e.g. katana a29)
    if own.exists():
        return own
    hits = glob.glob(str(REPO / "**" / "2016 (DSR)" / "**" / f"a0{gg}_{er_id:06d}.hkx"), recursive=True)
    if not hits:
        return None
    # hkaAnimation w tych plikach: +256 typ (3 = spline), czas trwania, liczba sciezek kosci.
    typ, _dur, tracks = struct.unpack_from("<ifi", Path(hits[0]).read_bytes(), 256)
    return Path(hits[0]) if typ == 3 and tracks == DSR_TRACKS else None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--groups", nargs="+", default=["a26"])
    ap.add_argument("--chr", type=Path, default=CHR,
                    help="folder written to (e.g. a test package); files missing there are read from the main mod, "
                         "then from the game")
    args = ap.parse_args()
    out_dir = args.chr.resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    load_soulsformats()
    from SoulsFormats import BND3, BND4, TAE, BinderFile
    from System import Array, Byte
    t1, te = template(DSAS / "TAE.Template.DS1.xml"), template(DSAS / "TAE.Template.ER.xml")
    # DSR damage events: InvokeAttackBehavior; fists (a42) hit through InvokePCBehavior (2026-11-14)
    a1 = {type_id(t1, "InvokeAttackBehavior"), type_id(t1, "InvokePCBehavior")}
    ae = type_id(te, "InvokeAttackBehavior")
    er_taes = {ntpath.basename(f.Name).lower(): f for f in read_binder(BND4, str(ER_ANI)).Files}

    ani_path = out_dir / "c0000.anibnd.dcx"
    ani = read_binder(BND3, str(ani_path if ani_path.exists() else CHR / "c0000.anibnd.dcx"))
    added = {}  # kontener -> [(new_full_id, hkx_path)]
    rows = []   # wiersze JumpAttackRow -> native/er_engine/jump_attack_table.h
    er_tae_cache = {}
    blend_idle = type_id(te, "BlendToIdleOrMovementAnim")
    early = type_id(t1, "ActivateJumpTableEarly")
    for g in args.groups:
        gg = g[1:]
        tf = next(f for f in ani.Files if ntpath.basename(f.Name).lower() == f"{g}.tae")
        tae = read_file(TAE, tf.Bytes)
        anims = {int(a.ID): a for a in tae.Animations}
        for src_id, new_id, er_id in PAIRS:
            src = anims.get(src_id)
            d_hit = first_hit(list(src.Events), a1) if src is not None else None
            if d_hit is None and src is not None and src.AnimFileReference and int(src.Unknown1) // 10000 == int(gg):
                # e.g. hammer a33 3300 / 4300: only a reference to 3600 / 4600, which holds the swing and its hit
                ref = anims.get(int(src.Unknown1) % 10000)
                r_hit = first_hit(list(ref.Events), a1) if ref is not None else None
                if r_hit is not None:
                    print(f"  {g}: {src_id} is a reference to {int(src.Unknown1) % 10000} - events taken from there")
                    src, d_hit = ref, r_hit
            if d_hit is None:
                print(f"  {g}: {src_id}->{new_id}: atak DSR {'bez trafienia' if src is not None else 'nie istnieje'} - pomijam")
                continue
            pick = None
            for need_land in (True, False):  # najpierw grupa z uzywalnym ladowaniem
                for eg in [gg] + FALLBACK.get(gg, []):
                    if eg not in er_tae_cache:
                        er_tae_cache[eg] = read_file(TAE, er_taes[f"a{eg}.tae"].Bytes) if f"a{eg}.tae" in er_taes else None
                    et, h = er_tae_cache[eg], er_hkx(eg, er_id)
                    ea = next((a for a in et.Animations if int(a.ID) == er_id), None) if et else None
                    if h is None or ea is None or first_hit(list(ea.Events), ae) is None:
                        continue
                    el = next((a for a in et.Animations if int(a.ID) == er_id + LAND_OFFSET), None)
                    land_ok = er_hkx(eg, er_id + LAND_OFFSET) is not None and el is not None and first_hit(list(el.Events), ae) is not None
                    if need_land and not land_ok:
                        continue
                    pick = (eg, et, h, ea)
                    break
                if pick:
                    break
            if pick is None:
                print(f"  {g}: {src_id}->{new_id} <- {er_id}: brak uzywalnego pliku ER (takze w grupach zastepczych) - pomijam")
                continue
            eg, er_tae, hkx, er_anim = pick
            if eg != gg:
                print(f"  {g}: {new_id}: animacja i czasy z grupy ER a{eg} (wlasna grupa bez uzywalnego pliku)")
            e_hit = first_hit(list(er_anim.Events), ae)
            shift = e_hit - d_hit
            for old in (new_id, new_id + 1, new_id + 2):
                if old in anims:
                    tae.Animations.Remove(anims.pop(old))
            # Zamach w powietrzu: bez okien przerwan (jak w ER - przerwania sa dopiero w ladowaniu).
            clone = TAE.Animation(new_id, src.AnimFileReference, src.Unknown1, src.Unknown2, f"{g}_{new_id:04d}.HKXwin")
            end = 0.0
            for e in src.Events:
                if jt_of(e) in CANCELS or int(e.Type) == early:
                    continue  # takze ActivateJumpTableEarly - krotkie okna przerwan atakiem w powietrzu
                s, en = max(0.0, e.StartTime + shift), max(0.03, e.EndTime + shift)
                clone.Events.Add(TAE.Event(s, en, e.Type, e.Unk04, e.GetParameterBytes(False), False))
                end = max(end, en)
            jt51 = next(e for e in src.Events if int(e.Type) == 0)  # wzor zdarzenia JumpTable
            p = bytearray(bytes(jt51.GetParameterBytes(False)))
            struct.pack_into("<i", p, 0, JT_DISABLE_FALL)
            clone.Events.Add(TAE.Event(0.0, end, jt51.Type, jt51.Unk04, Array[Byte](list(p)), False))
            tae.Animations.Add(clone)
            swing_end = hit_end(list(er_anim.Events), ae) + SWING_AFTER_HIT
            print(f"  {g}: {new_id} = zdarzenia {src_id} przesuniete o {shift:+.2f} s (trafienie {d_hit:.2f} -> {e_hit:.2f}), koniec zamachu {swing_end:.2f} s, HKX {hkx.name}")
            container = f"c0000_a{gg[0]}x.anibnd.dcx"
            full = int(gg) * 10000 + new_id
            added.setdefault(container, []).append((full, hkx, f"{g}_{new_id:04d}.hkx"))

            # Ladowanie (ER: er_id + 40, np. 31070): ten sam ruch co zamach, ale na ziemi i z wstawaniem.
            # +1 = z trafieniem (ladowanie przed trafieniem), +2 = bez trafienia (ladowanie po trafieniu).
            land_hkx = er_hkx(eg, er_id + LAND_OFFSET)
            er_land = next((a for a in er_tae.Animations if int(a.ID) == er_id + LAND_OFFSET), None)
            l_hit = first_hit(list(er_land.Events), ae) if er_land else None
            row = [full, int(round(e_hit * 1000)), int(round(swing_end * 1000)), 0, 0, 0, 0, 0]
            if land_hkx is None or l_hit is None:
                print(f"  {g}: {new_id}: brak ladowania {er_id + LAND_OFFSET} w ER - zostaje sam zamach")
            else:
                er_ev = list(er_land.Events)
                move_at = jt_start(er_ev, 11) or (hit_end(er_ev, ae) + 0.5)
                l_shift = l_hit - d_hit
                for k, with_hit in ((1, True), (2, False)):
                    lid = new_id + k
                    land = TAE.Animation(lid, src.AnimFileReference, src.Unknown1, src.Unknown2, f"{g}_{lid:04d}.HKXwin")
                    for e in src.Events:
                        j = jt_of(e)
                        s, en = max(0.0, e.StartTime + l_shift), max(0.03, e.EndTime + l_shift)
                        if j in CANCELS:  # okna przerwan w czasach ER (ten sam numer JT, inaczej czas ruchu)
                            s = jt_start(er_ev, j) or move_at
                            en = max(en, s + 1.0)
                        elif not with_hit and j is None:
                            continue  # bez trafienia: tylko zdarzenia JumpTable
                        land.Events.Add(TAE.Event(s, en, e.Type, e.Unk04, e.GetParameterBytes(False), False))
                    tae.Animations.Add(land)
                    added[container].append((int(gg) * 10000 + lid, land_hkx, f"{g}_{lid:04d}.hkx"))
                idle_at = next((e.StartTime for e in er_ev if int(e.Type) == blend_idle and e.EndTime > 1e30), move_at + 0.3)
                # End without input: not before the feet stand in the stance again (tools/er_land_settle.py; the
                # ER idle-blend time cut R1 landings in the middle of the step back, 2026-11-14)
                settle = settle_ms(int(eg), er_id + LAND_OFFSET) or 0
                end_ms = max(int(round(max(idle_at, move_at + 0.15) * 1000)), settle)
                row[3:] = [full + 1, full + 2, end_ms,
                           int(round((jt_start(er_ev, 4) or move_at) * 1000)), int(round(move_at * 1000))]
                print(f"  {g}: {new_id + 1}/{new_id + 2} = ladowanie {land_hkx.name}: trafienie {l_hit:.2f} s, atak od {jt_start(er_ev, 4) or move_at:.2f} s, ruch od {move_at:.2f} s, koniec bez inputu {row[5] / 1000:.2f} s")
            rows.append(tuple(row))
        srt = sorted(list(tae.Animations), key=lambda a: a.ID)
        tae.Animations.Clear()
        for a in srt:
            tae.Animations.Add(a)
        tf.Bytes = to_memory(tae.Write())
    tmp = ani_path.with_suffix(".tmp")
    ani.Write(str(tmp))
    ani.Dispose()
    tmp.replace(ani_path)

    for container, items in added.items():
        src_path = next(p for p in (out_dir / container, CHR / container, GAME_CHR / container) if p.exists())
        b = read_binder(BND3, str(src_path))
        ref = b.Files[0]
        for full_id, hkx, name in items:
            for f in [f for f in b.Files if int(f.ID) == full_id]:
                b.Files.Remove(f)
            path = ntpath.join(ntpath.dirname(ntpath.dirname(ref.Name)), name.split("_")[0], name)
            b.Files.Add(BinderFile(ref.Flags, full_id, path, to_memory(Array[Byte](list(hkx.read_bytes())))))
        files = sorted(list(b.Files), key=lambda f: int(f.ID))
        b.Files.Clear()
        for f in files:
            b.Files.Add(f)
        out = out_dir / container
        tmp = out.with_suffix(".tmp")
        b.Write(str(tmp))
        b.Dispose()
        tmp.replace(out)
        print(f"  {container}: +{len(items)} HKX")
    hdr = ROOT / "native/er_engine/jump_attack_table.h"
    lines = ["// Wygenerowane przez tools/add_jump_attacks.py - nie edytowac recznie.", "#pragma once",
             "// anim = zamach w powietrzu; hitMs = poczatek trafienia; swingEndMs = koniec zamachu;",
             "// landHit / landFollow = ladowanie z trafieniem / bez (0 = brak); landEndMs = koniec ladowania bez inputu.",
             "// landAtkMs / landMoveMs = od kiedy w ladowaniu wolno atakowac / ruszyc (czasy ER; pilnuje ich DLL).",
             "struct JumpAttackRow { int anim; unsigned hitMs, swingEndMs; int landHit, landFollow; unsigned landEndMs, landAtkMs, landMoveMs; };",
             "static const JumpAttackRow kJumpAttacks[] = {"]
    lines += ["    {" + ", ".join(str(v) for v in r) + "}," for r in sorted(rows)] + ["    {0, 0, 0, 0, 0, 0, 0, 0},", "};"]
    hdr.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"OK ({len(rows)} atakow z wyskoku) -> {hdr}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
