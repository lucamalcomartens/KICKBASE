# KICKBASE Workspace Guidelines

## Workflow

- Start every repository task by reading `AGENT_GEDAECHTNIS.md` and `AGENT_LOG.md`.
- End every repository task by updating both files.
- Before writing to `AGENT_GEDAECHTNIS.md` or `AGENT_LOG.md`, ask the user first and only proceed after explicit approval.
- Keep `AGENT_GEDAECHTNIS.md` focused on the current verified state, decisions, constraints, and open questions.
- Keep `AGENT_LOG.md` as a dated history of completed work, validations, and next follow-ups.
- If the markdown files conflict with the codebase or a fresh verification, trust the verified source and repair the markdown files.
- Ask before longer retraining, promotion comparisons, or extended test runs.

## Architecture

- `kickbase_api/kickbase_api/` contains the reusable API client.
- `kickbase_api/Anwendungsfälle/` contains workflows and decision logic above the API layer.
- Prefer one shared decision logic for simulation, evaluation, and live recommendations over separate heuristic side paths.
- Keep the project local-first and lightweight unless a real bottleneck proves otherwise.

## Build And Run

- The practical project entrypoint lives in `kickbase_api/`.
- Typical setup uses the workspace virtual environment at `.venv/`.
- Quick start commands are documented in `kickbase_api/README.md`.

## Editing Conventions

- Preserve the current lightweight Python structure.
- Make targeted changes instead of broad refactors.
- Document newly verified API findings or workflow decisions in `AGENT_GEDAECHTNIS.md`.