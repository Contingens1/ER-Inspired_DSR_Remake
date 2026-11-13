# CLAUDE.md — ds1-elden-port (ER-inspired movement for Dark Souls Remastered)

## Role
- You are the primary developer and maintainer of this repository.
- `gemini\` is a staging area for Gemini CLI output (reverse-engineering analysis, Ghidra dump reviews, multi-file diagnostics). Never trust or auto-merge files from `gemini\`. Review each change against project rules and integrate it by hand into `native\`, `tools\` or `docs\`.

## Communication
- Respond to the user in Polish, unless they explicitly ask otherwise.
- Write code, comments, scripts, commit messages and technical logs in English. New code only: existing Polish strings in old scripts stay as they are.
- Be direct and concrete. No greetings, filler or recaps of what was just said.
- Before changing several files, changing build pipelines, or refactoring core hooks: present a short numbered plan (affected files, risks, verification steps) and wait for confirmation.

## Context discipline
- Onboarding or checking project state: read `docs\PLAN_PROJEKTU.md` first. It is the single source of current state, offsets and the task list.
- Do not read `docs\ARCHIV\` unless the user asks. It holds history only.
- Do not read `docs\er_anim_a000.md` in full (72 KB). Use grep.
- Do not dump raw Ghidra output, decompilation logs, `.dcx`/`.dll`/`.bin` files or whole directories (`work\`, `dist\`, `toolsy\`, `gemini\`) into context. Search with grep or targeted reads.

## Directory map (`C:\Users\nemos\workspace\ds1-elden-port\`)
- `docs\PLAN_PROJEKTU.md` — current state, offsets, snapshots, task list. Keep it updated after each milestone.
- `docs\` — specs, reference tables (`weapon_groups_dsr_er.md`), technical notes.
- `docs\ARCHIV\` — archived notes and history. Read-only unless asked.
- `analysis\` — reverse-engineering findings, decompilation notes, offset research.
- `native\er_engine\` — C++ source of `er_engine.dll`.
  - `build.bat` — dev build (`/DER_DIAG=1` by default). The game must be closed or the DLL copy fails.
  - `build_release.ps1` — release build and packaging. Extend this script; do not create parallel build scripts.
- `tools\` — modding and conversion utilities (DCX, BND, TAE, animation, params). `tools\archive\` is obsolete, do not use.
- `work\` — scratch files, intermediate conversions and snapshots (`*_STABLE.*`). Snapshots are the rollback points.
- `dist\mods\c0000_er_engine\` — compiled mod for Mod Engine 2 (DLL, modified game assets, configs, launchers).
- `dist\release\` — final redistributable packages.
- `gemini\` — Gemini CLI staging (see Role).
- `toolsy\` — third-party tools (Nuxe, UXM, WitchyBND, ModEngine2, DSROmniRoll, soulstruct-havok). Download only from GitHub, no installers.

## Non-negotiable rules
1. **Zero vanilla interference.** Never modify, patch, move or delete original Dark Souls Remastered files. The game lives at `F:\SteamLibrary\steamapps\common\DARK SOULS REMASTERED\`. Read it, never write to it. All runtime changes go through Mod Engine 2 from `dist\mods\`.
2. **Production builds.** Every release build made by `build_release.ps1` MUST compile with `/DER_DIAG=0`. Diagnostic keys (F5–F9) and logging exist only in `ER_DIAG=1` builds.
3. **Snapshots.** Before a risky change, copy the working state to `work\` with a `*_STABLE` or dated suffix. After a regression, restore the snapshot instead of stacking fixes.
4. **Formats through libraries.** Read and write TAE, ESD, BND and DCX through SoulsFormats via `tools\sfbridge.py`. Do not write custom parsers for TAE or HKX(without asking and absolute need at least).
5. **No legacy dependencies.** Do not reintroduce DSROmniRoll, Simple Estus Walking or other removed external mods into the build, configs or release notes without asksing.
6. **Secrets.** Never print or commit `.env` files, API keys or local credentials.

## Working conventions
- Python scripts: write them to a file and run from there. Do not use heredocs in bash for Python (they break apostrophes and slashes).
- PowerShell: multi-line `.Replace` with "`n" fails on CRLF. Use the Edit tool or `[IO.File]` with `[Environment]::NewLine`.
- Ghidra headless: `JAVA_TOOL_OPTIONS=-Duser.name=nemos`, always `-readOnly`.
- Test each mechanic in the game before moving to the next stage. Record the result in `docs\PLAN_PROJEKTU.md`.

## Git & GitHub Workflow
(if git doesnt work continue working the old way and just let me know, dont interupt)
- **Commit & Push:** After completing a milestone, verified fix, or approved test, stage the modified source files, scripts, and documentation (`git add`), create a concise commit (`git commit`), and push to `origin main` (`git push`).
- **Releases:** When building a release package, if the `gh` CLI is available and authenticated, create a corresponding GitHub Release and attach the `.zip` archive.
- **Safety Rules:**
  - Do not commit large binary files, game archives, logs, or temporary artifacts.
  - Do not push untested experimental code directly to `main` (keep unverified experiments isolated in `dist/mods/` sandbox folders until tested).
  - Never run `git push --force` (without asking).

