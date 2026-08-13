# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- File-backed single source of truth: `scripts/cxwf.py` manages `.cxworkflow/`
  (state.json task state machine, append-only events.log, decisions.md, briefs/)
  so team state survives thread compaction and restarts.
- `cxwf check` validates event formats, severity values, forwarding rules, and
  task state transitions.
- Level-parameterized one-click prompts (`cxwf prompt --level 0-3`) so teams can
  start at minimal concurrency and scale up.
- Cross-platform local plugin update script (`scripts/update_local_plugin.py`)
  with thin PowerShell and bash wrappers; repo manifest keeps a clean semver and
  cachebusters are only written to installed/cache copies.
- Self-contained CI validator (`scripts/check_plugin.py`) and GitHub Actions
  workflow that runs unit tests + manifest/skill checks on every PR.
- Unit and golden tests under `tests/` covering the state machine, CLI, and
  protocol fields in the published prompts.
- Release helper (`scripts/release.py`) for keep-a-changelog version bumps.
- Self-install bootstrap: `AGENTS.md` (auto-loaded by Codex) plus
  `scripts/bootstrap.py`/`bootstrap.sh`/`bootstrap.ps1` that install the skill to
  `~/.codex/skills/` so a fresh Codex can adopt this workflow autonomously.
- Level-aware one-click prompts: L0/L1/L2 no longer reference Secretary/Reporter/obs
  sessions that do not exist at those levels; routing rules are generated per level.
- `cxwf check` hardening: validates required task fields, history transition
  legality, and history/status consistency (previously hand-edited state passed).
- `cxwf message`: record a Secretary message in the 8-field format with full
  validation; `cxwf level set <n>`; `cxwf rate-limit --count <n>` applies the
  1/3/5 consecutive-429 downgrade policy; `cxwf prompt --out <file>`.
- CLI ergonomics: `--version`, `task list` table, `status` dashboard (with
  `--json`), `check --json`, and automatic `--root` discovery from any
  subdirectory.
- Robustness: atomic `state.json` writes (temp + `os.replace`) and `check`
  validation of `load_level` / `paused`.
- MIT `LICENSE` file; CI badge in READMEs.
- CI: deduplicated test steps, `compileall` syntax check, ubuntu + windows
  matrix, and a hermetic bootstrap smoke test; new tests for bootstrap,
  check_plugin, and release.
- Plugin manifest metadata: homepage, repository, license, keywords, brandColor,
  logo, composer icon, and array-form default prompts.

## [0.1.0] - 2026-06-08

- Added the CXWorkflow multi-session coordination model.
- Added Secretary as the single source of truth and Commander inbox.
- Added structured Secretary routing with forwarding thresholds.
- Added task state machine and convergence mode.
- Added local plugin update guidance and tooling.
