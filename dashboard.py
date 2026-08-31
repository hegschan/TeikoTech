#!/usr/bin/env python3
"""Interactive Dash dashboard for Loblaw Bio miraclib trial analyses."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import dash_bootstrap_components as dbc
import pandas as pd
import plotly.express as px
from dash import Dash, Input, Output, dash_table, dcc, html

ROOT = Path(__file__).resolve().parent
DB_PATH = ROOT / "cell_counts.db"
TABLE_DIR = ROOT / "outputs" / "tables"
FIG_DIR = ROOT / "outputs" / "figures"

POPULATIONS = ["b_cell", "cd8_t_cell", "cd4_t_cell", "nk_cell", "monocyte"]


def read_table(name: str) -> pd.DataFrame:
    path = TABLE_DIR / name
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path)


def query_db(sql: str, params: tuple = ()) -> pd.DataFrame:
    if not DB_PATH.exists():
        return pd.DataFrame()
    with sqlite3.connect(DB_PATH) as conn:
        return pd.read_sql_query(sql, conn, params=params)


def load_assets() -> dict:
    freq = read_table("cell_population_frequencies.csv")
    stats = read_table("responder_vs_nonresponder_stats.csv")
    part3 = read_table("responder_comparison_data.csv")
    by_project = read_table("baseline_subset_by_project.csv")
    by_response = read_table("baseline_subset_by_response.csv")
    by_sex = read_table("baseline_subset_by_sex.csv")
    baseline = read_table("baseline_subset_samples.csv")

    n_samples = query_db("SELECT COUNT(*) AS n FROM samples")
    n_subjects = query_db("SELECT COUNT(*) AS n FROM subjects")

    return {
        "freq": freq,
        "stats": stats,
        "part3": part3,
        "by_project": by_project,
        "by_response": by_response,
        "by_sex": by_sex,
        "baseline": baseline,
        "n_samples": int(n_samples["n"].iloc[0]) if len(n_samples) else 0,
        "n_subjects": int(n_subjects["n"].iloc[0]) if len(n_subjects) else 0,
    }


def style_table(df: pd.DataFrame, page_size: int = 12) -> dash_table.DataTable:
    return dash_table.DataTable(
        data=df.to_dict("records"),
        columns=[{"name": c, "id": c} for c in df.columns],
        page_size=page_size,
        sort_action="native",
        filter_action="native",
        style_table={"overflowX": "auto"},
        style_header={
            "backgroundColor": "#1B4332",
            "color": "white",
            "fontWeight": "600",
        },
        style_cell={
            "fontFamily": "IBM Plex Sans, Helvetica, sans-serif",
            "fontSize": 13,
            "padding": "8px 10px",
            "border": "1px solid #E9ECEF",
        },
        style_data_conditional=[
            {
                "if": {"row_index": "odd"},
                "backgroundColor": "#F8F9FA",
            }
        ],
    )


def empty_notice(msg: str) -> html.Div:
    return html.Div(
        msg,
        style={
            "padding": "24px",
            "background": "#FFF3CD",
            "borderRadius": "8px",
            "color": "#664D03",
        },
    )


app = Dash(
    __name__,
    external_stylesheets=[dbc.themes.FLATLY],
    title="Loblaw Bio · Miraclib Trial",
)
server = app.server

app.layout = dbc.Container(
    [
        html.Div(
            [
                html.P(
                    "LOBLAW BIO",
                    style={
                        "letterSpacing": "0.28em",
                        "fontSize": "0.75rem",
                        "marginBottom": "4px",
                        "color": "#95D5B2",
                        "fontWeight": "600",
                    },
                ),
                html.H1(
                    "Miraclib Immune Cell Dashboard",
                    style={"margin": "0 0 6px 0", "fontWeight": "700"},
                ),
                html.P(
                    "Explore population frequencies, responder differences, "
                    "and baseline melanoma PBMC subsets from the miraclib trial.",
                    style={"margin": 0, "opacity": 0.85, "maxWidth": "720px"},
                ),
            ],
            style={
                "background": "linear-gradient(135deg, #081C15 0%, #1B4332 55%, #2D6A4F 100%)",
                "color": "white",
                "padding": "36px 28px",
                "borderRadius": "12px",
                "marginTop": "18px",
                "marginBottom": "22px",
            },
        ),
        dbc.Row(
            [
                dbc.Col(
                    dbc.Card(
                        dbc.CardBody(
                            [
                                html.H4(id="kpi-samples", className="card-title"),
                                html.P("Samples loaded", className="card-text text-muted"),
                            ]
                        )
                    ),
                    md=4,
                ),
                dbc.Col(
                    dbc.Card(
                        dbc.CardBody(
                            [
                                html.H4(id="kpi-subjects", className="card-title"),
                                html.P("Subjects", className="card-text text-muted"),
                            ]
                        )
                    ),
                    md=4,
                ),
                dbc.Col(
                    dbc.Card(
                        dbc.CardBody(
                            [
                                html.H4(id="kpi-baseline", className="card-title"),
                                html.P(
                                    "Baseline melanoma PBMC samples",
                                    className="card-text text-muted",
                                ),
                            ]
                        )
                    ),
                    md=4,
                ),
            ],
            className="mb-4 g-3",
        ),
        dcc.Tabs(
            id="tabs",
            value="part2",
            children=[
                dcc.Tab(label="Part 2 · Frequencies", value="part2"),
                dcc.Tab(label="Part 3 · Responders", value="part3"),
                dcc.Tab(label="Part 4 · Baseline subset", value="part4"),
            ],
            colors={"border": "#DEE2E6", "primary": "#1B4332", "background": "#F8F9FA"},
        ),
        html.Div(id="tab-content", style={"paddingTop": "20px", "paddingBottom": "40px"}),
        dcc.Interval(id="refresh", interval=60_000, n_intervals=0),
        html.Footer(
            "Built for Bob Loblaw · Loblaw Bio clinical analytics",
            style={
                "textAlign": "center",
                "color": "#6C757D",
                "fontSize": "0.85rem",
                "paddingBottom": "24px",
            },
        ),
    ],
    fluid=True,
    style={"maxWidth": "1200px"},
)


@app.callback(
    Output("kpi-samples", "children"),
    Output("kpi-subjects", "children"),
    Output("kpi-baseline", "children"),
    Output("tab-content", "children"),
    Input("tabs", "value"),
    Input("refresh", "n_intervals"),
)
def render(tab: str, _n: int):
    data = load_assets()
    kpi_s = f"{data['n_samples']:,}"
    kpi_u = f"{data['n_subjects']:,}"
    kpi_b = (
        f"{data['baseline']['sample_id'].nunique():,}"
        if len(data["baseline"])
        else "—"
    )

    if tab == "part2":
        freq = data["freq"]
        if freq.empty:
            return kpi_s, kpi_u, kpi_b, empty_notice(
                "No frequency table found. Run `make pipeline` first."
            )

        mean_pct = (
            freq.groupby("population", as_index=False)["percentage"]
            .mean()
            .sort_values("percentage", ascending=False)
        )
        fig = px.bar(
            mean_pct,
            x="population",
            y="percentage",
            title="Mean relative frequency across all samples",
            labels={"percentage": "Mean %", "population": "Population"},
            color="population",
            color_discrete_sequence=px.colors.qualitative.Set2,
        )
        fig.update_layout(showlegend=False, margin=dict(t=50, b=20))

        content = html.Div(
            [
                html.H4("Relative frequency of each cell population per sample"),
                html.P(
                    "Each row is one population from one sample. "
                    "percentage = count / total_count × 100. "
                    f"Showing all {len(freq):,} rows (sortable / filterable)."
                ),
                dcc.Graph(figure=fig),
                style_table(freq, page_size=15),
            ]
        )
        return kpi_s, kpi_u, kpi_b, content

    if tab == "part3":
        part3 = data["part3"]
        stats_df = data["stats"]
        if part3.empty or stats_df.empty:
            return kpi_s, kpi_u, kpi_b, empty_notice(
                "No Part 3 outputs found. Run `make pipeline` first."
            )

        fig = px.box(
            part3,
            x="response",
            y="percentage",
            color="response",
            facet_col="population",
            category_orders={"response": ["yes", "no"], "population": POPULATIONS},
            color_discrete_map={"yes": "#2A9D8F", "no": "#E76F51"},
            points="all",
            title="Melanoma · miraclib · PBMC — responders vs non-responders",
            labels={"percentage": "Relative frequency (%)", "response": "Response"},
        )
        fig.update_layout(showlegend=False, margin=dict(t=60))
        fig.for_each_annotation(lambda a: a.update(text=a.text.split("=")[-1]))

        sig = stats_df[stats_df["significant_at_0.05"] == True]  # noqa: E712
        if len(sig):
            conclusion = html.Div(
                [
                    html.Strong("Significant populations (Mann–Whitney U, p < 0.05): "),
                    html.Span(", ".join(sig["population"].tolist())),
                ],
                className="alert alert-success",
            )
        else:
            conclusion = html.Div(
                "No cell population showed a statistically significant difference "
                "(Mann–Whitney U, two-sided, α = 0.05) between responders and "
                "non-responders in this melanoma / miraclib / PBMC cohort.",
                className="alert alert-secondary",
            )

        box_img = None
        static_plot = FIG_DIR / "responder_vs_nonresponder_boxplots.png"
        if static_plot.exists():
            # Prefer interactive Plotly; still note the pipeline PNG exists.
            box_img = html.P(
                f"Static pipeline figure also saved at {static_plot.relative_to(ROOT)}.",
                className="text-muted",
            )

        content = html.Div(
            [
                html.H4("Responder vs non-responder comparison"),
                html.P(
                    "Restricted to melanoma patients treated with miraclib, PBMC samples only. "
                    "Relative frequencies come from the Part 2 summary table."
                ),
                dcc.Graph(figure=fig),
                box_img,
                conclusion,
                html.H5("Statistical summary"),
                style_table(stats_df, page_size=10),
            ]
        )
        return kpi_s, kpi_u, kpi_b, content

    # Part 4
    by_project = data["by_project"]
    by_response = data["by_response"]
    by_sex = data["by_sex"]
    baseline = data["baseline"]
    if by_project.empty:
        return kpi_s, kpi_u, kpi_b, empty_notice(
            "No Part 4 outputs found. Run `make pipeline` first."
        )

    fig_proj = px.bar(
        by_project,
        x="project_id",
        y="n_samples",
        text="n_samples",
        title="Baseline samples per project",
        labels={"project_id": "Project", "n_samples": "Samples"},
        color="project_id",
        color_discrete_sequence=px.colors.qualitative.Dark2,
    )
    fig_proj.update_layout(showlegend=False)

    fig_resp = px.pie(
        by_response,
        names="response",
        values="n_subjects",
        title="Subjects by response",
        color="response",
        color_discrete_map={"yes": "#2A9D8F", "no": "#E76F51"},
    )
    fig_sex = px.pie(
        by_sex,
        names="sex",
        values="n_subjects",
        title="Subjects by sex",
        color="sex",
        color_discrete_map={"M": "#457B9D", "F": "#F4A261"},
    )

    content = html.Div(
        [
            html.H4("Baseline melanoma PBMC · miraclib subset"),
            html.P(
                "Samples with condition=melanoma, sample_type=PBMC, "
                "treatment=miraclib, and time_from_treatment_start=0."
            ),
            html.P(
                f"Total: {baseline['sample_id'].nunique()} samples · "
                f"{baseline['subject_id'].nunique()} subjects"
            ),
            dbc.Row(
                [
                    dbc.Col(dcc.Graph(figure=fig_proj), md=4),
                    dbc.Col(dcc.Graph(figure=fig_resp), md=4),
                    dbc.Col(dcc.Graph(figure=fig_sex), md=4),
                ]
            ),
            html.H5("Samples / subjects per project"),
            style_table(by_project, page_size=10),
            html.H5("Subjects by response", className="mt-3"),
            style_table(by_response, page_size=10),
            html.H5("Subjects by sex", className="mt-3"),
            style_table(by_sex, page_size=10),
        ]
    )
    return kpi_s, kpi_u, kpi_b, content


def main() -> None:
    # 8050 is a common Codespaces-friendly default
    app.run(host="0.0.0.0", port=8050, debug=False)


if __name__ == "__main__":
    main()
