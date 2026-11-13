"""Artorias (c4100, AI 410000) battle script for DSR with a Nightreign-style second phase.

Starts from the decompiled DSR script (work/boss_ai/dsr_m12_01/410000_battle.lua, made by
`tools/ai_lua.py dump m12_01_00_00 work/boss_ai/dsr_m12_01`) and applies a fixed list of edits, so the
result is reproducible. Nightreign's own script (work/boss_ai/nr_772000) is the same DS1 script plus a
second phase; its phase-2 ideas are carried over with DS1 goals, tuned for the closed DSR arena.

Phases (player's decisions 2026-11-13, docs/PLAN_PROJEKTU.md §6a):
  phase 1 = the DS1 moveset only, no buff (the vanilla buff act 12 is switched off)
  HP ~0   = the DLL keeps the boss alive (ChrFlags2 NoDead); the AI plays 3016 (act 16) = the buff motion as an
            unbreakable transition (tools/artorias_phase2.py: no damage, HP refilled, burst gives SpEffect 5513)
  phase 2 = SpEffect 5513 (permanent buff + animIdOffset 10000) - every Nightreign move:
    3004 -> 3024 (NR 3033), 3007 -> 3025 (NR 3034)            follow-ups, 60 % / 55 %
    3027 -> 3028 instead of the plain charge 3005
    3003 -> [3009] -> 3026                                    gap-closer chain (off: USE_3026)
    3017 -> 3018 -> 3019 (NR 3030 -> 3031 -> 3032)            three-part combo (act 14)
    timer 3: after a long-travel move (3026, 3027, 3017 chain) no other one for 12-14 s
    less backing off after attacks (the "buffed" odds of the vanilla script)

New animation numbers stay inside 3000-3029, the range enemyCommon.esd accepts.

  python tools/make_artorias_ai.py            # writes the .lua and builds the luabnd into the test package
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "work" / "boss_ai" / "dsr_m12_01" / "410000_battle.lua"
OUT_LUA = ROOT / "work" / "boss_ai" / "410000_battle.nr_v2.lua"
OUT_BND = ROOT / "dist" / "mods" / "bossy_nightreign" / "files_c4100_v2" / "script" / "m12_01_00_00.luabnd.dcx"
USE_3026 = True   # 2026-11-13: back on, the leap is stretched to ~9.5 m (--rm-scale-window 1003026:2.83:3.17:2.65)
P2 = "Artorius410000_Phase2(ai)"          # phase-2 test in the edited acts
TRANSITION_HP = "0.01"                    # HP rate that ends phase 1 (the DLL holds the boss at >= 0 HP)


def sub_once(text: str, old: str, new: str) -> str:
    if text.count(old) != 1:
        raise RuntimeError(f"expected exactly one match, got {text.count(old)}: {old[:70]!r}")
    return text.replace(old, new)


HELPER = f'''-- (mod) phase 2 = SpEffect 5513, given by the burst of the transition 3016 (tools/artorias_phase2.py)
function Artorius410000_Phase2(ai)
    return ai:HasSpecialEffectId(TARGET_SELF, 5513)
end

-- (mod) no buff in either phase: phase 1 is the easier DS1 moveset, phase 2 is permanently buffed (5513)
function Artorius410000_CanBuff(ai)
    return false
end

function Artorius410000_Odds(ai, normal, buffed)
    if ai:HasSpecialEffectId(TARGET_SELF, 5510) or Artorius410000_Phase2(ai) then
        return buffed
    end
    return normal
end

-- (mod) end of phase 1: the buff motion 3016 as an unbreakable transition (no damage, HP refilled)
function Artorius410000_Act16(ai, goal, paramTbl)
    ai:SetNumber(5, 1)
    goal:AddSubGoal(GOAL_COMMON_AttackTunableSpin, 12, 3016, TARGET_ENE_0, DIST_None, 0, 90)
    GetWellSpace_Odds = 0
    return GetWellSpace_Odds
end

function Artorius410000_Act14(ai, goal, paramTbl)
    local targetDist = ai:GetDist(TARGET_ENE_0)
    local AppDist = 6
    local DashDist = 8
    local fate = ai:GetRandam_Int(1, 100)
    ai:SetTimer(3, 14)
    if AppDist <= targetDist then
        Approach_Act(ai, goal, AppDist, DashDist, 0, 3)
    end
    goal:AddSubGoal(GOAL_COMMON_CommonAttack, 10, 3017, TARGET_ENE_0, 999, 180, 0, 90, true, true, false, false, 0, 0)
    if fate <= 70 then
        goal:AddSubGoal(GOAL_COMMON_ComboRepeat_SuccessAngle180, 10, 3018, TARGET_ENE_0, 999, 0, 0)
        goal:AddSubGoal(GOAL_COMMON_ComboFinal, 10, 3019, TARGET_ENE_0, 999, 0)
    else
        goal:AddSubGoal(GOAL_COMMON_ComboFinal, 10, 3018, TARGET_ENE_0, 999, 0)
    end
    GetWellSpace_Odds = Artorius410000_Odds(ai, 60, 20)
    return GetWellSpace_Odds
end

'''

PHASE2_WEIGHTS = f'''    if actPerArr[16] == 0 then
        if targetDist < 3 and actPerArr[7] == 0 and actPerArr[10] == 0 and actPerArr[11] == 0 and actPerArr[12] == 0 and actPerArr[20] == 0 then
            actPerArr[15] = 15
        end
        if {P2} and actPerArr[7] == 0 and actPerArr[10] == 0 and actPerArr[11] == 0 and actPerArr[12] == 0 and actPerArr[20] == 0 then
            -- (mod) 3027 -> 3028 (act 5) on its own cooldown (timer 4), also from mid range: test 2026-11-13 showed
            -- none in phase 2 (act 5 only from 9 m, blocked 14 s after every 3017 chain by timer 3)
            if ai:IsFinishTimer(4) == true then
                if 15 <= targetDist then
                    actPerArr[5] = 60
                elseif 9 <= targetDist then
                    actPerArr[5] = 35
                elseif 7 <= targetDist then
                    actPerArr[5] = 15
                end
            else
                actPerArr[5] = 0
            end
            if ai:IsFinishTimer(3) == true then
                if 9 <= targetDist then
                    actPerArr[14] = 0
                elseif 7 <= targetDist then
                    actPerArr[14] = 30
                elseif 5 <= targetDist then
                    actPerArr[14] = 35
                elseif 3 <= targetDist then
                    actPerArr[14] = 30
                else
                    actPerArr[14] = 20
                end
            else
                if 10 < actPerArr[8] then
                    actPerArr[8] = 10
                end
            end
        end
    end
'''

# (mod) Reactions to the player healing / shooting from afar used the plain leap 3005: in phase 2 the double leap.
FAR_LEAP = f'''-- (mod) far reaction leap: 3005 in phase 1, 3027 -> 3028 in phase 2
function Artorius410000_FarLeap(ai, goal)
    if {P2} then
        ai:SetTimer(4, 15)
        goal:AddSubGoal(GOAL_COMMON_CommonAttack, 2, 3027, TARGET_ENE_0, 999, 180, 0, 90, true, true, false, false, 0, 0)
        goal:AddSubGoal(GOAL_COMMON_ComboFinal, 10, 3028, TARGET_ENE_0, 999, 0)
    else
        goal:AddSubGoal(GOAL_COMMON_AttackTunableSpin, 2, 3005, TARGET_ENE_0, DIST_None, 0, 90)
    end
end

'''

INTERRUPT_TRANSITION = f'''    if hprate <= {TRANSITION_HP} and {P2} == false and ai:GetNumber(5) == 0 then
        ai:SetNumber(5, 1)
        goal:ClearSubGoal()
        goal:AddSubGoal(GOAL_COMMON_AttackTunableSpin, 12, 3016, TARGET_ENE_0, DIST_None, 0, 90)
        return true
    end
'''


def main() -> int:
    t = SRC.read_text(encoding="shift_jis")
    t = re.sub(r"(?<=\d),(?=\d)", ".", t)  # the decompiler prints decimals with the Polish locale comma
    t, n = re.subn(
        r"if ai:HasSpecialEffectId\(TARGET_SELF, 5510\) then\n\s+GetWellSpace_Odds = (\d+)\n\s+else\n"
        r"\s+GetWellSpace_Odds = (\d+)\n\s+end",
        r"GetWellSpace_Odds = Artorius410000_Odds(ai, \2, \1)", t)
    print(f"odds blocks rewritten: {n}")
    # The vanilla buff (act 12, 3013) is chosen by six branches that all test timer 0: switch them off.
    t, n = re.subn(r"ai:IsFinishTimer\(0\) == true", "ai:IsFinishTimer(0) == true and Artorius410000_CanBuff(ai)", t)
    if n != 6:
        raise RuntimeError(f"expected 6 buff branches, got {n}")
    print(f"buff branches switched off: {n}")

    # Common_Clear_Param zeroes the arrays it knows about; make sure the slots tested below exist.
    t = sub_once(t, "    ai:SetNumber(0, 0)\n    local hprate = ai:GetHpRate(TARGET_SELF)\n",
                 "    ai:SetNumber(0, 0)\n    actPerArr[7] = 0\n    actPerArr[8] = 0\n    actPerArr[10] = 0\n"
                 "    actPerArr[11] = 0\n    actPerArr[12] = 0\n    actPerArr[14] = 0\n    actPerArr[15] = 0\n"
                 "    actPerArr[16] = 0\n    actPerArr[20] = 0\n"
                 "    local hprate = ai:GetHpRate(TARGET_SELF)\n")
    # End of phase 1 first: nothing else is chosen while the boss is at ~0 HP without phase 2.
    t = sub_once(t, "    if ai:IsInsideTarget(TARGET_ENE_0, AI_DIR_TYPE_B, 120) and fate <= 70 then\n"
                    "        if targetDist <= 3 then\n",
                 f"    if hprate <= {TRANSITION_HP} and {P2} == false then\n"
                 "        actPerArr[16] = 100\n"
                 "    elseif ai:IsInsideTarget(TARGET_ENE_0, AI_DIR_TYPE_B, 120) and fate <= 70 then\n"
                 "        if targetDist <= 3 then\n")
    t = sub_once(t, "    actFuncArr[1] = REGIST_FUNC(ai, goal, Artorius410000_Act01)\n",
                 PHASE2_WEIGHTS + "    actFuncArr[1] = REGIST_FUNC(ai, goal, Artorius410000_Act01)\n")
    t = sub_once(t, "    actFuncArr[13] = REGIST_FUNC(ai, goal, Artorius410000_Act13)\n",
                 "    actFuncArr[13] = REGIST_FUNC(ai, goal, Artorius410000_Act13)\n"
                 "    actFuncArr[14] = REGIST_FUNC(ai, goal, Artorius410000_Act14)\n"
                 # Act15 = Act10 (leap-back slash 3008) offered also when the player stands in front, close
                 # (the original only uses it when the player is behind); the player liked this move.
                 "    actFuncArr[15] = REGIST_FUNC(ai, goal, Artorius410000_Act10)\n"
                 "    actFuncArr[16] = REGIST_FUNC(ai, goal, Artorius410000_Act16)\n")
    # No after-attack step / spacing at the end of phase 1 (test 2026-11-13: 3004 ran out, then a step back 701
    # delayed the transition by 1.4 s): go straight to act 16.
    t = sub_once(t, "function Artorius410000_ActAfter(ai, goal)\n",
                 "function Artorius410000_ActAfter(ai, goal)\n"
                 f"    if ai:GetHpRate(TARGET_SELF) <= {TRANSITION_HP} and {P2} == false then\n"
                 "        return \n"
                 "    end\n")
    # The killing blow of phase 1 interrupts whatever the boss is doing and starts the transition at once
    # (only when the hit gets through: during a super-armoured attack the boss finishes it first).
    t = sub_once(t, "    local hprate = ai:GetHpRate(TARGET_SELF)\n    if ai:IsInterupt(INTERUPT_TargetIsGuard) and ai:GetNumber(0) == 1 then\n",
                 "    local hprate = ai:GetHpRate(TARGET_SELF)\n" + INTERRUPT_TRANSITION
                 + "    if ai:IsInterupt(INTERUPT_TargetIsGuard) and ai:GetNumber(0) == 1 then\n")

    # Act03: 3004 -> 3024 (NR 3033)
    t = sub_once(t, "    goal:AddSubGoal(GOAL_COMMON_Attack, 10, 3004, TARGET_ENE_0, AttDist, 0)\n",
                 f"    if {P2} and ai:GetRandam_Int(1, 100) <= 60 then\n"
                 # success angle 180 / no distance limit: 3004 travels 11 m and usually ends beside the player,
                 # with the stock 90-degree check the follow-up was dropped (1 of 6 in the test log)
                 "        goal:AddSubGoal(GOAL_COMMON_CommonAttack, 10, 3004, TARGET_ENE_0, 999, 180, 0, 90, true, true, false, false, 0, 0)\n"
                 "        goal:AddSubGoal(GOAL_COMMON_ComboFinal, 10, 3024, TARGET_ENE_0, 999, 0)\n"
                 "    else\n"
                 "        goal:AddSubGoal(GOAL_COMMON_Attack, 10, 3004, TARGET_ENE_0, AttDist, 0)\n"
                 "    end\n")
    # Act04: 3007 -> 3025 (NR 3034)
    t = sub_once(t, "    if fate <= 70 then\n        goal:AddSubGoal(GOAL_COMMON_AttackTunableSpin, 10, 3007, TARGET_ENE_0, AttDist, -1, 25)\n",
                 f"    if {P2} and fate <= 55 then\n"
                 "        goal:AddSubGoal(GOAL_COMMON_CommonAttack, 10, 3007, TARGET_ENE_0, 999, 180, 1.5, 25, true, true, false, false, 0, 0)\n"
                 "        goal:AddSubGoal(GOAL_COMMON_ComboFinal, 10, 3025, TARGET_ENE_0, 999, 0)\n"
                 "    elseif fate <= 70 then\n"
                 "        goal:AddSubGoal(GOAL_COMMON_AttackTunableSpin, 10, 3007, TARGET_ENE_0, AttDist, -1, 25)\n")
    # Act05: 3027 -> 3028 instead of the plain charge
    t = sub_once(t, "    ai:SetTimer(1, 0)\n    if Distmin <= targetDist and targetDist <= Distmax then\n",
                 "    ai:SetTimer(1, 0)\n"
                 f"    if {P2} then\n"
                 "        ai:SetTimer(4, 15)\n"
                 "        if targetDist <= Distmin then\n"
                 "            goal:AddSubGoal(GOAL_COMMON_SpinStep, 5, 701, TARGET_ENE_0, 0, AI_DIR_TYPE_B, 5)\n"
                 "        elseif Distmax < targetDist then\n"
                 "            Approach_Act(ai, goal, AppDist, DashDist, Odds_Guard, 3)\n"
                 "        end\n"
                 "        goal:AddSubGoal(GOAL_COMMON_CommonAttack, 10, 3027, TARGET_ENE_0, 999, 180, 0, 90, true, true, false, false, 0, 0)\n"
                 "        goal:AddSubGoal(GOAL_COMMON_ComboFinal, 10, 3028, TARGET_ENE_0, 999, 0)\n"
                 "        GetWellSpace_Odds = Artorius410000_Odds(ai, 100, 30)\n"
                 "        return GetWellSpace_Odds\n"
                 "    end\n"
                 "    if Distmin <= targetDist and targetDist <= Distmax then\n")
    # Act08: 3003 -> [3009] -> 3026. 3026 repositions ~10 m sideways and leaps back at the target; NR scales that
    # leap at run time (TAE 760), here it is stretched once in the port (--rm-scale-window). As in NR phase 2 the
    # flip chain always ends with 3026: 40 % 3003, 30 % 3003 + 3009, 30 % 3003 + 3009 x2 (test 2026-11-13 with
    # 40 % of chains: seen once, after the player had died).
    if USE_3026:
      t = sub_once(t, "    if fate <= 40 then\n        goal:AddSubGoal(GOAL_COMMON_AttackTunableSpin, 10, 3003, TARGET_ENE_0, AttDist, -1, 60)\n",
                 f"    if {P2} and ai:IsFinishTimer(3) == true then\n"
                 "        ai:SetTimer(3, 12)\n"
                 "        goal:AddSubGoal(GOAL_COMMON_CommonAttack, 10, 3003, TARGET_ENE_0, 999, 180, 1.5, 60, true, true, false, false, 0, 0)\n"
                 "        if 40 < fate then\n"
                 "            goal:AddSubGoal(GOAL_COMMON_ComboRepeat_SuccessAngle180, 10, 3009, TARGET_ENE_0, 999, 0, 0)\n"
                 "        end\n"
                 "        if 70 < fate then\n"
                 "            goal:AddSubGoal(GOAL_COMMON_ComboRepeat_SuccessAngle180, 10, 3009, TARGET_ENE_0, 999, 0, 0)\n"
                 "        end\n"
                 "        goal:AddSubGoal(GOAL_COMMON_ComboFinal, 10, 3026, TARGET_ENE_0, 999, 0)\n"
                 "        GetWellSpace_Odds = Artorius410000_Odds(ai, 80, 30)\n"
                 "        return GetWellSpace_Odds\n"
                 "    end\n"
                 "    if fate <= 40 then\n"
                 "        goal:AddSubGoal(GOAL_COMMON_AttackTunableSpin, 10, 3003, TARGET_ENE_0, AttDist, -1, 60)\n")
    # Far reactions of the interrupt handler (player heals / shoots from 10-11 m+): 3005 -> FarLeap (phase-aware).
    far = "goal:AddSubGoal(GOAL_COMMON_AttackTunableSpin, 2, 3005, TARGET_ENE_0, DIST_None, 0, 90)"
    if t.count(far) != 2:
        raise RuntimeError(f"expected 2 far-reaction leaps, got {t.count(far)}")
    t = t.replace(far, "Artorius410000_FarLeap(ai, goal)")
    t = sub_once(t, "function Artorius410000_Act20(ai, goal, paramTbl)\n",
                 HELPER + FAR_LEAP + "function Artorius410000_Act20(ai, goal, paramTbl)\n")
    if re.search(r"\d,\d", t):
        raise RuntimeError("decimal comma left in the script")
    OUT_LUA.write_text(t, encoding="shift_jis", newline="\n")
    print(f"written {OUT_LUA} ({len(t.splitlines())} lines)")
    OUT_BND.parent.mkdir(parents=True, exist_ok=True)
    return subprocess.call([sys.executable, str(ROOT / "tools" / "ai_lua.py"), "build", "m12_01_00_00",
                            "410000_battle.lua", str(OUT_LUA), str(OUT_BND)])


if __name__ == "__main__":
    sys.exit(main())
