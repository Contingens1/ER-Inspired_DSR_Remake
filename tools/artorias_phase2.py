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

Stage 2, effects as tested by the player 13-14.11 (default; the 0.4.0 set below stays behind --old-fx):
  - sword: dense dark buff aura FFX 845 on three blade points (tip 11, past the tip 18, middle 21) for the whole
    phase 2 (SpEffects 5531-5533 given in 3016 at 5.40 s, SpEffectVfx rows 220-222), no aura on the body (5513
    stateInfo 0); SpEffectVfx rows past 242 are ignored by the game, mod rows reuse empty online-arena rows;
  - 3026 / 3027 / 3028 (the three phase-2 leaps): tip sparks of 3007 every 0.05 s from the top of the jump to the
    slam (they announce the explosion); at the slam the ground-hit FFX 13912 on mid-blade dummypoly 21, 0.1 s later
    the Dark Bead hit burst 20206 + sound s000020212 (x3, louder) + damage (invisible bullet 41532, 2 m, 0.1 s) at
    the same point - one well-timed roll dodges sword and burst, an early roll gets the burst; 3026 gets the
    landing sounds of 3027 (its port had none at the slam); first big leap 3027 is ported at x0.8 (12 m);
  - 3016 bead rings as before. Details and test history: the FX_* / SLAM_* comments below.

Stage 2 as released in 0.4.0 (--old-fx; the sword smoke never showed - row 250 is past 242):
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

  python tools/artorias_phase2.py [--hp 880] [--dry-run]               # main package files_c4100_v2
  python tools/artorias_phase2.py --tag _v2_test [--easy]              # test package files_c4100_v2_test
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
# SpEffectVfx: 205 vanilla "[DLC] Dark Enhancement". Rows past 242 "最大数(選択禁止)" are ignored by the game (0.4.0
# used 250 - never shown); the mod takes the online-arena rows 233-241 (only inside the boss package's GameParam).
VFX_AURA, VFX_SWORD = 205, 241
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

# Phase-2 effects (default since 14.11; built and tuned in the test package files_c4100_v2_test, tests #1-#12).
# The look rotation below is test machinery, kept for future comparisons: with one entry in LOOK_VFX it is a
# single endless look.
# Sword: looks that take turns every FX_LOOK_TIME s from the transition on (1 -> 2 -> ... -> 1). Each look is a set
# of parallel "tracks" (SpEffects that run together); every SpEffect hands over to the same track of the next look
# through replaceSpEffectId (vanilla uses it on enemies too: 5210 -> 5211 -> 5212). A track with nothing to show
# carries stateInfo 0. A ("pulse", id) track re-adds a short SpEffect every PULSE_EVERY s (cycleOccurrenceSpEffectId)
# whose start effect is a one-shot FFX.
# Tests 13.11 #2-#5 showed none of the sword looks: SpEffectVfx rows 247-255 are past the vanilla row
# 242 "最大数(選択禁止)" (max count, do not select), so the game ignores them (the 0.4.0 sword smoke row 250 too).
# The mod rows now reuse the arena (online PvP) rows 233-241 inside the boss package's GameParam.
# Wanted (test #5): "something intense, at the end of the sword", for the whole phase 2 (Nightreign has its sword
# effect in every phase-2 animation). Candidates at the blade tip (dummypoly 11), in this order:
#   1 tip sparks of the 3007 slash every 0.05 s (the leap sparks the player liked, all the time)
#   2 FFX 845 = the vanilla buff aura (body aura in 0.4.0)    3 FFX 20284 = player Crystal Magic Weapon (VFX 61)
#   4 FFX 20257 = "magic enhancement" (VFX 64)                5 FFX 22723 = Charcoal Pine Resin fire (VFX 62)
#   6 FFX 20221 = "power of madness" (VFX 200)
# The weapon-buff rows are effectType 1 (drawn along a player weapon); here they are plain effects on a dummypoly.
# Player (test #6): the plain leap sparks on the sword would blur the telegraph of the leaps - only mixed with
# something else; the buff aura only if it can be made denser. Round 7 (rows 220-231 = empty arena rows):
#   1 dense aura: 845 at the tip, past the tip and mid-blade      2 aura at the tip + past it, sparks every 0.3 s
#   3-6 Crystal Magic Weapon / magic enhancement / resin fire / power of madness, each at the tip and past the tip
FX_LOOK_TIME = 8.0
PULSE_EVERY = 0.3
DMY_HILT, DMY_BLADE_END, VFX_AURA_FFX = 12, 18, 845
_T, _E, _M = DMY_BLADE_TIP, DMY_BLADE_END, DMY_BLADE_MID
# SpEffectVfx rows of the test: id -> (midst ffx, midst dmy, init ffx, init dmy)
TEST_VFX = {220: (VFX_AURA_FFX, _T, -1, -1), 221: (VFX_AURA_FFX, _E, -1, -1), 222: (VFX_AURA_FFX, _M, -1, -1),
            223: (-1, -1, FFX_SPARKS, _T),
            224: (20284, _T, -1, -1), 225: (20284, _E, -1, -1), 226: (20257, _T, -1, -1), 227: (20257, _E, -1, -1),
            228: (22723, _T, -1, -1), 229: (22723, _E, -1, -1), 230: (20221, _T, -1, -1), 231: (20221, _E, -1, -1)}
TEST_PULSES = {5515: 223}                 # short SpEffects re-added by the pulse tracks: id -> vfx row
SP_LOOKS = ((5531, 5532, 5533), (5534, 5535, 5536), (5537, 5538, 5539), (5523, 5524, 5525), (5526, 5527, 5528),
            (5529, 5517, 5518))
LOOK_VFX = ((220, 221, 222), (220, 221, ("pulse", 5515)), (224, 225, 0), (226, 227, 0), (228, 229, 0), (230, 231, 0))
# test #7: only look 1 (dense aura, tip + mid-blade) was seen - "looks quite good"; the weapon-buff FFX showed
# nothing on a plain dummypoly. Round 8: look 1 for the whole phase 2.
LOOK_VFX = LOOK_VFX[:1]
TEST_BODY_AURA = 0                        # stateInfo of 5513 in the test (release: VFX_AURA = 205)
FX_ENERGY = 13906                        # vanilla: dark energy gathering above the head during the buff charge
BULLET_AOE_S, BULLET_AOE_M = 41531, 41532
BEH_AOE_S, BEH_AOE_M = 241000531, 241000532
# anim -> (trail kind, trail step s, slam bullet behavior, trail start s or None = AOE_MOVES start)
# test #3: the 3027 sparks every 0.05 s are good ("the attack is stronger"), wanted on both big leaps, starting in
# flight, not at the take-off; the 3028 explosion FFX 13909 ("vortex") too big; the 3027 one (13912, 1.5 m) not seen.
# Round 4: sparks on all three leaps from the top of the jump (pelvis curves, work/boss_views/pelvis_curve.py:
# 3027 take-off 1.45 / top 1.9 / slam 2.43, 3028 0.75 / 1.3 / 1.83, 3026 leap at the player 2.83-3.17 / slam 3.20),
# one explosion for all: FFX 13912, 2.0 m.
FX_TEST_MOVES = {3026: ("sparks", 0.05, BEH_AOE_M, 2.50), 3027: ("sparks", 0.05, BEH_AOE_M, 1.80),
                 3028: ("sparks", 0.05, BEH_AOE_M, 1.20)}
# test #5: no explosion seen and no damage with the player standing at the 3028 slam. 13912 shows in vanilla only as
# a TAE one-shot on dummypoly 230 (ground 2.41 m in front: the sword-into-ground hit of 3002 / 3003 / 3009 / 3014),
# not as a bullet effect; a bullet from the blade tip may also land too far from a player standing beside the boss.
# Round 6: look = TAE 96 (13912, dummypoly 230, 0.5 s) at the slam, damage = invisible bullet from the same dummypoly.
# Player (test #6): at the slam of both big leaps the blade is stuck in the ground (under the floor). Round 7: look
# and damage from the hilt, dummypoly 12 - the point of the Nightreign explosion bullets 465 / 475 / 485.
DMY_GROUND = 12
SLAM_LOOK = (FFX_SLAM, DMY_GROUND, 0.5)
# test #7: the explosion hits (3027: player HP down at 2.64-2.75 s, after the melee window 2.37-2.47, inside the
# bullet life 2.43-2.93 right after a roll) but reads poorly. Round 8: + the Dark Bead hit burst 20206 at the hilt,
# + the dark layer of the buff burst sound (3013: TAE 128 (7, 257005200) at 5.30), bullet life 0.5 -> 0.2 s.
SLAM_EXTRA_FFX = (FFX_BEAD_HIT, DMY_GROUND, 0.3)
SLAM_SOUND = (7, 257005200)
# Player (test #8): one roll must be able to dodge the slam and the explosion, but only a well-timed one - an early
# roll gets the explosion. Player roll 710: JT8 0.00-0.43 s (most likely the i-frames, 13 frames at 30 fps).
# Round 9: the ground hit shows at the slam, the dark burst + sound + damage SLAM_DELAY later, damage for
# SLAM_BULLET_LIFE. Melee start (3027 2.37, 3028 1.77, 3026 3.13) to explosion end ~0.27 s -> one roll covers both only
# when started in the last ~0.17 s (5 frames) before the melee hit; vanilla 3005 also hits the area 0.1 s after the sword.
SLAM_DELAY = 0.1
SLAM_BULLET_LIFE = 0.1
# Player (test #9): the hilt is high (3027 / 3028 plant the sword upright: work/boss_views/blade_at.py gives the hilt
# 1.33 m above the floor at the slam, blade vertical, 1.26 / 1.57 m in front; in 3026 the blade lies on the floor), so
# the burst at the hilt floats; wanted on the floor where the blade goes in, or on the blade at ~2/3-3/4 of its
# length. The only blade dummypolys: 12 hilt, 21 middle, 11 near the tip (18 past it); 21 is the lowest one that is
# not in the floor. The voice sound category 7 was Artorias' roar: now the buff burst sound (character, 410004005).
# Round 10: look, burst and damage at dummypoly 21.
DMY_GROUND = DMY_BLADE_MID
SLAM_LOOK = (FFX_SLAM, DMY_GROUND, 0.5)
SLAM_EXTRA_FFX = (FFX_BEAD_HIT, DMY_GROUND, 0.3)
SLAM_SOUND = (1, 410004005)
OLD_SLAM_EVENTS = {(FFX_SLAM, 230), (FFX_SLAM, 12), (FFX_BEAD_HIT, 12)}   # earlier rounds, removed on every run
OLD_SLAM_SOUNDS = {(7, 257005200), (1, 410004005)}
# Player (test #10): 410004005 is a scream of Artorias too. Sound types (TAE 128): 1 = character (c<chr>, only
# while that character's bank is loaded), 5 = SFX (s..., always loaded when in frpg_main.fev / fdlc_main.fev),
# 7 = voice. Round 11: one candidate small burst per leap, all SFX from the always-loaded main banks (names from the
# .fev files, use from a scan of every chr TAE, scratchpad sfx_sound_usage.py):
#   3026 -> s000020212 (fdlc_main, next to the Dark Bead FFX ids - maybe a dark sorcery hit; not used in any TAE)
#   3027 -> s000023111 (player pyromancy 6409 at 0.87 s, enemy c2380 attack 3007 at 2.03 s)
#   3028 -> s000022200 (player pyromancy 6409 at 1.20 s and 6417 at 0.63 s)
SLAM_SOUNDS = {3026: (5, 20212), 3027: (5, 23111), 3028: (5, 22200)}
# test #11: 3027 / 3028 candidates not heard at all; s000020212 (3026) heard, too quiet. A TAE sound event has no
# volume: round 12 plays s000020212 SLAM_SOUND_COPIES times at once on all three leaps.
OLD_SLAM_SOUNDS |= set(SLAM_SOUNDS.values())
SLAM_SOUNDS = {3026: (5, 20212), 3027: (5, 20212), 3028: (5, 20212)}
SLAM_SOUND_COPIES = 3
# test #11: 3026 has no blade-into-ground sound - the port took its sounds from 3007, whose hit comes earlier, and the
# Nightreign slam (hit 3.13 s) got none. Round 12: the landing sounds of 3027 (big-leap impact c410004003 on the tip,
# s410077777, s410099999 debris) copied to 3026, same offsets from the slam (3027 2.43 -> 3026 3.20).
CLANG_SRC, CLANG_DST = 3027, 3026
CLANG_IDS = {(8, 410003001), (1, 410004003), (5, 410077777), (5, 410099999)}
CLANG_WINDOW = (-0.1, 0.35)               # s around the source slam


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


def build_params(sf, hp: int, anim_offset: int, fx: bool = True, easy: bool = False) -> object:
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
    if fx:
        for vid, (mffx, mdmy, iffx, idmy) in TEST_VFX.items():
            v = clone_row(sf, vfx, VFX_AURA, vid, f"c4100 Artorias phase 2 test sword {vid} (mod)")
            print(f"SpEffectVfx {vid} (from {VFX_AURA}): " + "; ".join(edit_row(v, {
                "midstSfxId": mffx, "midstDmyId": mdmy, "initSfxId": iffx, "initDmyId": idmy})))
    changed.append((f_vfx, vfx))

    if fx:
        # the sword looks: the four tracks of look 1 are given by TAE 401 in 3016 at the burst
        print(f"SpEffect {SP_PHASE2} (test): " + "; ".join(edit_row(p2, {"stateInfo": TEST_BODY_AURA})))
        for look, tracks in enumerate(SP_LOOKS[:len(LOOK_VFX)]):
            for track, sid in enumerate(tracks):
                nxt = SP_LOOKS[(look + 1) % len(SP_LOOKS)][track]
                vrow = LOOK_VFX[look][track]
                single = len(SP_LOOKS) == 1 or len(LOOK_VFX) == 1
                vals = {"effectEndurance": -1.0 if single else FX_LOOK_TIME, "spCategory": 0, "stateInfo": 0,
                        "replaceSpEffectId": -1 if single else nxt}
                if isinstance(vrow, tuple):
                    vals.update({"motionInterval": PULSE_EVERY, "cycleOccurrenceSpEffectId": vrow[1]})
                else:
                    vals["stateInfo"] = vrow
                r = clone_row(sf, sp, SP_NEUTRAL, sid, f"c4100 Artorias phase 2 test look {look + 1} track {track + 1} (mod)")
                print(f"SpEffect {sid} (from {SP_NEUTRAL}): " + "; ".join(edit_row(r, vals)))
        for sid, vrow in TEST_PULSES.items():
            r = clone_row(sf, sp, SP_NEUTRAL, sid, "c4100 Artorias phase 2 test sword pulse (mod)")
            print(f"SpEffect {sid} (from {SP_NEUTRAL}): " + "; ".join(edit_row(r, {
                "effectEndurance": 0.05, "spCategory": 0, "stateInfo": vrow})))
    if easy:
        # test package only: phase 2 without the buff's x1.5 damage, so the player lives long enough to see the looks
        print(f"SpEffect {SP_PHASE2} (easy test): " + "; ".join(edit_row(p2, {
            k: 1.0 for k in ("physicsAttackPowerRate", "magicAttackPowerRate", "fireAttackPowerRate",
                             "thunderAttackPowerRate", "staminaAttackRate")})))

    f_atk, atk = open_param("AtkParam_Npc", "AtkParam")
    a = clone_row(sf, atk, ATK_AOE_SRC, ATK_AOE, "c4100 Artorias phase 2 slam explosion (mod)")
    # hit0 (3 m sphere on dummypoly 12) belongs to the melee area hit 410180; on a bullet it found no dummypoly 12
    # (test 13.11 #4: player standing 1.3 m from the 3028 slam, no damage) - a bullet without spheres (as the buff
    # burst 410510) hits with the Bullet hitRadius
    print(f"AtkParam_Npc {ATK_AOE} (from {ATK_AOE_SRC}): " + "; ".join(edit_row(a, {
        "atkPhys": 110, "atkMag": 110, "atkStam": 220, "hit0_Radius": 0.0, "hit0_DmyPoly1": -1})))
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
    if fx:
        # invisible: the look is a TAE one-shot of the ground-hit FFX at the same dummypoly (see SLAM_LOOK)
        for bid, ffx, radius in ((BULLET_AOE_S, -1, 1.5), (BULLET_AOE_M, -1, 2.0)):
            b = clone_row(sf, bu, BULLET_BUFF, bid, "[Knight Artorias] Phase 2 test slam explosion (mod)")
            print(f"Bullet {bid} (from {BULLET_BUFF}): " + "; ".join(edit_row(b, {
                "atkId_Bullet": ATK_AOE, "sfxId_Bullet": ffx, "sfxId_Hit": -1, "hitRadius": radius,
                "spEffectIDForShooter": -1, "life": SLAM_BULLET_LIFE})))
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
    behs = [(BEH_PHASE2, BULLET_PHASE2, "phase 2 burst"), (BEH_AOE, BULLET_AOE, "phase 2 slam explosion"),
            (BEH_BEAD_A, BULLET_BEAD_A, "phase 2 dark beads 1"), (BEH_BEAD_B, BULLET_BEAD_B, "phase 2 dark beads 2")]
    if fx:
        behs += [(BEH_AOE_S, BULLET_AOE_S, "phase 2 test slam small"), (BEH_AOE_M, BULLET_AOE_M, "phase 2 test slam mid")]
    for beh, ref, name in behs:
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


def build_anibnd(sf, fx: bool = True) -> object:
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
    tpl = {int(ev.Type): ev for ev in buff.Events if int(ev.Type) in (2, 96, 128, 401)}
    idle = next(a for a in tae.Animations if int(a.ID) == 0)
    tpl[100] = next(ev for ev in idle.Events if int(ev.Type) == 100)   # vanilla: endless smoke 13910 in slot 1
    for sid in (SP_LOOKS[0] if fx else (SP_SWORD,)):
        add_event(sf, na, SWORD_TIME, SWORD_TIME + 0.033, tpl[401], {0: sid})
    add_event(sf, na, SWORD_TIME, SWORD_TIME + 0.100, tpl[100], {0: FFX_SMOKE, 4: DMY_BLADE_TIP, 8: SLOT_SWORD_SMOKE})
    for t, beh in zip(BEAD_TIMES, (BEH_BEAD_A, BEH_BEAD_B)):
        add_event(sf, na, t, t + 0.033, tpl[2], {0: DMY_FRONT, 8: beh % 1000})
    pos = next((i for i, a in enumerate(tae.Animations) if int(a.ID) > ANIM_TRANSITION), tae.Animations.Count)
    tae.Animations.Insert(pos, na)
    print(f"anibnd: {ANIM_TRANSITION} = clip of {ANIM_BUFF}, {na.Events.Count} events "
          f"(401 -> {SP_TRANSITION}, bullet 510 -> {BEH_PHASE2 % 1000}, JT24 0.00-{end:.2f}; "
          f"401 {'/'.join(map(str, SP_LOOKS[0])) if fx else SP_SWORD} + smoke {FFX_SMOKE} slot {SLOT_SWORD_SMOKE} at {SWORD_TIME:.2f}, bead rings "
          f"{BEH_BEAD_A % 1000}/{BEH_BEAD_B % 1000} at {BEAD_TIMES[0]:.2f}/{BEAD_TIMES[1]:.2f} from dummypoly {DMY_FRONT})")

    # stage 2 in the phase-2 jump attacks: sparks from the jump to the slam, explosion at the slam
    my_behs = {BEH_AOE % 1000, BEH_AOE_S % 1000, BEH_AOE_M % 1000}
    for anim_id, (glow, slam) in AOE_MOVES.items():
        anim = next(a for a in tae.Animations if int(a.ID) == anim_id)
        kind, step, beh, start = FX_TEST_MOVES[anim_id] if fx else ("sparks", SPARK_STEP, BEH_AOE, None)
        trail_start = glow if start is None else start
        removed = 0
        for ev in list(anim.Events):
            p = bytes(ev.GetParameterBytes(False))
            ty = int(ev.Type)
            ints = struct.unpack_from(f"<{len(p) // 4}i", p) if len(p) >= 4 else ()
            start = float(ev.StartTime)
            # trail events of this script: tip sparks / energy inside the jump-to-slam window (the vanilla 3007
            # sparks copied into 3026 by the port end before 1.90 s and stay)
            my_trail = ty == 96 and len(ints) >= 3 and ints[0] in (FFX_SPARKS, FX_ENERGY) \
                and ints[1:3] == (DMY_BLADE_TIP, -1) and glow - 1e-3 <= start < slam - 1e-3
            mine = my_trail or (ty == 96 and tuple(ints[:3]) in OLD_FFX_EVENTS) \
                or (ty == 2 and len(ints) >= 3 and ints[2] in my_behs) \
                or (ty == 96 and len(ints) >= 2 and tuple(ints[:2]) in ({SLAM_LOOK[:2], SLAM_EXTRA_FFX[:2]} | OLD_SLAM_EVENTS)
                    and slam - 1e-3 <= start <= slam + 0.3) \
                or (ty == 128 and tuple(ints[:2]) in ({SLAM_SOUND} | OLD_SLAM_SOUNDS | set(SLAM_SOUNDS.values())) and slam - 1e-3 <= start <= slam + 0.3) \
                or (ty == 96 and anim_id in OLD_LANDING_FX[1] and tuple(ints[:2]) == OLD_LANDING_FX[0]) \
                or (ty == 1 and anim_id == 3027 and len(ints) >= 3 and ints[2] == BEH_VANILLA_AREA) \
                or (fx and anim_id == CLANG_DST and ty in (128, 129) and tuple(ints[:2]) in CLANG_IDS
                    and slam + CLANG_WINDOW[0] - 1e-3 <= start <= slam + CLANG_WINDOW[1] + 1e-3)
            if mine:
                anim.Events.Remove(ev)
                removed += 1
        if kind == "sparks":
            starts = [round(trail_start + i * step, 3) for i in range(int((slam - trail_start) / step + 1e-6))]
            for s in starts:
                add_event(sf, anim, s, s + SPARK_LEN, tpl[96], {0: FFX_SPARKS, 4: DMY_BLADE_TIP, 8: -1})
            trail = f"{len(starts)} spark spawns (every {step:.2f} s)"
        else:
            add_event(sf, anim, glow, slam, tpl[96], {0: FX_ENERGY, 4: DMY_BLADE_TIP, 8: -1})
            trail = f"energy {FX_ENERGY}"
        boom_dmy = DMY_GROUND if fx else DMY_BLADE_TIP
        boom = round(slam + SLAM_DELAY, 3) if fx else slam
        add_event(sf, anim, boom, boom + 0.033, tpl[2], {0: boom_dmy, 8: beh % 1000})
        if fx:
            add_event(sf, anim, slam, slam + SLAM_LOOK[2], tpl[96], {0: SLAM_LOOK[0], 4: SLAM_LOOK[1], 8: -1})
            add_event(sf, anim, boom, boom + SLAM_EXTRA_FFX[2], tpl[96],
                      {0: SLAM_EXTRA_FFX[0], 4: SLAM_EXTRA_FFX[1], 8: -1})
            snd = SLAM_SOUNDS.get(anim_id, SLAM_SOUND)
            for _ in range(SLAM_SOUND_COPIES):
                add_event(sf, anim, boom, boom + 0.067, tpl[128], {0: snd[0], 4: snd[1]})
            if anim_id == CLANG_DST:
                src_anim = next(a for a in tae.Animations if int(a.ID) == CLANG_SRC)
                src_slam = AOE_MOVES[CLANG_SRC][1]
                n_clang = 0
                for ev in src_anim.Events:
                    pb = bytes(ev.GetParameterBytes(False))
                    if int(ev.Type) not in (128, 129) or len(pb) < 8 or struct.unpack_from("<ii", pb) not in CLANG_IDS:
                        continue
                    rel = float(ev.StartTime) - src_slam
                    if not (CLANG_WINDOW[0] - 1e-3 <= rel <= CLANG_WINDOW[1] + 1e-3):
                        continue
                    s0 = round(slam + rel, 3)
                    anim.Events.Add(sf.TAE.Event(s0, s0 + float(ev.EndTime) - float(ev.StartTime), ev.Type, ev.Unk04,
                                                 net_bytes(pb), False))
                    n_clang += 1
                print(f"anibnd: {anim_id}: {n_clang} landing sound(s) copied from {CLANG_SRC}")
        print(f"anibnd: {anim_id}: {trail} {trail_start:.2f}-{slam:.2f}, explosion "
              f"{beh % 1000} at {slam:.2f} (dummypoly {boom_dmy}{', look ' + str(SLAM_LOOK[0]) if fx else ''}); "
              f"{removed} old event(s) removed")
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
    ap.add_argument("--tag", default="_v2", help="package folder files_c4100<tag> (test packages: _v2_test)")
    ap.add_argument("--old-fx", action="store_true", help="the 0.4.0 phase-2 effects instead of the tested ones")
    ap.add_argument("--easy", action="store_true", help="test package: phase 2 without the x1.5 damage of the buff")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(argv)
    if args.easy and args.tag == "_v2":
        ap.error("--easy only for a test package (--tag), the release takes files_c4100_v2")
    args.fx = not args.old_fx
    global PKG, ANIBND, PARAM_OUT
    PKG = PKG.with_name(f"files_c4100{args.tag}")
    ANIBND = PKG / "chr" / "c4100.anibnd.dcx"
    PARAM_OUT = PKG / "param" / "GameParam" / "GameParam.parambnd.dcx"
    sf = load_soulsformats()
    params = build_params(sf, args.hp, args.anim_offset, args.fx, args.easy)
    anibnd = build_anibnd(sf, args.fx)
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
