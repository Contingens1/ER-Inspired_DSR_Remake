"""
Patch vanilla DSR c0000.esd.dcx to enable walking and turning during Estus / crush-item animations.

Reads clean vanilla DSR chr/c0000.esd.dcx (read-only) via tools/sfbridge.py (SoulsFormats.ESD)
and updates ONLY the 7 item-use states in StateGroup 1:
  - 1  (anim 7500), 15 (anim 7501)
  - 16 (anim 7585: Estus start), 17 (anim 7588: Estus empty),
    18 (anim 7586: Estus drink), 19 (anim 7587: Estus end), 20 (anim 7589: Estus shrug)

In each of those 7 states:
  - Removes SwitchMotion Cmd(1, 101) from EntryCommands and ExitCommands (removes leg movement lock).
  - Replaces full-body ChangeGeneralAnim Cmd(1, 3) on slot 6 with ChangeUpperBodyAnim Cmd(1, 1)
    on upper-body layer 5 (matching vanilla DSR resin states 26 & 28).
  - Switches the anim-end condition of those states to the upper-body slot.
  - Preserves all other 495 states, evaluators, and transitions in Group 0 and Group 1 untouched.

Replaces the third-party "Simple Estus Walking" ESD. Written by Gemini CLI in gemini/tools, reviewed and
moved here on 2026-11-12. Usage: python tools/patch_vanilla_esd.py
"""
from __future__ import annotations

import argparse
import struct
import sys
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS_DIR))
from sfbridge import load_soulsformats, net_bytes, read_file  # noqa: E402

DEFAULT_VANILLA = Path("F:/SteamLibrary/steamapps/common/DARK SOULS REMASTERED/chr/c0000.esd.dcx")
DEFAULT_OUT = Path(__file__).resolve().parent.parent / "dist" / "mods" / "c0000_er_engine" / "files" / "chr" / "c0000.esd.dcx"

# (state_id): (expected_anim_id, entry_blend_style, exit_blend_style)
# style "blend" -> (blend=0.1, start=0, weight=2) [like vanilla state 26]
# style "snap"  -> (blend=0,   start=0, weight=1) [like vanilla state 28]
TARGET_STATES: dict[int, tuple[int, str, str]] = {
    1: (7500, "blend", "snap"),
    15: (7501, "blend", "snap"),
    16: (7585, "blend", "blend"),
    17: (7588, "snap", "snap"),
    18: (7586, "snap", "snap"),
    19: (7587, "snap", "snap"),
    20: (7589, "snap", "snap"),
}


def ezl_int(val: int) -> bytes:
    if -64 <= val <= 63:
        return bytes([val + 64, 0xA1])
    return b"\x82" + struct.pack("<i", val) + b"\xA1"


def ezl_double(val: float) -> bytes:
    return b"\x81" + struct.pack("<d", val) + b"\xA1"


def make_upper_anim_cmd(ESD_cls, anim_id: int, style: str):
    cmd = ESD_cls.CommandCall(1, 1)  # ChangeUpperBodyAnim(animId, layer=5, blend, startFrame, flag)
    if style == "blend":
        raw_args = [ezl_int(anim_id), ezl_int(5), ezl_double(0.1), ezl_int(0), ezl_int(2)]
    elif style == "snap":
        raw_args = [ezl_int(anim_id), ezl_int(5), ezl_int(0), ezl_int(0), ezl_int(1)]
    else:
        raise ValueError(f"Unknown blend style: {style}")
    for arg in raw_args:
        cmd.Arguments.Add(net_bytes(arg))
    return cmd


def decode_ezl_int(raw: bytes) -> int | None:
    if len(raw) == 2 and 0x00 <= raw[0] <= 0x7F and raw[1] == 0xA1:
        return raw[0] - 64
    if len(raw) == 6 and raw[0] == 0x82 and raw[5] == 0xA1:
        return struct.unpack_from("<i", raw, 1)[0]
    return None


def patch_esd(src_path: Path, out_path: Path) -> int:
    if not src_path.is_file():
        raise FileNotFoundError(f"Vanilla ESD not found: {src_path}")
    if src_path.resolve() == out_path.resolve():
        raise ValueError("Refusing to overwrite source ESD file in place.")

    load_soulsformats()
    from SoulsFormats import ESD

    esd = read_file(ESD, str(src_path))
    group1 = next((kv.Value for kv in esd.StateGroups if int(kv.Key) == 1), None)
    if group1 is None:
        raise RuntimeError("StateGroup 1 not found in ESD.")

    states = {int(kv.Key): kv.Value for kv in group1}
    patched = 0

    for sid, (expected_anim, entry_style, exit_style) in sorted(TARGET_STATES.items()):
        st = states.get(sid)
        if st is None:
            raise RuntimeError(f"State {sid} missing in StateGroup 1.")

        # Verify vanilla EntryCommands: [Cmd(1,101)(0), Cmd(1,117)(1), Cmd(1,3)(3, animId, 6, 0.2, 0)]
        entry_cmds = list(st.EntryCommands)
        if len(entry_cmds) != 3:
            raise RuntimeError(f"State {sid}: unexpected EntryCommands count {len(entry_cmds)}")
        c_sw_in, c_flag_in, c_anim_in = entry_cmds
        if (int(c_sw_in.CommandBank), int(c_sw_in.CommandID)) != (1, 101):
            raise RuntimeError(f"State {sid}: expected Entry Cmd(1,101), got ({c_sw_in.CommandBank},{c_sw_in.CommandID})")
        if (int(c_flag_in.CommandBank), int(c_flag_in.CommandID)) != (1, 117):
            raise RuntimeError(f"State {sid}: expected Entry Cmd(1,117), got ({c_flag_in.CommandBank},{c_flag_in.CommandID})")
        if (int(c_anim_in.CommandBank), int(c_anim_in.CommandID)) != (1, 3):
            raise RuntimeError(f"State {sid}: expected Entry Cmd(1,3), got ({c_anim_in.CommandBank},{c_anim_in.CommandID})")
        actual_anim = decode_ezl_int(bytes(c_anim_in.Arguments[1]))
        if actual_anim != expected_anim:
            raise RuntimeError(f"State {sid}: expected anim {expected_anim}, got {actual_anim}")

        # Verify vanilla ExitCommands: [Cmd(1,3)(3, -1, 6, 0.2, 0), Cmd(1,117)(0), Cmd(1,101)(1)]
        exit_cmds = list(st.ExitCommands)
        if len(exit_cmds) != 3:
            raise RuntimeError(f"State {sid}: unexpected ExitCommands count {len(exit_cmds)}")
        c_anim_out, c_flag_out, c_sw_out = exit_cmds
        if (int(c_anim_out.CommandBank), int(c_anim_out.CommandID)) != (1, 3):
            raise RuntimeError(f"State {sid}: expected Exit Cmd(1,3), got ({c_anim_out.CommandBank},{c_anim_out.CommandID})")
        if (int(c_flag_out.CommandBank), int(c_flag_out.CommandID)) != (1, 117):
            raise RuntimeError(f"State {sid}: expected Exit Cmd(1,117), got ({c_flag_out.CommandBank},{c_flag_out.CommandID})")
        if (int(c_sw_out.CommandBank), int(c_sw_out.CommandID)) != (1, 101):
            raise RuntimeError(f"State {sid}: expected Exit Cmd(1,101), got ({c_sw_out.CommandBank},{c_sw_out.CommandID})")

        # Apply surgical upper-body replacement
        st.EntryCommands.Clear()
        st.EntryCommands.Add(c_flag_in)
        st.EntryCommands.Add(make_upper_anim_cmd(ESD, expected_anim, entry_style))

        st.ExitCommands.Clear()
        st.ExitCommands.Add(make_upper_anim_cmd(ESD, -1, exit_style))
        st.ExitCommands.Add(c_flag_out)

        # Switch anim-end condition from full-body IsAnimEnd(0) [40 40 85 ...] to upper-body IsAnimEnd(1) [41 40 85 ...].
        # IMPORTANT: Clone ESD.Condition rather than mutating in place, because SoulsFormats shares deduplicated
        # Condition instances across states (e.g. full-body states 2..14 share target=0, eval=404085a6a1).
        cond_idx = 0 if sid == 16 else len(st.Conditions) - 1
        cond = st.Conditions[cond_idx]
        eval_bytes = bytearray(bytes(cond.Evaluator))
        if eval_bytes[:3] != bytearray(b"\x40\x40\x85"):
            raise RuntimeError(
                f"State {sid} Condition[{cond_idx}]: expected prefix 404085, got {bytes(eval_bytes[:4]).hex()}"
            )
        eval_bytes[0] = 0x41  # slot 1 = upper-body animation (matches vanilla resin states 26 & 28)
        new_cond = ESD.Condition(int(cond.TargetState), net_bytes(bytes(eval_bytes)))
        for pc in cond.PassCommands:
            new_cond.PassCommands.Add(pc)
        for sc in cond.Subconditions:
            new_cond.Subconditions.Add(sc)
        st.Conditions[cond_idx] = new_cond
        patched += 1

    out_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = out_path.with_suffix(".tmp")
    esd.Write(str(tmp_path))
    tmp_path.replace(out_path)
    print(f"OK: patched {patched} states from vanilla DSR -> {out_path} ({out_path.stat().st_size} B)")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Patch vanilla DSR c0000.esd.dcx for walking Estus.")
    ap.add_argument("--src", type=Path, default=DEFAULT_VANILLA, help="Path to clean vanilla c0000.esd.dcx")
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT, help="Output path (default: the mod's files/chr)")
    args = ap.parse_args(argv)
    return patch_esd(args.src, args.out)


if __name__ == "__main__":
    raise SystemExit(main())
