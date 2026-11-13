# Simple Variable Speed — push / docs sweep prep

**Date:** 2026-11-13  
**Branch:** `main` (tracks `origin/main`)  
**Feature status:** Implemented in Prince Modern; documented; unit tests registered.  
**Docs sweep:** **Complete** (2026-11-13).

This note is a checklist for the **GitHub commit/push**. Do **not** treat it as authorization to commit or push — wait for an explicit ask.

## Feature is in the working tree

| Path | Role |
|------|------|
| `support_modules/simple_variable_speed.py` | Core EDT / schedule / `.txt` rewrite |
| `prince_modern/simple_variable_speed_dialog.py` | Qt dialog |
| `prince_modern/main_window.py` | System Actions button |
| `prince_modern/controller.py` | Open + Apply reload |
| `tests/test_simple_variable_speed.py` | Unit tests (unittest) |
| `tests/run_all_tests.py` | Suite key `simple_variable_speed` |
| `documentation/SIMPLE_VARIABLE_SPEED.md` | Operator / developer guide |
| `documentation/CHANGELOG.md` | 2026-11-13 entry |
| `documentation/PRINCE_MODERN_GUI.md` | Feature checklist row |
| `documentation/README.md` | Index link |
| `START_HERE_FOR_AI.md` | Handoff table row |
| `README.md` | Tree listing + Nov 2026 blurb |
| `debug/capture_simple_variable_speed_dialog.py` (+ plot scripts) | Diagnostics |
| `documentation/analysis_summaries/simple_variable_speed_*` | Preview / diagnostic figures |

## Broader documentation sweep (done)

| Item | Status |
|------|--------|
| Root `DOCUMENTATION_INDEX.md` SVS link | Done |
| `QUICK_REFERENCE_CARD.md` continuous-print tip | Done |
| `UNDERGRADUATE_TEAM_GUIDE.md` Modern + SVS note | Done |
| `PRINTING_PROCESS_GUIDE.md` Run Cont. rewrite section | Done |
| `MASTER_WORKFLOW_GUIDE.md` Modern System Actions step | Done |
| `README_COMPREHENSIVE.md` vs canonical indexes | Done (canonical pointer + SVS link) |
| Test count bump (**83** pass, 1 skipped) | Done in README / PROJECT_ORGANIZATION / CHANGELOG Nov-13 |
| `PROJECT_ORGANIZATION.md`, `DEBUG_FOLDER_INDEX.md`, `IMAGE_MODIFICATION_MODULE.md`, `PRE_PRINT_SETUP_GUIDE.md`, `START_HERE_FOR_AI.md` | Done |

Historical CHANGELOG lines that say “57 tests” / “71 tests” for older dates were left as-is (accurate for those entries).

## Suggested commit scope (when asked)

**Include**
- All feature code paths above
- Docs updates from this sweep
- Dialog preview PNG
- Unit tests + `run_all_tests.py` registration

**Review before including**
- Large diagnostic PNGs / `simple_variable_speed_dmax_cache.npz` under `documentation/analysis_summaries/` (useful for papers; may bloat the repo)
- `data/monitor_print_state.json` and `SessionLogs/` if present as dirty/untracked — usually **do not** commit

**Never commit**
- `.conda/`, `__pycache__/`, `Printing_Logs/`, secrets

## Suggested commit message (draft)

```
feat: Simple Variable Speed for Prince Modern continuous prints

Add EDT-based β=4 Stefan speed scheduling with dose-coupled PWM,
Qt preview dialog, instruction Time/Intensity rewrite, tests, and docs.
```

## Pre-push verification

```powershell
.\.conda\python.exe tests/run_all_tests.py simple_variable_speed
.\.conda\python.exe -m py_compile prince_modern/simple_variable_speed_dialog.py support_modules/simple_variable_speed.py
git status
git log -3 --oneline
```

Full suite (2026-11-13): **83** passed, **1** skipped.

Remote (from `START_HERE_FOR_AI.md`): `origin` → `https://github.com/ehj3110/Prince.git`.

## Explicit next user asks

- “Commit …” — stage agreed files and create the commit.
- “Push …” — `git push origin main` (or a feature branch + PR if preferred).
