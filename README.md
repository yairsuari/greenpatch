# Green Patch 2026

In August–September 2026 an unusual "green patch" appeared along the Israeli Mediterranean coast: chlorophyll concentrations were anomalously high and sea-surface salinity dropped markedly. The event has potential ecological impacts and, critically, impacts on seawater desalination plants and the Israeli water sector. Nile-origin microalgae intrude every summer; the question is why the 2026 event was so much stronger.

The project is one paper with three questions (see `guidelines/00_project_overview.md`):
1. **Q1 — Observed:** did satellites see the patch, and what was its extent in space and time?
2. **Q2 — Operational system:** did the operational Mediterranean biogeochemical system represent the patch, even in its best estimate, and does it contain the inputs and processes needed to forecast it? (Its issued forecasts are not archived.)
3. **Q3 — Forecastability:** could the patch have been forecast, how far ahead, and what would that have required? Own model reforecasts; includes attribution (Gaza/Nile discharge vs oceanographic conditions).

News coverage:
- ynet: https://www.ynet.co.il/environment-science/article/h18uzn00dzg
- Calcalist: https://www.calcalist.co.il/local_news/article/byrmxi0fgg

## Folder layout
```
guidelines/            shared markdown files (plan, data sources, conventions, decisions, todo)
background_material/   literature, news, reports, reading notes
background_data/       static context data: bathymetry, coastline, infrastructure, climatologies
data/                  raw (never edited) -> interim -> processed   [not in git]
src/greenpatch/        reusable Python code
scripts/               numbered pipeline scripts
notebooks/             exploration
model/                 own model setup: config, grid, forcing, runs [runs not in git], postprocessing
results/               figures, tables, maps
reports/               drafts, presentations, manuscript
env/                   environment specification (requirements.txt)
```

## Python environment
```
python -m venv --system-site-packages .venv
.venv\Scripts\activate
pip install -r env/requirements.txt   # only packages not already available
```
