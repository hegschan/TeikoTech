#!/usr/bin/env python3
"""Part 1: Initialize SQLite schema and load cell-count.csv into cell_counts.db."""

from __future__ import annotations

import csv
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CSV_PATH = ROOT / "cell-count.csv"
DB_PATH = ROOT / "cell_counts.db"

POPULATIONS = ("b_cell", "cd8_t_cell", "cd4_t_cell", "nk_cell", "monocyte")

SCHEMA_SQL = """
PRAGMA foreign_keys = ON;

DROP TABLE IF EXISTS cell_counts;
DROP TABLE IF EXISTS samples;
DROP TABLE IF EXISTS subjects;
DROP TABLE IF EXISTS projects;

CREATE TABLE projects (
    project_id TEXT PRIMARY KEY
);

CREATE TABLE subjects (
    subject_id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL,
    condition  TEXT NOT NULL,
    age        INTEGER NOT NULL,
    sex        TEXT NOT NULL,
    treatment  TEXT NOT NULL,
    response   TEXT,
    FOREIGN KEY (project_id) REFERENCES projects(project_id)
);

CREATE TABLE samples (
    sample_id                   TEXT PRIMARY KEY,
    subject_id                  TEXT NOT NULL,
    sample_type                 TEXT NOT NULL,
    time_from_treatment_start   INTEGER NOT NULL,
    FOREIGN KEY (subject_id) REFERENCES subjects(subject_id)
);

CREATE TABLE cell_counts (
    sample_id  TEXT NOT NULL,
    population TEXT NOT NULL,
    count      INTEGER NOT NULL CHECK (count >= 0),
    PRIMARY KEY (sample_id, population),
    FOREIGN KEY (sample_id) REFERENCES samples(sample_id)
);

CREATE INDEX idx_subjects_project    ON subjects(project_id);
CREATE INDEX idx_subjects_condition  ON subjects(condition);
CREATE INDEX idx_subjects_treatment  ON subjects(treatment);
CREATE INDEX idx_subjects_response   ON subjects(response);
CREATE INDEX idx_samples_subject     ON samples(subject_id);
CREATE INDEX idx_samples_type_time   ON samples(sample_type, time_from_treatment_start);
CREATE INDEX idx_cell_counts_pop     ON cell_counts(population);
"""


def init_db(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA_SQL)
    conn.commit()


def load_csv(conn: sqlite3.Connection, csv_path: Path = CSV_PATH) -> None:
    projects: set[str] = set()
    subjects: dict[str, tuple] = {}
    samples: list[tuple] = []
    counts: list[tuple] = []

    with csv_path.open(newline="") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            project_id = row["project"]
            subject_id = row["subject"]
            sample_id = row["sample"]

            projects.add(project_id)

            # Subject-level attributes are constant per subject in this dataset.
            if subject_id not in subjects:
                response = row["response"].strip() or None
                subjects[subject_id] = (
                    subject_id,
                    project_id,
                    row["condition"],
                    int(row["age"]),
                    row["sex"],
                    row["treatment"],
                    response,
                )

            samples.append(
                (
                    sample_id,
                    subject_id,
                    row["sample_type"],
                    int(row["time_from_treatment_start"]),
                )
            )

            for population in POPULATIONS:
                counts.append((sample_id, population, int(row[population])))

    conn.executemany(
        "INSERT INTO projects (project_id) VALUES (?)",
        [(p,) for p in sorted(projects)],
    )
    conn.executemany(
        """
        INSERT INTO subjects
            (subject_id, project_id, condition, age, sex, treatment, response)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        list(subjects.values()),
    )
    conn.executemany(
        """
        INSERT INTO samples
            (sample_id, subject_id, sample_type, time_from_treatment_start)
        VALUES (?, ?, ?, ?)
        """,
        samples,
    )
    conn.executemany(
        "INSERT INTO cell_counts (sample_id, population, count) VALUES (?, ?, ?)",
        counts,
    )
    conn.commit()

    n_projects = conn.execute("SELECT COUNT(*) FROM projects").fetchone()[0]
    n_subjects = conn.execute("SELECT COUNT(*) FROM subjects").fetchone()[0]
    n_samples = conn.execute("SELECT COUNT(*) FROM samples").fetchone()[0]
    n_counts = conn.execute("SELECT COUNT(*) FROM cell_counts").fetchone()[0]
    print(
        f"Loaded into {DB_PATH.name}: "
        f"{n_projects} projects, {n_subjects} subjects, "
        f"{n_samples} samples, {n_counts} cell-count rows."
    )


def main() -> None:
    if not CSV_PATH.exists():
        raise FileNotFoundError(f"Missing input file: {CSV_PATH}")

    if DB_PATH.exists():
        DB_PATH.unlink()

    conn = sqlite3.connect(DB_PATH)
    try:
        init_db(conn)
        load_csv(conn)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
