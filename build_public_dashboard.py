#!/usr/bin/env python3
"""Build a static interactive dashboard for GitHub Pages (docs/index.html)."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

ROOT = Path(__file__).resolve().parent
TABLE_DIR = ROOT / "outputs" / "tables"
DOCS_DIR = ROOT / "docs"
POPULATIONS = ["b_cell", "cd8_t_cell", "cd4_t_cell", "nk_cell", "monocyte"]


def fig_to_div(fig: go.Figure, include_js: bool = False) -> str:
    return fig.to_html(
        full_html=False,
        include_plotlyjs="cdn" if include_js else False,
        config={"displayModeBar": True, "responsive": True},
    )


def build() -> Path:
    freq = pd.read_csv(TABLE_DIR / "cell_population_frequencies.csv")
    part3 = pd.read_csv(TABLE_DIR / "responder_comparison_data.csv")
    stats = pd.read_csv(TABLE_DIR / "responder_vs_nonresponder_stats.csv")
    by_project = pd.read_csv(TABLE_DIR / "baseline_subset_by_project.csv")
    by_response = pd.read_csv(TABLE_DIR / "baseline_subset_by_response.csv")
    by_sex = pd.read_csv(TABLE_DIR / "baseline_subset_by_sex.csv")
    baseline = pd.read_csv(TABLE_DIR / "baseline_subset_samples.csv")

    # Part 2: mean relative frequency
    mean_pct = (
        freq.groupby("population", as_index=False)["percentage"]
        .mean()
        .sort_values("percentage", ascending=False)
    )
    fig2 = px.bar(
        mean_pct,
        x="population",
        y="percentage",
        color="population",
        title="Mean relative frequency across all samples",
        labels={"percentage": "Mean %", "population": "Population"},
        color_discrete_sequence=px.colors.qualitative.Set2,
    )
    fig2.update_layout(showlegend=False, paper_bgcolor="white", plot_bgcolor="white")

    # Part 3: boxplots
    fig3 = px.box(
        part3,
        x="response",
        y="percentage",
        color="response",
        facet_col="population",
        category_orders={"response": ["yes", "no"], "population": POPULATIONS},
        color_discrete_map={"yes": "#66BB6A", "no": "#EF9A9A"},
        points="outliers",
        title="Melanoma / miraclib / PBMC: responders vs non-responders",
        labels={"percentage": "Relative frequency (%)", "response": "Response"},
    )
    fig3.update_layout(showlegend=False, paper_bgcolor="white", plot_bgcolor="white")
    fig3.for_each_annotation(lambda a: a.update(text=a.text.split("=")[-1]))

    sig = stats.loc[stats["significant_at_0.05"] == True, "population"].tolist()  # noqa: E712
    if sig:
        sig_html = (
            "<p class='callout'><strong>Significant populations "
            "(Mann–Whitney U, p &lt; 0.05):</strong> "
            + ", ".join(sig)
            + "</p>"
        )
    else:
        sig_html = (
            "<p class='callout'>No populations reached p &lt; 0.05 "
            "in this cohort.</p>"
        )

    stats_rows = "".join(
        "<tr>"
        + "".join(f"<td>{stats.iloc[i][c]}</td>" for c in stats.columns)
        + "</tr>"
        for i in range(len(stats))
    )
    stats_head = "".join(f"<th>{c}</th>" for c in stats.columns)

    # Part 4
    fig_proj = px.bar(
        by_project,
        x="project_id",
        y="n_samples",
        text="n_samples",
        title="Baseline samples per project",
        labels={"project_id": "Project", "n_samples": "Samples"},
        color="project_id",
        color_discrete_sequence=px.colors.qualitative.Pastel,
    )
    fig_proj.update_layout(showlegend=False, paper_bgcolor="white", plot_bgcolor="white")

    fig_resp = px.pie(
        by_response,
        names="response",
        values="n_subjects",
        title="Subjects by response",
        color="response",
        color_discrete_map={"yes": "#66BB6A", "no": "#EF9A9A"},
    )
    fig_resp.update_layout(paper_bgcolor="white")

    fig_sex = px.pie(
        by_sex,
        names="sex",
        values="n_subjects",
        title="Subjects by sex",
        color="sex",
        color_discrete_map={"M": "#90CAF9", "F": "#F48FB1"},
    )
    fig_sex.update_layout(paper_bgcolor="white")

    n_base_samples = baseline["sample_id"].nunique()
    n_base_subjects = baseline["subject_id"].nunique()

    # Sample of frequency table (first 25 rows)
    preview = freq.head(25)
    freq_head = "".join(f"<th>{c}</th>" for c in preview.columns)
    freq_rows = "".join(
        "<tr>"
        + "".join(f"<td>{preview.iloc[i][c]}</td>" for c in preview.columns)
        + "</tr>"
        for i in range(len(preview))
    )

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Miraclib Immune Cell Dashboard</title>
  <style>
    :root {{
      --bg: #f7faf7;
      --card: #ffffff;
      --ink: #1b4332;
      --muted: #4a6356;
      --pastel: #c8e6c9;
      --line: #d7e5d8;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: "IBM Plex Sans", Helvetica, Arial, sans-serif;
      background: var(--bg);
      color: var(--ink);
      line-height: 1.5;
    }}
    header {{
      background: var(--pastel);
      padding: 28px 20px;
    }}
    header .wrap, main {{
      max-width: 1100px;
      margin: 0 auto;
    }}
    header p.eyebrow {{
      margin: 0 0 4px 0;
      letter-spacing: 0.22em;
      font-size: 0.75rem;
      font-weight: 600;
      color: #2e7d32;
    }}
    header h1 {{
      margin: 0;
      font-size: 1.8rem;
      color: #1b5e20;
    }}
    nav {{
      display: flex;
      gap: 10px;
      flex-wrap: wrap;
      margin: 18px auto 0;
      max-width: 1100px;
      padding: 0 20px;
    }}
    nav a {{
      text-decoration: none;
      background: white;
      border: 1px solid var(--line);
      color: var(--ink);
      padding: 8px 14px;
      border-radius: 999px;
      font-size: 0.92rem;
    }}
    section {{
      background: var(--card);
      border: 1px solid var(--line);
      border-radius: 10px;
      padding: 22px;
      margin: 18px auto;
      max-width: 1100px;
    }}
    h2 {{ margin-top: 0; }}
    p.lead, p.note {{ color: var(--muted); }}
    .callout {{
      background: #e8f5e9;
      border: 1px solid #a5d6a7;
      border-radius: 8px;
      padding: 12px 14px;
    }}
    .grid3 {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
      gap: 12px;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      font-size: 0.9rem;
      overflow-x: auto;
      display: block;
    }}
    th, td {{
      border-bottom: 1px solid var(--line);
      text-align: left;
      padding: 8px 10px;
      white-space: nowrap;
    }}
    th {{ background: #edf7ee; }}
    footer {{
      text-align: center;
      color: var(--muted);
      font-size: 0.85rem;
      padding: 24px;
    }}
  </style>
</head>
<body>
  <header>
    <div class="wrap">
      <p class="eyebrow">LOBLAW BIO</p>
      <h1>Miraclib Immune Cell Dashboard</h1>
    </div>
  </header>

  <nav>
    <a href="#part2">Part 2 Frequencies</a>
    <a href="#part3">Part 3 Responders</a>
    <a href="#part4">Part 4 Baseline</a>
  </nav>

  <section id="part2">
    <h2>Part 2 · Population frequencies</h2>
    <p class="lead">
      Relative frequency of each immune cell population per sample
      (percentage = count / total_count × 100).
      Full table: {len(freq):,} rows in
      <code>outputs/tables/cell_population_frequencies.csv</code>.
    </p>
    {fig_to_div(fig2, include_js=True)}
    <h3>Preview (first 25 rows)</h3>
    <table>
      <thead><tr>{freq_head}</tr></thead>
      <tbody>{freq_rows}</tbody>
    </table>
  </section>

  <section id="part3">
    <h2>Part 3 · Responders vs non-responders</h2>
    <p class="lead">
      Melanoma patients treated with miraclib, PBMC samples only.
      Interactive boxplots compare relative frequencies by response.
    </p>
    {fig_to_div(fig3)}
    {sig_html}
    <h3>Statistical summary</h3>
    <table>
      <thead><tr>{stats_head}</tr></thead>
      <tbody>{stats_rows}</tbody>
    </table>
  </section>

  <section id="part4">
    <h2>Part 4 · Baseline melanoma PBMC subset</h2>
    <p class="lead">
      condition=melanoma, sample_type=PBMC, treatment=miraclib,
      time_from_treatment_start=0.
      Total: {n_base_samples} samples · {n_base_subjects} subjects.
    </p>
    <div class="grid3">
      <div>{fig_to_div(fig_proj)}</div>
      <div>{fig_to_div(fig_resp)}</div>
      <div>{fig_to_div(fig_sex)}</div>
    </div>
  </section>

  <footer>
    Built from pipeline outputs · Loblaw Bio miraclib trial analysis
  </footer>
</body>
</html>
"""

    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    out = DOCS_DIR / "index.html"
    out.write_text(html)
    print(f"Wrote public dashboard → {out.relative_to(ROOT)}")
    return out


if __name__ == "__main__":
    if not (TABLE_DIR / "cell_population_frequencies.csv").exists():
        raise SystemExit("Missing outputs/. Run `make pipeline` first.")
    build()
