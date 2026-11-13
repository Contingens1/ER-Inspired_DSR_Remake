"""Mapa kosci Asylum Demon (DSR c2230) -> Erdtree Avatar (ER c4810). Klucz: kosc DSR, wartosc: kosc ER."""
from __future__ import annotations


def c2230_to_c4810() -> dict[str, str]:
    m = {
        "Master": "Master", "Pelvis": "Pelvis", "Spine": "Spine", "Spine1": "Spine2", "Neck": "Neck", "Head": "Head",
        "Jaw": "Jaw", "Jaw2": "Jaw2", "Tongue_00": "Tongue", "Tongue_01": "Tongue02", "R_weapon": "R_Club",
        "a": "Stomach1", "b": "Stomach2", "c": "Stomach3", "d": "L_Hip2", "e": "R_Hip2",
    }
    for i in range(8):
        m[f"tail_{i:02d}"] = "Tail" if i == 0 else f"Tail{i + 1:02d}"
    for s in "LR":
        m[f"{s}ThighTwist"] = f"{s}_ThighTwist"
        m[f"{s}UpArmTwist"] = f"{s}_UpArmTwist"
        m[f"{s} ForeTwist"] = f"{s}_ForeArmTwist"
        for n in ("Thigh", "Calf", "Foot", "Clavicle", "UpperArm", "Forearm", "Hand"):
            m[f"{s} {n}"] = f"{s}_{n}"
        for f in range(4):
            for seg in ("", "1", "2"):
                m[f"{s} Finger{f}{seg}"] = f"{s}_Finger{f}{seg}"
        for t in range(3):
            m[f"{s} Toe{t}"] = f"{s}_FootFinger{3 - t}"
            m[f"{s} Toe{t}1"] = f"{s}_FootFinger{3 - t}02"
            m[f"{s} Toe{t}2"] = f"{s}_FootFinger{3 - t}03"
        for i in range(5):
            m[f"{s}_wing_{i:02d}"] = f"{s}_Wing1" if i == 0 else f"{s}_Wing1{i + 1:02d}"
        m[f"{s}_wing_digit_a_00"], m[f"{s}_wing_digit_a_01"], m[f"{s}_wing_digit_a_02"] = (
            f"{s}_Wing3", f"{s}_Wing302", f"{s}_Wing303")
        m[f"{s}_wing_digit_b_00"], m[f"{s}_wing_digit_b_01"] = f"{s}_Wing4", f"{s}_Wing402"
        m[f"{s}_wing_digit_c"] = f"{s}_Wing2"
        m[f"{s}_ear_00"], m[f"{s}_ear_01"], m[f"{s}_ear_02"] = f"{s}_Ear", f"{s}_Ear02", f"{s}_Ear03"
    return m
