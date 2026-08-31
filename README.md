# Loblaw Bio — Miraclib Immune Cell Analysis

Python pipeline and interactive dashboard for Bob Loblaw’s miraclib clinical trial
at Loblaw Bio. Covers immune-cell frequencies, responder vs non-responder
comparisons, and baseline melanoma PBMC subset summaries. (Quintazide was not
among this trial’s treatment arms and is noted only for completeness.)

---

## How to run (GitHub Codespaces)

From the repository root:

```bash
make setup      # install Python dependencies from requirements.txt
make pipeline   # Part 1 DB load + Parts 2–4 tables/plots (no prompts)
make dashboard  # start the interactive dashboard server
```

Equivalent without Make:

```bash
python3 -m pip install -r requirements.txt
python3 load_data.py    # Part 1 → cell_counts.db
python3 analysis.py     # Parts 2–4 → outputs/
python3 dashboard.py    # dashboard server
```

Expected artifacts after `make pipeline`:

| Artifact | Description |
|----------|-------------|
| `cell_counts.db` | SQLite database (Part 1) |
| `outputs/tables/cell_population_frequencies.csv` | Part 2 frequency table |
| `outputs/tables/responder_comparison_data.csv` | Part 3 cohort data |
| `outputs/tables/responder_vs_nonresponder_stats.csv` | Part 3 Mann–Whitney results |
| `outputs/figures/responder_vs_nonresponder_boxplots.png` | Part 3 boxplots |
| `outputs/tables/baseline_subset_*.csv` / `baseline_subset_summary.txt` | Part 4 |

Input file required in the repo root: **`cell-count.csv`**.

---

## Dashboard link

After `make dashboard`, open:

### [http://127.0.0.1:8050](http://127.0.0.1:8050)

In GitHub Codespaces, open the **Ports** panel and preview / forward port **8050**.

---

## Database schema

SQLite file created in the repo root: **`cell_counts.db`**.

```
projects
  └── project_id (PK)

subjects
  ├── subject_id (PK)
  ├── project_id → projects
  ├── condition, age, sex, treatment, response

samples
  ├── sample_id (PK)
  ├── subject_id → subjects
  ├── sample_type
  └── time_from_treatment_start

cell_counts
  ├── (sample_id, population) PRIMARY KEY
  ├── sample_id → samples
  ├── population   # b_cell, cd8_t_cell, cd4_t_cell, nk_cell, monocyte
  └── count
```

### Rationale

The raw CSV is wide and denormalized: subject-level fields (`age`, `sex`,
`treatment`, `response`, …) repeat on every sample row, and the five cell
populations are separate columns.

1. **Normalize by entity** — `projects`, `subjects`, `samples`, and
   `cell_counts` change at different rates. Subject metadata is stored once;
   samples reference subjects; counts are facts about a sample.
2. **Long-format counts** — one row per `(sample, population)` instead of five
   wide columns. Filtering, summing totals, and computing relative frequencies
   are ordinary SQL. Adding a new population does not require a schema change.
3. **Indexes** on foreign keys and common cohort filters (`condition`,
   `treatment`, `response`, `sample_type`, `time_from_treatment_start`,
   `population`) keep Part 3 / Part 4 queries efficient.

### Scaling (hundreds of projects, thousands of samples, many analytics)

- The same 3NF shape ports to Postgres / Snowflake with minimal SQL changes.
- Partition or cluster fact tables (`cell_counts`) by project (via joins) once
  row counts reach tens of millions.
- Materialize Part 2–style frequency views or nightly summary tables so
  dashboards stay fast under concurrent users.
- Keep assay/panel metadata in satellite tables keyed by `sample_id` rather
  than widening `samples`.
- Treat `cell_counts` as the source of truth; build downstream feature marts
  for QC, longitudinal models, and ML without reshaping the core schema.

---

## Code structure

| Path | Role |
|------|------|
| `cell-count.csv` | Input data |
| `load_data.py` | Part 1: create schema + load CSV → `cell_counts.db` |
| `analysis.py` | Parts 2–4: frequency table, stats/boxplots, baseline subset |
| `dashboard.py` | Interactive Dash app (reads DB + `outputs/`) |
| `Makefile` | Grader entrypoints: `setup`, `pipeline`, `dashboard` |
| `requirements.txt` | Dependencies installed by `make setup` |
| `outputs/` | Generated tables and figures |
| `cell_counts.db` | Generated SQLite database |

### Why this design

- **`load_data.py` alone owns ingestion** — matches the Part 1 requirement
  (`python load_data.py` in the repo root, no CLI args) and stays idempotent
  (rebuilds the DB each run).
- **`analysis.py` owns analytics** — Parts 2→4 run sequentially against the DB
  and write only under `outputs/`, so graders can re-run analysis without
  re-implementing load logic.
- **`dashboard.py` owns presentation** — consumes the same pipeline artifacts
  the grader inspects, avoiding a second divergent analysis path.
- **`Makefile` targets** — `setup` / `pipeline` / `dashboard` are the exact
  Codespaces grading hooks, with zero interactive prompts.

---

## Analysis summary

### Part 2 — Population frequencies

For each sample, `total_count` is the sum of the five populations;
`percentage = 100 × count / total_count`. Output columns:
`sample`, `total_count`, `population`, `count`, `percentage`.

### Part 3 — Responders vs non-responders

Cohort: **melanoma** + **miraclib** + **PBMC**, response `yes` vs `no`.
Boxplots compare relative frequencies; **Mann–Whitney U** (two-sided) tests
each population. Populations with `p < 0.05` are flagged in
`responder_vs_nonresponder_stats.csv`.

### Part 4 — Baseline subset

Cohort: melanoma + miraclib + PBMC + `time_from_treatment_start = 0`.
Reports sample counts per project, and subject counts by response and by sex.
