"""Artorias (c4100, AI 410000) battle script for DSR with the Nightreign phase-2 moves.

Starts from the decompiled DSR script (work/boss_ai/dsr_m12_01/410000_battle.lua, made by
`tools/ai_lua.py dump m12_01_00_00 work/boss_ai/dsr_m12_01`) and applies a fixed list of edits, so the
result is reproducible. Nightreign's own script (work/boss_ai/nr_772000) is the same DS1 script plus a
second phase; the phase-2 ideas are carried over with DS1 goals, tuned for the closed DSR arena:

  phase 2 = HP <= 65 % (NR threshold)
  3004 -> 3024 (NR 3033), 3007 -> 3025 (NR 3034)            follow-ups, 60 % / 55 %
  3027 -> 3028 instead of the plain charge 3005
  3003 -> [3009] -> 3026                                    gap-closer chain
  3017 -> 3018 -> 3019 (NR 3030 -> 3031 -> 3032)            new three-part combo (Act14)
  timer 3: after a long-travel move (3026, 3027, 3017 chain) no other one for 12-14 s
  less backing off after attacks in phase 2

New animation numbers stay inside 3000-3029, the range enemyCommon.esd accepts.

  python tools/make_artorias_ai.py            # writes the .lua and builds the luabnd into the test package
  python tools/make_artorias_ai.py 1.0 _p2test   # test variant: phase 2 from the start of the fight
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
# 2026-11-13, player's decision: no phase switch - the extra moves are available for the whole fight
# (a buff-triggered phase would be skipped by anyone who interrupts the buff). 0.65 = NR threshold.
PHASE2 = "1.0"
USE_3026 = False


def sub_once(text: str, old: str, new: str) -> str:
    if text.count(old) != 1:
        raise RuntimeError(f"expected exactly one match, got {text.count(old)}: {old[:70]!r}")
    return text.replace(old, new)


HELPER = f'''function Artorius410000_Odds(ai, normal, buffed)
    if ai:HasSpecialEffectId(TARGET_SELF, 5510) then
        return buffed
    end
    if ai:GetHpRate(TARGET_SELF) <= {PHASE2} then
        return (normal + buffed) / 2
    end
    return normal
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

PHASE2_WEIGHTS = f'''    if targetDist < 3 and actPerArr[7] == 0 and actPerArr[10] == 0 and actPerArr[11] == 0 and actPerArr[12] == 0 and actPerArr[20] == 0 then
        actPerArr[15] = 15
    end
    if hprate <= {PHASE2} and actPerArr[7] == 0 and actPerArr[10] == 0 and actPerArr[11] == 0 and actPerArr[12] == 0 and actPerArr[20] == 0 then
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
            actPerArr[5] = 0
            if 10 < actPerArr[8] then
                actPerArr[8] = 10
            end
        end
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

    # Common_Clear_Param zeroes the arrays it knows about; make sure the slots tested below exist.
    t = sub_once(t, "    ai:SetNumber(0, 0)\n    local hprate = ai:GetHpRate(TARGET_SELF)\n",
                 "    ai:SetNumber(0, 0)\n    actPerArr[7] = 0\n    actPerArr[8] = 0\n    actPerArr[10] = 0\n"
                 "    actPerArr[11] = 0\n    actPerArr[12] = 0\n    actPerArr[14] = 0\n    actPerArr[15] = 0\n    actPerArr[20] = 0\n"
                 "    local hprate = ai:GetHpRate(TARGET_SELF)\n")
    t = sub_once(t, "    actFuncArr[1] = REGIST_FUNC(ai, goal, Artorius410000_Act01)\n",
                 PHASE2_WEIGHTS + "    actFuncArr[1] = REGIST_FUNC(ai, goal, Artorius410000_Act01)\n")
    t = sub_once(t, "    actFuncArr[13] = REGIST_FUNC(ai, goal, Artorius410000_Act13)\n",
                 "    actFuncArr[13] = REGIST_FUNC(ai, goal, Artorius410000_Act13)\n"
                 "    actFuncArr[14] = REGIST_FUNC(ai, goal, Artorius410000_Act14)\n"
                 # Act15 = Act10 (leap-back slash 3008) offered also when the player stands in front, close
                 # (the original only uses it when the player is behind); the player liked this move.
                 "    actFuncArr[15] = REGIST_FUNC(ai, goal, Artorius410000_Act10)\n")

    # Act03: 3004 -> 3024 (NR 3033)
    t = sub_once(t, "    goal:AddSubGoal(GOAL_COMMON_Attack, 10, 3004, TARGET_ENE_0, AttDist, 0)\n",
                 f"    if ai:GetHpRate(TARGET_SELF) <= {PHASE2} and ai:GetRandam_Int(1, 100) <= 60 then\n"
                 # success angle 180 / no distance limit: 3004 travels 11 m and usually ends beside the player,
                 # with the stock 90-degree check the follow-up was dropped (1 of 6 in the test log)
                 "        goal:AddSubGoal(GOAL_COMMON_CommonAttack, 10, 3004, TARGET_ENE_0, 999, 180, 0, 90, true, true, false, false, 0, 0)\n"
                 "        goal:AddSubGoal(GOAL_COMMON_ComboFinal, 10, 3024, TARGET_ENE_0, 999, 0)\n"
                 "    else\n"
                 "        goal:AddSubGoal(GOAL_COMMON_Attack, 10, 3004, TARGET_ENE_0, AttDist, 0)\n"
                 "    end\n")
    # Act04: 3007 -> 3025 (NR 3034)
    t = sub_once(t, "    if fate <= 70 then\n        goal:AddSubGoal(GOAL_COMMON_AttackTunableSpin, 10, 3007, TARGET_ENE_0, AttDist, -1, 25)\n",
                 f"    if ai:GetHpRate(TARGET_SELF) <= {PHASE2} and fate <= 55 then\n"
                 "        goal:AddSubGoal(GOAL_COMMON_CommonAttack, 10, 3007, TARGET_ENE_0, 999, 180, 1.5, 25, true, true, false, false, 0, 0)\n"
                 "        goal:AddSubGoal(GOAL_COMMON_ComboFinal, 10, 3025, TARGET_ENE_0, 999, 0)\n"
                 "    elseif fate <= 70 then\n"
                 "        goal:AddSubGoal(GOAL_COMMON_AttackTunableSpin, 10, 3007, TARGET_ENE_0, AttDist, -1, 25)\n")
    # Act05: 3027 -> 3028 instead of the plain charge
    t = sub_once(t, "    ai:SetTimer(1, 0)\n    if Distmin <= targetDist and targetDist <= Distmax then\n",
                 "    ai:SetTimer(1, 0)\n"
                 f"    if ai:GetHpRate(TARGET_SELF) <= {PHASE2} then\n"
                 "        ai:SetTimer(3, 12)\n"
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
    # Act08: 3003 -> [3009] -> 3026. Switched off 2026-11-13: 3026 repositions ~11 m sideways and then leaps
    # back at the target with a run-time scaled jump (TAE 760, 2.5-15 m) that DSR cannot do, so it missed.
    if USE_3026:
      t = sub_once(t, "    if fate <= 40 then\n        goal:AddSubGoal(GOAL_COMMON_AttackTunableSpin, 10, 3003, TARGET_ENE_0, AttDist, -1, 60)\n",
                 f"    if ai:GetHpRate(TARGET_SELF) <= {PHASE2} and ai:IsFinishTimer(3) == true and fate <= 40 then\n"
                 "        ai:SetTimer(3, 12)\n"
                 "        goal:AddSubGoal(GOAL_COMMON_CommonAttack, 10, 3003, TARGET_ENE_0, 999, 180, 1.5, 60, true, true, false, false, 0, 0)\n"
                 "        if fate <= 20 then\n"
                 "            goal:AddSubGoal(GOAL_COMMON_ComboRepeat_SuccessAngle180, 10, 3009, TARGET_ENE_0, 999, 0, 0)\n"
                 "        end\n"
                 "        goal:AddSubGoal(GOAL_COMMON_ComboFinal, 10, 3026, TARGET_ENE_0, 999, 0)\n"
                 "        GetWellSpace_Odds = Artorius410000_Odds(ai, 80, 30)\n"
                 "        return GetWellSpace_Odds\n"
                 "    end\n"
                 "    if fate <= 40 then\n"
                 "        goal:AddSubGoal(GOAL_COMMON_AttackTunableSpin, 10, 3003, TARGET_ENE_0, AttDist, -1, 60)\n")
    t = sub_once(t, "function Artorius410000_Act20(ai, goal, paramTbl)\n",
                 HELPER + "function Artorius410000_Act20(ai, goal, paramTbl)\n")
    if re.search(r"\d,\d", t):
        raise RuntimeError("decimal comma left in the script")
    out_lua, out_bnd = OUT_LUA, OUT_BND
    if len(sys.argv) > 2:  # test variant: other phase-2 threshold, written to files_c4100_v2<tag>
        phase, tag = sys.argv[1], sys.argv[2]
        n = t.count(f"<= {PHASE2}")
        t = t.replace(f"<= {PHASE2}", f"<= {phase}")
        print(f"phase-2 threshold {PHASE2} -> {phase} in {n} places")
        out_lua = OUT_LUA.with_name(f"410000_battle.nr_v2{tag}.lua")
        out_bnd = OUT_BND.parents[1].with_name(f"files_c4100_v2{tag}") / "script" / OUT_BND.name
    out_lua.write_text(t, encoding="shift_jis", newline="\n")
    print(f"written {out_lua} ({len(t.splitlines())} lines)")
    out_bnd.parent.mkdir(parents=True, exist_ok=True)
    return subprocess.call([sys.executable, str(ROOT / "tools" / "ai_lua.py"), "build", "m12_01_00_00",
                            "410000_battle.lua", str(out_lua), str(out_bnd)])


if __name__ == "__main__":
    sys.exit(main())
