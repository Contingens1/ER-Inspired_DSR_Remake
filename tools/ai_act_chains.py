"""List the attack sequence of every function in a decompiled DSR battle AI (read-only).

  python tools\\ai_act_chains.py work/boss_ai/dsr_m18_00/279000_battle.lua

Per function: the attack animation IDs of its AddSubGoal calls in source order (Attack / ComboAttack / ComboFinal /
ComboRepeat ...), plus the goal kinds, so combos read as "3000 > 3001 > 3004".
"""
import re
import sys
from pathlib import Path

src = Path(sys.argv[1]).read_text(encoding="utf-8", errors="ignore")
funcs = re.split(r"\n(?=function |\w+\s*=\s*function)", src)
call = re.compile(r"AddSubGoal\(GOAL_COMMON_(\w+),\s*[\d.,]+,\s*(\d{4,5})\b")
for f in funcs:
    m = re.match(r"(?:function\s+([\w.:]+)|(\w+)\s*=\s*function)", f)
    if not m:
        continue
    name = m.group(1) or m.group(2)
    seq = [(k, a) for k, a in call.findall(f) if "Attack" in k or "Combo" in k]
    if seq:
        print(f"{name}: " + " > ".join(f"{a}({k.replace('Attack', 'A').replace('Combo', 'C')})" for k, a in seq))
