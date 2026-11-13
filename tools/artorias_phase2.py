"""Artorias (c4100) phase 2, data side: params and the transition animation 3016 for the boss test package.

Design (docs/PLAN_PROJEKTU.md §6a): phase 1 ends at HP 0 (the DLL keeps the boss alive with ChrFlags2
NoDead), the AI then plays 3016 = the buff motion of 3013 with:
  - TAE 401 at the start -> SpEffect 5512 "transition": no damage taken, HP refilled to full over the kneel
    (the original 3013 gives 5511 here: half damage, lower poise - that is why the vanilla buff can be broken);
  - super armor (JT24) over the whole animation;
  - the burst at 5.40 s fires bullet 41520 (copy of the buff burst 41510) that gives the boss SpEffect 5513
    "phase 2": the buff values of 5510 without an end (its stateInfo 205 = the vanilla dark body aura, FFX 845).
    The AI reads the phase from 5513. (--anim-offset would add animIdOffset for a 130xx variant set; not used.)
NpcParam 410000 hp is lowered so that both phases together are about 1.1-1.2x the vanilla fight.

Stage 2 (effects and AOE; only phase-2 animations are touched, so no 130xx variants are needed):
  - phase-2 sword smoke: FFX 13910 = the endless abyss smoke the vanilla boss carries on the pelvis (started by a
    slot event, type 100, in idle animation 0), put on the blade twice: SpEffect 5514 (no stats, endless, given by
    TAE 401 in 3016 at 5.40 s) with stateInfo 250 = new SpEffectVfx row (13910 on dummypoly 21, middle of the
    blade), and a type-100 slot event in 3016 (13910 on dummypoly 11, near the tip);
    test 13.11 #1: the buff aura FFX 845 on dummypoly 21 was hardly visible;
  - 3016 fires two rings of dark beads (Dark Bead visuals 20106 / 20206, own AtkParam_Npc) from the fixed
    dummypoly 8 right after the burst, the second ring offset by half a step;
  - 3026, 3027, 3028 (NR jump attacks, phase 2 only): from the jump to the slam the blade tip throws the sparks
    of the vanilla charge slash 3007 (FFX 13907 on dummypoly 11, a new spawn every 0.1 s), and at the slam a
    small visible explosion = bullet 41530 (FFX 13912 = the vanilla sword-into-ground hit of the somersaults,
    radius 2.5 m) at the blade tip (dummypoly 11); 3027 loses the invisible vanilla area hit 180.
    test 13.11 #1: the buff burst FFX 13908 was much bigger than the Nightreign one; FFX 13914 used before for
    the glow shares its models with the footstep dust (likely the dust of the vanilla charges, not a glow).
  Timings follow the Nightreign TAE of the same animations (bullets 465 / 475 / 485 at 3.20 / 2.43 / 1.83 s).

Writes:
  dist/mods/bossy_nightreign/files_c4100_v2/param/GameParam/GameParam.parambnd.dcx
      (built from the main mod's GameParam, so the ER lock-on camera stays - the boss package is loaded first
       and its file wins; rerun after the main mod's GameParam changes)
  dist/mods/bossy_nightreign/files_c4100_v2/chr/c4100.anibnd.dcx  (adds / replaces 3016 in place;
      rerun after every `nr_boss_port.py --install`, which rewrites the anibnd)

  python tools/artorias_phase2.py [--hp 880] [--dry-run]
"""
from __future__ import annotations

import argparse
import ntpath
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from sfbridge import load_soulsformats, net_bytes, read_binder, read_file, to_memory  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
PKG = ROOT / "dist" / "mods" / "bossy_nightreign" / "files_c4100_v2"
ANIBND = PKG / "chr" / "c4100.anibnd.dcx"
PARAM_SRC = ROOT / "dist" / "mods" / "c0000_er_engine" / "files" / "param" / "GameParam" / "GameParam.parambnd.dcx"
PARAM_OUT = PKG / "param" / "GameParam" / "GameParam.parambnd.dcx"
DEFS = Path(r"C:\Users\nemos\workspace\toolsy\Smithbox_2_2_6_2026_09_20_b\Assets\PARAM\DS1R\Defs")

NPC_ID = 410000
SP_BUFF, SP_BUFF_SA = 5510, 5511          # vanilla: buff (60 s) and "SA adjustment during self-enhancement"
SP_TRANSITION, SP_PHASE2 = 5512, 5513     # new rows (5512-5519 are free in DSR)
BULLET_BUFF, BULLET_PHASE2 = 41510, 41520
BEH_BUFF, BEH_PHASE2 = 241000510, 241000520
ANIM_BUFF, ANIM_TRANSITION = 3013, 3016
TRANSITION_TIME = 7.6                     # s, SpEffect 5512 life (3013 is 8.0 s, the burst is at 5.40 s)
HEAL_INTERVAL, HEAL_RATE = 0.25, -4.0     # % of max HP per tick (negative = heal); test 13.11: -3.5 gave 97.8 %

# stage 2: effects and AOE
SP_NEUTRAL, SP_SWORD = 5400, 5514         # 5400 = endless, no stats ("Weapon Change Anime ID Offset 0")
VFX_AURA, VFX_SWORD = 205, 250            # SpEffectVfx: 205 vanilla "[DLC] Dark Enhancement"; 243-255 are free
FFX_SMOKE, FFX_SPARKS, FFX_SLAM, FFX_SLAM_HIT = 13910, 13907, 13912, 13909
FFX_BEAD, FFX_BEAD_HIT = 20106, 20206     # Dark Bead (CommonEffects, always loaded)
DMY_BLADE_TIP, DMY_BLADE_MID, DMY_FRONT = 11, 21, 8   # c4100.flver (8: fixed dummy 2.09 m high, 0.6 m in front)
SLOT_SWORD_SMOKE = 5                      # vanilla slots: 1-2 (idle smoke), 10 (blade trail), 11
SPARK_STEP, SPARK_LEN = 0.1, 0.4          # s; vanilla 3007 spawns 13907 every ~0.03 s, 0.4-0.9 s each
BULLET_AOE, ATK_AOE, BEH_AOE = 41530, 410530, 241000530
BULLET_BEAD_A, BULLET_BEAD_B, ATK_BEAD = 41540, 41541, 410540
BEH_BEAD_A, BEH_BEAD_B = 241000540, 241000541
BULLET_BEAD_SRC, ATK_AOE_SRC, ATK_BEAD_SRC = 14100, 410180, 410500   # Dark Bead; 3005 area hit; left-hand beads
BEH_VANILLA_AREA = 180                    # 3005's invisible 3 m area hit, copied into 3027 by the port
AOE_RADIUS = 2.5
BEAD_COUNT, BEAD_SPEED, BEAD_PITCH = 12, 12.0, -7   # per ring; m/s; degrees (from 2.09 m: ~1.5 m high at 5 m)
BEAD_TIMES = (5.433, 5.700)               # s in 3016 (burst at 5.40)
SWORD_TIME = 5.400
# animation: (sparks start, slam) in s - same timing as the Nightreign TAE of these moves
AOE_MOVES = {3026: (1.900, 3.200), 3027: (0.500, 2.433), 3028: (0.133, 1.833)}
# events written by earlier versions of this script (removed on every run): (ffx, dummypoly, slot)
OLD_FFX_EVENTS = {(13914, -1, 12), (845, 21, 13)}
OLD_LANDING_FX = ((13920, 230), (3026, 3028))      # added to 3026 / 3028 only (3027 has its own from 3005)


def set_value(cell, value) -> None:
    import System
    t = str(cell.Def.DisplayType).lower()
    conv = {"s8": System.SByte, "u8": System.Byte, "s16": System.Int16, "u16": System.UInt16,
            "s32": System.Int32, "u32": System.UInt32, "f32": System.Single, "b32": System.Int32}
    if t not in conv:
        raise TypeError(f"{cell.Def.InternalName}: unsupported type {t}")
    cell.Value = conv[t](value)


def edit_row(row, values: dict) -> list[str]:
    cells = {str(c.Def.InternalName): c for c in row.Cells}
    out = []
    for k, v in values.items():
        if k not in cells:
            raise KeyError(f"row {int(row.ID)}: no field {k}")
        old = cells[k].Value
        set_value(cells[k], v)
        out.append(f"{k} {old} -> {cells[k].Value}")
    return out


def clone_row(sf, param, src_id: int, new_id: int, name: str):
    """Copy of row src_id under new_id (replaced if it already exists), inserted in ID order."""
    src = next(r for r in param.Rows if int(r.ID) == src_id)
    for r in list(param.Rows):
        if int(r.ID) == new_id:
            param.Rows.Remove(r)
    row = sf.PARAM.Row(src)
    row.ID = new_id
    row.Name = name
    pos = next((i for i, r in enumerate(param.Rows) if int(r.ID) > new_id), param.Rows.Count)
    param.Rows.Insert(pos, row)
    return row


def build_params(sf, hp: int, anim_offset: int) -> object:
    bnd = read_binder(sf.BND3, str(PARAM_SRC))
    files = {ntpath.basename(str(f.Name)).lower(): f for f in bnd.Files}

    def open_param(file_name: str, def_name: str):
        f = files[f"{file_name.lower()}.param"]
        p = read_file(sf.PARAM, f.Bytes)
        p.ApplyParamdef(sf.PARAMDEF.XmlDeserialize(str(DEFS / f"{def_name}.xml"), False))
        return f, p

    changed = []
    f_npc, npc = open_param("NpcParam", "NpcParam")
    row = next(r for r in npc.Rows if int(r.ID) == NPC_ID)
    print(f"NpcParam {NPC_ID}: " + "; ".join(edit_row(row, {"hp": hp})))
    changed.append((f_npc, npc))

    f_sp, sp = open_param("SpEffectParam", "SpEffect")
    tr = clone_row(sf, sp, SP_BUFF_SA, SP_TRANSITION, "c4100 Artorias phase transition (mod)")
    cut = {k: 0.0 for k in ("slashDamageCutRate", "blowDamageCutRate", "thrustDamageCutRate", "neutralDamageCutRate",
                            "magicDamageCutRate", "fireDamageCutRate", "thunderDamageCutRate")}
    print(f"SpEffect {SP_TRANSITION} (from {SP_BUFF_SA}): " + "; ".join(edit_row(tr, {
        "effectEndurance": TRANSITION_TIME, "changeSuperArmorPoint": 0, "motionInterval": HEAL_INTERVAL,
        "changeHpRate": HEAL_RATE, **cut})))
    p2 = clone_row(sf, sp, SP_BUFF, SP_PHASE2, "c4100 Artorias phase 2 (mod)")
    print(f"SpEffect {SP_PHASE2} (from {SP_BUFF}): " + "; ".join(edit_row(p2, {
        "effectEndurance": -1.0, "animIdOffset": anim_offset, "spCategory": 0})))
    sw = clone_row(sf, sp, SP_NEUTRAL, SP_SWORD, "c4100 Artorias phase 2 sword (mod)")
    print(f"SpEffect {SP_SWORD} (from {SP_NEUTRAL}): " + "; ".join(edit_row(sw, {
        "effectEndurance": -1.0, "spCategory": 0, "stateInfo": VFX_SWORD})))
    changed.append((f_sp, sp))

    f_vfx, vfx = open_param("SpEffectVfxParam", "SpEffectVfx")
    v = clone_row(sf, vfx, VFX_AURA, VFX_SWORD, "c4100 Artorias phase 2 sword smoke (mod)")
    print(f"SpEffectVfx {VFX_SWORD} (from {VFX_AURA}): " + "; ".join(edit_row(v, {
        "midstSfxId": FFX_SMOKE, "midstDmyId": DMY_BLADE_MID})))
    changed.append((f_vfx, vfx))

    f_atk, atk = open_param("AtkParam_Npc", "AtkParam")
    a = clone_row(sf, atk, ATK_AOE_SRC, ATK_AOE, "c4100 Artorias phase 2 slam explosion (mod)")
    print(f"AtkParam_Npc {ATK_AOE} (from {ATK_AOE_SRC}): " + "; ".join(edit_row(a, {
        "atkPhys": 110, "atkMag": 110, "atkStam": 220})))
    a = clone_row(sf, atk, ATK_BEAD_SRC, ATK_BEAD, "c4100 Artorias phase 2 dark bead (mod)")
    print(f"AtkParam_Npc {ATK_BEAD} (from {ATK_BEAD_SRC}): " + "; ".join(edit_row(a, {
        "atkPhys": 60, "atkMag": 80, "atkStam": 40, "atkSuperArmor": 10, "dmgLevel": 1})))
    changed.append((f_atk, atk))

    f_bu, bu = open_param("Bullet", "BulletParam")
    b = clone_row(sf, bu, BULLET_BUFF, BULLET_PHASE2, "[Knight Artorias] Phase 2 burst (mod)")
    print(f"Bullet {BULLET_PHASE2} (from {BULLET_BUFF}): " + "; ".join(edit_row(b, {"spEffectIDForShooter": SP_PHASE2})))
    b = clone_row(sf, bu, BULLET_BUFF, BULLET_AOE, "[Knight Artorias] Phase 2 slam explosion (mod)")
    print(f"Bullet {BULLET_AOE} (from {BULLET_BUFF}): " + "; ".join(edit_row(b, {
        "atkId_Bullet": ATK_AOE, "sfxId_Bullet": FFX_SLAM, "sfxId_Hit": FFX_SLAM_HIT, "hitRadius": AOE_RADIUS,
        "spEffectIDForShooter": -1})))
    for bid, start in ((BULLET_BEAD_A, -180), (BULLET_BEAD_B, -180 + 180 // BEAD_COUNT)):
        b = clone_row(sf, bu, BULLET_BEAD_SRC, bid, "[Knight Artorias] Phase 2 dark bead ring (mod)")
        print(f"Bullet {bid} (from {BULLET_BEAD_SRC}): " + "; ".join(edit_row(b, {
            "atkId_Bullet": ATK_BEAD, "sfxId_Bullet": FFX_BEAD, "sfxId_Hit": FFX_BEAD_HIT,
            "numShoot": BEAD_COUNT, "shootAngle": start, "shootAngleInterval": 360 // BEAD_COUNT,
            "shootAngleXZ": BEAD_PITCH, "lockShootLimitAng": 0,
            "initVellocity": BEAD_SPEED, "maxVellocity": BEAD_SPEED, "minVellocity": BEAD_SPEED,
            "accelInRange": 0.0, "accelOutRange": 0.0, "gravityInRange": 0.0,
            "life": 1.6, "dist": 15.0, "hitRadius": 0.25})))
    changed.append((f_bu, bu))

    f_be, be = open_param("BehaviorParam", "BehaviorParam")
    for beh, ref, name in ((BEH_PHASE2, BULLET_PHASE2, "phase 2 burst"), (BEH_AOE, BULLET_AOE, "phase 2 slam explosion"),
                           (BEH_BEAD_A, BULLET_BEAD_A, "phase 2 dark beads 1"),
                           (BEH_BEAD_B, BULLET_BEAD_B, "phase 2 dark beads 2")):
        r = clone_row(sf, be, BEH_BUFF, beh, f"c4100 Artorias {name} (mod)")
        print(f"BehaviorParam {beh} (from {BEH_BUFF}): " + "; ".join(edit_row(r, {
            "refId": ref, "behaviorJudgeId": beh % 1000})))
    changed.append((f_be, be))

    for f, p in changed:
        f.Bytes = to_memory(p.Write())
    return bnd


def jt_of(ev):
    p = bytes(ev.GetParameterBytes(False))
    return struct.unpack_from("<i", p)[0] if int(ev.Type) == 0 and len(p) >= 4 else None


def build_anibnd(sf) -> object:
    bnd = read_binder(sf.BND3, str(ANIBND))
    files = {ntpath.basename(str(f.Name)).lower(): f for f in bnd.Files}
    tentry = files["c4100.tae"]
    tae = read_file(sf.TAE, tentry.Bytes)

    # HKX: 3016 = copy of the buff clip (binder ID = animation ID, as the ported attacks)
    src = files[f"a00_{ANIM_BUFF:04d}.hkx"]
    name = str(src.Name).replace(f"a00_{ANIM_BUFF:04d}", f"a00_{ANIM_TRANSITION:04d}")
    for f in list(bnd.Files):
        if ntpath.basename(str(f.Name)).lower() == f"a00_{ANIM_TRANSITION:04d}.hkx":
            bnd.Files.Remove(f)
    entry = sf.BinderFile(src.Flags, ANIM_TRANSITION, name, src.Bytes)
    pos = next((i for i, f in enumerate(bnd.Files) if int(f.ID) > ANIM_TRANSITION), bnd.Files.Count)
    bnd.Files.Insert(pos, entry)

    # TAE: events of 3013 with the transition changes
    for a in list(tae.Animations):
        if int(a.ID) == ANIM_TRANSITION:
            tae.Animations.Remove(a)
    buff = next(a for a in tae.Animations if int(a.ID) == ANIM_BUFF)
    na = sf.TAE.Animation(ANIM_TRANSITION, False, 0, -1, f"a00_{ANIM_TRANSITION:04d}.hkxwin")
    end = max(float(ev.EndTime) for ev in buff.Events)
    jt24 = None
    n401 = nbul = 0
    for ev in buff.Events:
        p = bytearray(bytes(ev.GetParameterBytes(False)))
        ty = int(ev.Type)
        if ty == 0 and jt_of(ev) == 24:
            jt24 = jt24 or ev  # replaced by one window over the whole animation below
            continue
        if ty == 401 and struct.unpack_from("<i", p)[0] == SP_BUFF_SA:
            struct.pack_into("<i", p, 0, SP_TRANSITION)
            n401 += 1
        if ty == 2 and len(p) >= 12 and struct.unpack_from("<i", p, 8)[0] == BEH_BUFF % 1000:
            struct.pack_into("<i", p, 8, BEH_PHASE2 % 1000)
            nbul += 1
        na.Events.Add(sf.TAE.Event(float(ev.StartTime), float(ev.EndTime), ev.Type, ev.Unk04, net_bytes(bytes(p)), False))
    if jt24 is None or n401 != 1 or nbul != 1:
        raise RuntimeError(f"3013 layout changed: JT24 {jt24 is not None}, TAE 401 x{n401}, bullet 510 x{nbul}")
    na.Events.Add(sf.TAE.Event(0.0, end, jt24.Type, jt24.Unk04, jt24.GetParameterBytes(False), False))

    # stage 2 in 3016: endless sword smoke, two rings of dark beads after the burst
    tpl = {int(ev.Type): ev for ev in buff.Events if int(ev.Type) in (2, 96, 401)}
    idle = next(a for a in tae.Animations if int(a.ID) == 0)
    tpl[100] = next(ev for ev in idle.Events if int(ev.Type) == 100)   # vanilla: endless smoke 13910 in slot 1
    add_event(sf, na, SWORD_TIME, SWORD_TIME + 0.033, tpl[401], {0: SP_SWORD})
    add_event(sf, na, SWORD_TIME, SWORD_TIME + 0.100, tpl[100], {0: FFX_SMOKE, 4: DMY_BLADE_TIP, 8: SLOT_SWORD_SMOKE})
    for t, beh in zip(BEAD_TIMES, (BEH_BEAD_A, BEH_BEAD_B)):
        add_event(sf, na, t, t + 0.033, tpl[2], {0: DMY_FRONT, 8: beh % 1000})
    pos = next((i for i, a in enumerate(tae.Animations) if int(a.ID) > ANIM_TRANSITION), tae.Animations.Count)
    tae.Animations.Insert(pos, na)
    print(f"anibnd: {ANIM_TRANSITION} = clip of {ANIM_BUFF}, {na.Events.Count} events "
          f"(401 -> {SP_TRANSITION}, bullet 510 -> {BEH_PHASE2 % 1000}, JT24 0.00-{end:.2f}; "
          f"401 {SP_SWORD} + smoke {FFX_SMOKE} slot {SLOT_SWORD_SMOKE} at {SWORD_TIME:.2f}, bead rings "
          f"{BEH_BEAD_A % 1000}/{BEH_BEAD_B % 1000} at {BEAD_TIMES[0]:.2f}/{BEAD_TIMES[1]:.2f} from dummypoly {DMY_FRONT})")

    # stage 2 in the phase-2 jump attacks: sparks from the jump to the slam, explosion at the slam
    for anim_id, (glow, slam) in AOE_MOVES.items():
        anim = next(a for a in tae.Animations if int(a.ID) == anim_id)
        spark_starts = [round(glow + i * SPARK_STEP, 3) for i in range(int((slam - glow) / SPARK_STEP + 1e-6))]
        removed = 0
        for ev in list(anim.Events):
            p = bytes(ev.GetParameterBytes(False))
            ty = int(ev.Type)
            ints = struct.unpack_from(f"<{len(p) // 4}i", p) if len(p) >= 4 else ()
            start, length = float(ev.StartTime), float(ev.EndTime) - float(ev.StartTime)
            my_spark = ty == 96 and ints[:3] == (FFX_SPARKS, DMY_BLADE_TIP, -1) and abs(length - SPARK_LEN) < 1e-3 \
                and any(abs(start - s) < 1e-3 for s in spark_starts)
            mine = my_spark or (ty == 96 and tuple(ints[:3]) in OLD_FFX_EVENTS) \
                or (ty == 2 and len(ints) >= 3 and ints[2] == BEH_AOE % 1000) \
                or (ty == 96 and anim_id in OLD_LANDING_FX[1] and tuple(ints[:2]) == OLD_LANDING_FX[0]) \
                or (ty == 1 and anim_id == 3027 and len(ints) >= 3 and ints[2] == BEH_VANILLA_AREA)
            if mine:
                anim.Events.Remove(ev)
                removed += 1
        for s in spark_starts:
            add_event(sf, anim, s, s + SPARK_LEN, tpl[96], {0: FFX_SPARKS, 4: DMY_BLADE_TIP, 8: -1})
        add_event(sf, anim, slam, slam + 0.033, tpl[2], {0: DMY_BLADE_TIP, 8: BEH_AOE % 1000})
        print(f"anibnd: {anim_id}: {len(spark_starts)} spark spawns {glow:.2f}-{slam:.2f}, explosion "
              f"{BEH_AOE % 1000} at {slam:.2f} (dummypoly {DMY_BLADE_TIP}); {removed} old event(s) removed")
    tentry.Bytes = to_memory(tae.Write())
    return bnd


def add_event(sf, anim, start: float, end: float, template, ints: dict[int, int]) -> None:
    """Append an event of the template's type/size with int params overwritten at the given byte offsets."""
    p = bytearray(bytes(template.GetParameterBytes(False)))
    for off, val in ints.items():
        struct.pack_into("<i", p, off, val)
    anim.Events.Add(sf.TAE.Event(float(start), float(end), template.Type, template.Unk04, net_bytes(bytes(p)), False))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--hp", type=int, default=880, help="NpcParam 410000 hp (vanilla 1500; x2.5 DLC area scaling)")
    # 0: stage 2 adds its effects to the phase-2-only animations, so no 130xx variant set exists. Whether the game
    # falls back to 3xxx when a 13xxx entry is missing is not tested; a missing fallback would break every attack.
    ap.add_argument("--anim-offset", type=int, default=0, help="animIdOffset of SpEffect 5513 (10000 = 130xx set)")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(argv)
    sf = load_soulsformats()
    params = build_params(sf, args.hp, args.anim_offset)
    anibnd = build_anibnd(sf)
    if args.dry_run:
        print("OK (dry-run, nothing written)")
        return 0
    PARAM_OUT.parent.mkdir(parents=True, exist_ok=True)
    params.Write(str(PARAM_OUT))
    # the source anibnd is memory-mapped while the binder is open: write next to it, close, then replace
    tmp = ANIBND.with_name(ANIBND.name + ".tmp")
    anibnd.Write(str(tmp))
    anibnd.Dispose()
    import gc
    gc.collect()
    tmp.replace(ANIBND)
    # read back
    chk = read_binder(sf.BND3, str(ANIBND))
    tae = read_file(sf.TAE, next(f for f in chk.Files if ntpath.basename(str(f.Name)).lower() == "c4100.tae").Bytes)
    assert any(int(a.ID) == ANIM_TRANSITION for a in tae.Animations)
    pchk = read_binder(sf.BND3, str(PARAM_OUT))
    print(f"written {PARAM_OUT} ({PARAM_OUT.stat().st_size} B, {pchk.Files.Count} params) and {ANIBND} "
          f"({ANIBND.stat().st_size} B, {chk.Files.Count} entries)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
