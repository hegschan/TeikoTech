# Analyzing immune cell counts from the miraclib trial

## Running the project (GitHub Codespaces)

```bash
make setup
make pipeline
make dashboard
```

* `make setup` installs dependencies from `requirements.txt`
* `make pipeline` creates `cell_counts.db`, then writes all Part 2 to 4 tables and plots under `outputs/`
* `make dashboard` starts the app on port 8050

You can also run the steps directly:

```bash
python3 -m pip install -r requirements.txt
python3 load_data.py
python3 analysis.py
python3 dashboard.py
```

`cell-count.csv` must be in the repo root. After `make pipeline`, you should see `cell_counts.db` plus files in `outputs/tables/` and `outputs/figures/`.

## Dashboard

https://hegschan.github.io/TeikoTech/

## Database schema

The SQLite database is `cell_counts.db`, built by `load_data.py`.

* `projects`: `project_id`
* `subjects`: subject metadata (project, condition, age, sex, treatment, response)
* `samples`: one row per sample (subject, sample type, time from treatment start)
* `cell_counts`: one row per sample and population (`b_cell`, `cd8_t_cell`, `cd4_t_cell`, `nk_cell`, `monocyte`) with the raw count

Why this shape: the CSV repeats subject level fields on every sample row and stores the five populations as columns. Splitting into projects, subjects, and samples keeps metadata in one place. Putting counts in long format makes it easy to filter by population, compute totals, and calculate relative frequencies in SQL. Indexes cover the joins and filters used in Parts 3 and 4 (`condition`, `treatment`, `response`, `sample_type`, `time_from_treatment_start`, `population`).

Scaling: the same layout works if you move to Postgres later. With hundreds of projects and many more samples, you would keep this core model and add things around it, like partitioning or clustering the count table by project, materialized frequency views for dashboards, and separate tables for assay or panel metadata keyed by `sample_id`. New analytics (QC, longitudinal models, ML features) can sit on top without widening the base tables.

## Code structure

* `load_data.py`: Part 1. Create the schema and load `cell-count.csv`
* `analysis.py`: Parts 2 to 4. Frequency table, responder stats and boxplots, baseline subset
* `dashboard.py`: interactive Dash UI over the DB and `outputs/` (local via `make dashboard`)
* `build_public_dashboard.py`: builds the public GitHub Pages site under `docs/`
* `Makefile`: `setup`, `pipeline`, and `dashboard` for Codespaces grading
* `requirements.txt`: Python dependencies
* `outputs/`: generated tables and figures
* `docs/`: public dashboard HTML served by GitHub Pages

I kept load, analysis, and the dashboard in separate scripts on purpose. Part 1 has to be a root level `load_data.py` with no CLI args, so ingestion stays isolated and idempotent (it rebuilds the DB each run). Analysis then only talks to the database and writes under `outputs/`, which makes `make pipeline` a simple two step sequence. The dashboard reads those same artifacts instead of reimplementing the stats, so what you see in the UI matches what the pipeline produced.
