# Documentation Index

Project documentation is available in two languages. Use the same structure under `en/` and `ru/`.

## English (EN)

- **Overview and runbooks:** [docs/en/root/](en/root/)
  - [README](en/root/README.md) — project overview, quick start, repository structure
  - [NEW_PC_SETUP](en/root/NEW_PC_SETUP.md) — install and run on a new machine
  - [README_RUNNING](en/root/README_RUNNING.md) — run log and decision history
  - [README_SHAMALGAN](en/root/README_SHAMALGAN.md) — Shamalgan runbook and commands
  - [SHAMALGAN_HANDOFF](en/root/SHAMALGAN_HANDOFF.md) — short handoff for new sessions
  - [SHAMALGAN_REAL_PT_INTEGRATION_PLAN](en/root/SHAMALGAN_REAL_PT_INTEGRATION_PLAN.md) — PT integration roadmap
- **Progress (timeline, runs, gaps):** [docs/en/progress/](en/progress/)
- **Domain (placeholders):** [docs/en/domain/](en/domain/)

## Русский (RU)

- **Обзоры и руководства:** [docs/ru/root/](ru/root/)
  - [README](ru/root/README.md) — обзор проекта, быстрый старт, структура репозитория
  - [NEW_PC_SETUP](ru/root/NEW_PC_SETUP.md) — установка на новом ПК
  - [README_RUNNING](ru/root/README_RUNNING.md) — журнал запусков и решений
  - [README_SHAMALGAN](ru/root/README_SHAMALGAN.md) — руководство по запуску Шамалгана
  - [SHAMALGAN_HANDOFF](ru/root/SHAMALGAN_HANDOFF.md) — краткий handoff
  - [SHAMALGAN_REAL_PT_INTEGRATION_PLAN](ru/root/SHAMALGAN_REAL_PT_INTEGRATION_PLAN.md) — план интеграции ОТ
- **Прогресс:** [docs/ru/progress/](ru/progress/)
- **Домен (заглушки):** [docs/ru/domain/](ru/domain/)

## Legacy and redirects

- **docs/root/** — redirects to `docs/en/root/` and `docs/ru/root/`. Old links to `docs/root/*` continue to work.
- **docs/progress/** — main update location for progress logs; mirrored in `docs/en/progress/` for the EN doc branch. `docs/ru/progress/` holds the same files plus a Russian README.

## Archive

- **docs/archive/** — historical session memory and continuity profile. Not part of the main navigation. See [docs/archive/README.md](archive/README.md).

## README Hub

- **docs/readme-hub/** — auto-collected copies of README-style files for quick browsing. Regenerate with:
  - `powershell -ExecutionPolicy Bypass -File tools/collect_readmes.ps1`
- This is a helper index, not the primary documentation structure.

## Output convention

- Active simulation output: `output/`
- Archived outputs: `archive-outputs/`
