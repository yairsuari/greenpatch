# Instructions for Claude — Green Patch 2026

## How to work with me
1. **Be verbose.** Explain what you are doing, why, and what you found. Include intermediate results, assumptions and caveats rather than only the final answer.
2. **Ask questions when something is not clear.** If a request is ambiguous, a scientific choice is open (thresholds, baselines, domains, algorithms), or data behaves unexpectedly, stop and ask before proceeding. Do not silently pick an interpretation.
3. Work in **English** (code, comments, documents), even when I write in Hebrew.

## Manuscript rules (`reports/ms_draft.docx`)
1. **Everything Claude adds to or changes in the manuscript must be a tracked change** (Word revision marks: `<w:ins>` / `<w:del>`), with author `Claude` and the current date. Never edit the manuscript silently, and never accept or reject existing tracked changes unless asked.
2. **If more than 25 % of a paragraph is edited, track the whole paragraph:** mark the entire old paragraph as deleted and insert the entire new paragraph, instead of word-level edits. Measure the 25 % in words of the original paragraph (added + deleted + replaced words, divided by the original word count).
3. Before editing, keep a backup copy of the previous version in `reports/versions/` named `ms_draft_YYYY-MM-DD_HHMM.docx`.
4. After editing, validate the file (docx skill: `validate.py --original ... --author Claude`) and tell me which sections changed.
5. Uncertain facts, product IDs or citations go in as Word comments, or as `[VERIFY: ...]` inside the tracked insertion. Never invent references.

## Read first
**Start with `guidelines/handoff.md`** (state of the project, decisions, open questions, next steps). Update it at the end of each session.

Before any task, read the files in `guidelines/`:
- `00_project_overview.md` — background, goals, hypotheses
- `01_research_plan.md` — stages, methods, milestones
- `02_data_sources.md` — data sources, access, status
- `03_models.md` — ocean model options (stage 2)
- `04_conventions.md` — naming, units, CRS, domain, periods
- `05_stage1_patch_identification.md` — statistical procedure for identifying the patch in space and time
- `06_local_pilot.md` — local pilot first, then move to a server; portability rules and exit criteria
- `07_q2_operational_model.md` — Q2: what the operational Med biogeochemical system shows and could have shown
- `08_next_study_draft.md` — draft of the continuation study (not part of this paper)
- `09_remote_setup.md` — working from the second laptop via SSH on the remote machine
- `decisions_log.md` — decisions already made; do not reopen them without a reason
- `todo.md` — current tasks

Update `decisions_log.md` and `todo.md` when decisions are made or tasks change.

## Project layout
See `README.md`. Key rules:
- `data/raw/` is never edited. Processing writes to `data/interim/` and `data/processed/`.
  - **Exception (approved by the user 2026-10-15), satellite imagery only:** downloaded satellite files from public archives (Sentinel-2, Landsat, Copernicus Marine) may be **deleted** after a verified slim copy exists (`scripts/02_slim_storage.py --delete-originals`, which logs checksums). They are never modified in place. Reason: they are re-fetchable, not lab data. All other raw data (in-situ, lab, partner data) remain untouchable.
- Reusable code goes in `src/greenpatch/`; pipeline steps are numbered scripts in `scripts/`.
- Figures go to `results/figures/`, tables to `results/tables/`.
- `data/`, `model/runs/` and `.venv/` are not tracked in git.

## Python
- Use the project venv at `.venv/` (created with `--system-site-packages`).
- Before `pip install`, check whether the package is already importable. Install only what is missing, and record it in `env/requirements.txt`.

## Current focus
One paper, three questions (`guidelines/00_project_overview.md`): Q1 observed patch (satellite; current focus), Q2 operational system (`07`; issued forecasts not archived, so an upper-bound test), Q3 forecastability with our own model (`03`, draft, not yet reviewed).
