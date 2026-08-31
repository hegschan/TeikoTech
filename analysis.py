#!/usr/bin/env python3
"""Parts 2–4: frequency table, responder vs non-responder stats, baseline subset."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import matplotlib

# Headless-safe for GitHub Codespaces / CI (no display server).
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd
import seaborn as sns
from scipy import stats

ROOT = Path(__file__).resolve().parent
DB_PATH = ROOT / "cell_counts.db"
OUT_DIR = ROOT / "outputs"
TABLE_DIR = OUT_DIR / "tables"
FIG_DIR = OUT_DIR / "figures"

POPULATIONS = ("b_cell", "cd8_t_cell", "cd4_t_cell", "nk_cell", "monocyte")


def connect() -> sqlite3.Connection:
    if not DB_PATH.exists():
        raise FileNotFoundError(
            f"{DB_PATH} not found. Run `python load_data.py` first."
        )
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def ensure_dirs() -> None:
    TABLE_DIR.mkdir(parents=True, exist_ok=True)
    FIG_DIR.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# Part 2 — relative frequency of each population per sample
# ---------------------------------------------------------------------------

FREQUENCY_SQL = """
WITH totals AS (
    SELECT sample_id, SUM(count) AS total_count
    FROM cell_counts
    GROUP BY sample_id
)
SELECT
    cc.sample_id AS sample,
    t.total_count,
    cc.population,
    cc.count,
    ROUND(100.0 * cc.count / t.total_count, 4) AS percentage
FROM cell_counts AS cc
JOIN totals AS t USING (sample_id)
ORDER BY cc.sample_id, cc.population
"""


def run_part2(conn: sqlite3.Connection) -> pd.DataFrame:
    df = pd.read_sql_query(FREQUENCY_SQL, conn)
    out = TABLE_DIR / "cell_population_frequencies.csv"
    df.to_csv(out, index=False)
    print(f"[Part 2] Wrote {len(df):,} rows → {out.relative_to(ROOT)}")
    return df


# ---------------------------------------------------------------------------
# Part 3 — melanoma / miraclib / PBMC responders vs non-responders
# ---------------------------------------------------------------------------

PART3_SQL = """
WITH totals AS (
    SELECT sample_id, SUM(count) AS total_count
    FROM cell_counts
    GROUP BY sample_id
)
SELECT
    s.sample_id,
    sub.subject_id,
    sub.response,
    cc.population,
    ROUND(100.0 * cc.count / t.total_count, 4) AS percentage
FROM samples AS s
JOIN subjects AS sub ON sub.subject_id = s.subject_id
JOIN cell_counts AS cc ON cc.sample_id = s.sample_id
JOIN totals AS t ON t.sample_id = s.sample_id
WHERE sub.condition = 'melanoma'
  AND sub.treatment = 'miraclib'
  AND s.sample_type = 'PBMC'
  AND sub.response IN ('yes', 'no')
"""


def run_part3(conn: sqlite3.Connection) -> tuple[pd.DataFrame, pd.DataFrame]:
    df = pd.read_sql_query(PART3_SQL, conn)
    df.to_csv(TABLE_DIR / "responder_comparison_data.csv", index=False)

    # Boxplots — one panel per population
    sns.set_theme(style="whitegrid", context="talk")
    fig, axes = plt.subplots(1, 5, figsize=(18, 5), sharey=True)
    order = ["yes", "no"]
    palette = {"yes": "#2A9D8F", "no": "#E76F51"}

    for ax, population in zip(axes, POPULATIONS):
        subset = df[df["population"] == population]
        sns.boxplot(
            data=subset,
            x="response",
            y="percentage",
            order=order,
            hue="response",
            palette=palette,
            legend=False,
            ax=ax,
            showfliers=False,
        )
        sns.stripplot(
            data=subset,
            x="response",
            y="percentage",
            order=order,
            color="0.25",
            size=2.5,
            alpha=0.35,
            ax=ax,
        )
        ax.set_title(population.replace("_", " "))
        ax.set_xlabel("Response")
        ax.set_ylabel("Relative frequency (%)" if population == POPULATIONS[0] else "")

    fig.suptitle(
        "Melanoma · miraclib · PBMC — population frequencies by response",
        fontsize=14,
        y=1.02,
    )
    fig.tight_layout()
    boxplot_path = FIG_DIR / "responder_vs_nonresponder_boxplots.png"
    fig.savefig(boxplot_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"[Part 3] Wrote boxplots → {boxplot_path.relative_to(ROOT)}")

    # Mann–Whitney U (two-sided) + effect size (rank-biserial / Cliff's delta approx)
    rows = []
    for population in POPULATIONS:
        subset = df[df["population"] == population]
        yes = subset.loc[subset["response"] == "yes", "percentage"]
        no = subset.loc[subset["response"] == "no", "percentage"]
        if len(yes) < 2 or len(no) < 2:
            rows.append(
                {
                    "population": population,
                    "n_responders": len(yes),
                    "n_non_responders": len(no),
                    "median_responders": yes.median() if len(yes) else None,
                    "median_non_responders": no.median() if len(no) else None,
                    "mean_responders": yes.mean() if len(yes) else None,
                    "mean_non_responders": no.mean() if len(no) else None,
                    "u_statistic": None,
                    "p_value": None,
                    "significant_at_0.05": False,
                    "note": "insufficient sample size",
                }
            )
            continue

        u_stat, p_value = stats.mannwhitneyu(yes, no, alternative="two-sided")
        rows.append(
            {
                "population": population,
                "n_responders": int(len(yes)),
                "n_non_responders": int(len(no)),
                "median_responders": round(float(yes.median()), 4),
                "median_non_responders": round(float(no.median()), 4),
                "mean_responders": round(float(yes.mean()), 4),
                "mean_non_responders": round(float(no.mean()), 4),
                "u_statistic": float(u_stat),
                "p_value": float(p_value),
                "significant_at_0.05": bool(p_value < 0.05),
                "note": "",
            }
        )

    stats_df = pd.DataFrame(rows)
    stats_path = TABLE_DIR / "responder_vs_nonresponder_stats.csv"
    stats_df.to_csv(stats_path, index=False)
    print(f"[Part 3] Wrote stats → {stats_path.relative_to(ROOT)}")

    sig = stats_df.loc[stats_df["significant_at_0.05"], "population"].tolist()
    if sig:
        print(f"[Part 3] Significant (p < 0.05): {', '.join(sig)}")
    else:
        print("[Part 3] No populations reached p < 0.05.")

    return df, stats_df


# ---------------------------------------------------------------------------
# Part 4 — baseline melanoma PBMC miraclib subset summaries
# ---------------------------------------------------------------------------

BASELINE_SQL = """
SELECT
    s.sample_id,
    sub.subject_id,
    sub.project_id,
    sub.response,
    sub.sex
FROM samples AS s
JOIN subjects AS sub ON sub.subject_id = s.subject_id
WHERE sub.condition = 'melanoma'
  AND sub.treatment = 'miraclib'
  AND s.sample_type = 'PBMC'
  AND s.time_from_treatment_start = 0
"""


def run_part4(conn: sqlite3.Connection) -> dict[str, pd.DataFrame]:
    baseline = pd.read_sql_query(BASELINE_SQL, conn)
    baseline.to_csv(TABLE_DIR / "baseline_subset_samples.csv", index=False)

    by_project = (
        baseline.groupby("project_id", as_index=False)
        .agg(n_samples=("sample_id", "nunique"), n_subjects=("subject_id", "nunique"))
        .sort_values("project_id")
    )
    by_project.to_csv(TABLE_DIR / "baseline_subset_by_project.csv", index=False)

    # Subject-level response / sex (one row per subject)
    subjects = baseline.drop_duplicates(subset=["subject_id"])

    by_response = (
        subjects.groupby("response", dropna=False, as_index=False)
        .agg(n_subjects=("subject_id", "nunique"))
        .sort_values("response")
    )
    by_response.to_csv(TABLE_DIR / "baseline_subset_by_response.csv", index=False)

    by_sex = (
        subjects.groupby("sex", as_index=False)
        .agg(n_subjects=("subject_id", "nunique"))
        .sort_values("sex")
    )
    by_sex.to_csv(TABLE_DIR / "baseline_subset_by_sex.csv", index=False)

    summary_lines = [
        "Part 4 — Melanoma PBMC baseline (t=0) miraclib subset",
        f"Total samples:  {baseline['sample_id'].nunique()}",
        f"Total subjects: {baseline['subject_id'].nunique()}",
        "",
        "Samples / subjects per project:",
        by_project.to_string(index=False),
        "",
        "Subjects by response:",
        by_response.to_string(index=False),
        "",
        "Subjects by sex:",
        by_sex.to_string(index=False),
        "",
        "Note: exploratory analyses involving quintazide were out of scope for this trial.",
    ]
    summary_path = TABLE_DIR / "baseline_subset_summary.txt"
    summary_path.write_text("\n".join(summary_lines) + "\n")
    print(f"[Part 4] Wrote summary → {summary_path.relative_to(ROOT)}")
    print("\n".join(summary_lines))

    return {
        "baseline": baseline,
        "by_project": by_project,
        "by_response": by_response,
        "by_sex": by_sex,
    }


def main() -> None:
    ensure_dirs()
    conn = connect()
    try:
        run_part2(conn)
        run_part3(conn)
        run_part4(conn)
    finally:
        conn.close()
    print("Analysis complete.")


if __name__ == "__main__":
    main()
