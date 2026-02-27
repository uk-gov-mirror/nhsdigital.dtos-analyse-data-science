from __future__ import annotations

from argparse import ArgumentParser
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.patches import Ellipse

from kpis import (
    kpi_cancer_detection_rate_per_1000,
    kpi_discrepant_cancer_rate,
    kpi_number_cancers_detected,
    kpi_number_discrepant_cancers,
    kpi_number_of_images_read,
    kpi_number_recalled_for_assessment,
    kpi_percentage_recalled_for_assessment,
    kpi_ppv_of_recall_for_assessment,
    preprocess_kpi_data,
)


def load_tables(data_dir: str = "large_data") -> dict[str, pd.DataFrame]:
    data_path = Path(data_dir)
    return {p.stem: pd.read_csv(p) for p in sorted(data_path.glob("*.csv"))}


def build_summary_table(
    tables: dict[str, pd.DataFrame],
) -> pd.DataFrame:
    preprocessed = preprocess_kpi_data(tables)

    reader_decision_counts = kpi_number_of_images_read(tables, preprocessed)
    recalled_for_assessment_per_reader = kpi_number_recalled_for_assessment(
        tables, preprocessed
    )
    percentage_recalled_for_assessment_per_reader = (
        kpi_percentage_recalled_for_assessment(
            tables,
            preprocessed,
            reader_decision_counts=reader_decision_counts,
            recalled_for_assessment_per_reader=recalled_for_assessment_per_reader,
        )
    )
    number_cancers_detected_per_reader = kpi_number_cancers_detected(
        tables, preprocessed
    )
    cancer_detection_rate_per_1000_per_reader = kpi_cancer_detection_rate_per_1000(
        tables,
        number_cancers_detected_per_reader,
        preprocessed,
        reader_decision_counts=reader_decision_counts,
    )
    ppv_of_recall_for_assessment_per_reader = kpi_ppv_of_recall_for_assessment(
        tables,
        preprocessed,
        recalled_for_assessment_per_reader=recalled_for_assessment_per_reader,
    )
    number_discrepant_cancers_per_reader = kpi_number_discrepant_cancers(tables)
    discrepant_cancer_rate_per_reader = kpi_discrepant_cancer_rate(
        number_cancers_detected_per_reader,
        number_discrepant_cancers_per_reader,
    )

    summary_table = (
        tables["Reader"][["reader_id", "bso_code"]]
        .rename(columns={"reader_id": "Unique Code", "bso_code": "BSO Code"})
        .merge(
            reader_decision_counts[["reader_id", "read_decision_count"]].rename(
                columns={
                    "reader_id": "Unique Code",
                    "read_decision_count": "Total Cases Reported as First & Second Reader",
                }
            ),
            on="Unique Code",
            how="left",
        )
        .merge(
            recalled_for_assessment_per_reader[
                ["reader_id", "recalled_for_assessment_count"]
            ].rename(
                columns={
                    "reader_id": "Unique Code",
                    "recalled_for_assessment_count": "Total Recalled to assessment",
                }
            ),
            on="Unique Code",
            how="left",
        )
        .merge(
            percentage_recalled_for_assessment_per_reader[
                ["reader_id", "recalled_for_assessment_pct"]
            ].rename(
                columns={
                    "reader_id": "Unique Code",
                    "recalled_for_assessment_pct": "Recall Rate",
                }
            ),
            on="Unique Code",
            how="left",
        )
        .merge(
            number_cancers_detected_per_reader[
                ["reader_id", "cancers_detected_count"]
            ].rename(
                columns={
                    "reader_id": "Unique Code",
                    "cancers_detected_count": "Total Cancers Detected",
                }
            ),
            on="Unique Code",
            how="left",
        )
        .merge(
            cancer_detection_rate_per_1000_per_reader[
                ["reader_id", "cancer_detection_rate_per_1000"]
            ].rename(
                columns={
                    "reader_id": "Unique Code",
                    "cancer_detection_rate_per_1000": "Cancer Detection Rate",
                }
            ),
            on="Unique Code",
            how="left",
        )
        .merge(
            ppv_of_recall_for_assessment_per_reader[
                ["reader_id", "ppv_recall_for_assessment_pct"]
            ].rename(
                columns={
                    "reader_id": "Unique Code",
                    "ppv_recall_for_assessment_pct": "PPV",
                }
            ),
            on="Unique Code",
            how="left",
        )
        .merge(
            number_discrepant_cancers_per_reader[
                ["reader_id", "discrepant_cancers_count"]
            ].rename(
                columns={
                    "reader_id": "Unique Code",
                    "discrepant_cancers_count": "Total Discrepant Cancers",
                }
            ),
            on="Unique Code",
            how="left",
        )
        .merge(
            discrepant_cancer_rate_per_reader[
                ["reader_id", "discrepant_cancer_rate_pct"]
            ].rename(
                columns={
                    "reader_id": "Unique Code",
                    "discrepant_cancer_rate_pct": "Discrepant Cancer Rate",
                }
            ),
            on="Unique Code",
            how="left",
        )
        .fillna(0)
        .sort_values("Unique Code")
        .reset_index(drop=True)
    )

    return summary_table


def filter_by_bso(dataframe: pd.DataFrame, bso_codes: list[str] | None) -> pd.DataFrame:
    if not bso_codes:
        return dataframe.copy()
    return dataframe[dataframe["BSO Code"].isin(bso_codes)].copy()


def plot_elliptical_chart(summary_table: pd.DataFrame) -> plt.Figure:
    plot_df = summary_table[
        ["Unique Code", "Recall Rate", "Discrepant Cancer Rate"]
    ].copy()
    plot_df["Recall Rate"] = pd.to_numeric(plot_df["Recall Rate"], errors="coerce")
    plot_df["Discrepant Cancer Rate"] = pd.to_numeric(
        plot_df["Discrepant Cancer Rate"], errors="coerce"
    )
    plot_df = plot_df.dropna(subset=["Recall Rate", "Discrepant Cancer Rate"])

    if plot_df.empty:
        print("No data available for plotting.")
    else:
        fig, ax = plt.subplots(figsize=(9, 6))

        ax.scatter(
            plot_df["Recall Rate"],
            plot_df["Discrepant Cancer Rate"],
            alpha=0.9,
            s=70,
            color="#1f77b4",
        )

        for _, row in plot_df.iterrows():
            ax.annotate(
                row["Unique Code"],
                (row["Recall Rate"], row["Discrepant Cancer Rate"]),
                textcoords="offset points",
                xytext=(4, 4),
                fontsize=8,
                alpha=0.8,
            )

        x_mean = plot_df["Recall Rate"].mean()
        y_mean = plot_df["Discrepant Cancer Rate"].mean()
        x_std = plot_df["Recall Rate"].std(ddof=0)
        y_std = plot_df["Discrepant Cancer Rate"].std(ddof=0)

        ax.scatter(
            [x_mean],
            [y_mean],
            color="black",
            marker="x",
            s=90,
            label="Mean",
        )

        # Axis-aligned standard deviation ellipses centered on the mean
        for sigma, color in [(1, "#2ca02c"), (2, "#ff7f0e"), (3, "#d62728")]:
            width = 2 * sigma * x_std
            height = 2 * sigma * y_std
            if width > 0 and height > 0:
                ellipse = Ellipse(
                    (x_mean, y_mean),
                    width=width,
                    height=height,
                    angle=0,
                    fill=False,
                    edgecolor=color,
                    linewidth=2,
                    alpha=0.9,
                    label=f"{sigma}σ ellipse",
                )
                ax.add_patch(ellipse)

        ax.set_title("Discrepant Cancer Rate vs Recall Rate")
        ax.set_xlabel("Recall Rate (%)")
        ax.set_ylabel("Discrepant Cancer Rate (%)")
        ax.grid(True, alpha=0.25)
        ax.legend(loc="best")
        plt.tight_layout()

        return fig


def plot_quadrant_chart(summary_table: pd.DataFrame) -> plt.Figure:
    quadrant_df = summary_table[
        ["Unique Code", "Recall Rate", "Cancer Detection Rate"]
    ].copy()
    quadrant_df["Recall Rate"] = pd.to_numeric(
        quadrant_df["Recall Rate"], errors="coerce"
    )
    quadrant_df["Cancer Detection Rate"] = pd.to_numeric(
        quadrant_df["Cancer Detection Rate"], errors="coerce"
    )
    quadrant_df = quadrant_df.dropna(subset=["Recall Rate", "Cancer Detection Rate"])

    if quadrant_df.empty:
        print("No data available for plotting.")
    else:
        fig, ax = plt.subplots(figsize=(11, 7.5))

        ax.scatter(
            quadrant_df["Recall Rate"],
            quadrant_df["Cancer Detection Rate"],
            color="#1f77b4",
            alpha=0.9,
            s=70,
        )

        for _, row in quadrant_df.iterrows():
            ax.annotate(
                row["Unique Code"],
                (row["Recall Rate"], row["Cancer Detection Rate"]),
                textcoords="offset points",
                xytext=(4, 4),
                fontsize=8,
                alpha=0.85,
            )

        x_mean = quadrant_df["Recall Rate"].mean()
        y_mean = quadrant_df["Cancer Detection Rate"].mean()

        ax.axvline(
            x=x_mean,
            color="#d62728",
            linestyle="--",
            linewidth=2,
            label="Mean Recall Rate",
        )
        ax.axhline(
            y=y_mean,
            color="#2ca02c",
            linestyle="--",
            linewidth=2,
            label="Mean Cancer Detection Rate",
        )

        label_box = {"facecolor": "white", "alpha": 0.78, "edgecolor": "#bdbdbd"}

        ax.text(
            0.02,
            0.94,
            "Better than average sensitivity\nand specificity",
            transform=ax.transAxes,
            va="top",
            ha="left",
            fontsize=9,
            bbox=label_box,
        )
        ax.text(
            0.98,
            0.92,
            "Better than average sensitivity\nand poorer specificity",
            transform=ax.transAxes,
            va="top",
            ha="right",
            fontsize=9,
            bbox=label_box,
        )
        ax.text(
            0.02,
            0.02,
            "Better than average specificity\nand poorer sensitivity",
            transform=ax.transAxes,
            va="bottom",
            ha="left",
            fontsize=9,
            bbox=label_box,
        )
        ax.text(
            0.98,
            0.02,
            "Poorer than average sensitivity\nand specificity",
            transform=ax.transAxes,
            va="bottom",
            ha="right",
            fontsize=9,
            bbox=label_box,
        )

        ax.set_title("Cancer Detection Rate vs Recall Rate")
        ax.set_xlabel("Recall Rate (%)")
        ax.set_ylabel("Cancer Detection Rate (per 1000)")
        ax.grid(True, alpha=0.25)

        ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.12), ncol=2, frameon=True)
        plt.subplots_adjust(bottom=0.2)

    return fig


def plot_funnel_chart(tables: pd.DataFrame, summary_table: pd.DataFrame) -> plt.Figure:
    first_reads_per_reader = (
        tables["ReadEpisode"]["first_reader_id"]
        .value_counts()
        .rename_axis("Unique Code")
        .reset_index(name="Number of first reads")
    )

    funnel_df = (
        summary_table[["Unique Code", "Cancer Detection Rate"]]
        .merge(first_reads_per_reader, on="Unique Code", how="left")
        .fillna({"Number of first reads": 0})
    )
    funnel_df["Number of first reads"] = funnel_df["Number of first reads"].astype(int)
    funnel_df["Cancer Detection Rate"] = pd.to_numeric(
        funnel_df["Cancer Detection Rate"], errors="coerce"
    )
    funnel_df = funnel_df.dropna(subset=["Cancer Detection Rate"])

    if funnel_df.empty or (funnel_df["Number of first reads"] <= 0).all():
        print("No data available for funnel chart.")
    else:
        plot_df = funnel_df.loc[funnel_df["Number of first reads"] > 0].copy()
        preprocessed = preprocess_kpi_data(tables)
        number_cancers_detected = kpi_number_cancers_detected(tables, preprocessed)
        reader_decision_counts = kpi_number_of_images_read(tables, preprocessed)
        total_detected = number_cancers_detected["cancers_detected_count"].sum()
        total_reads = reader_decision_counts["read_decision_count"].sum()
        p_bar = (total_detected / total_reads) if total_reads > 0 else 0.0
        average_cdr_per_1000 = p_bar * 1000

        n_min = max(1, int(plot_df["Number of first reads"].min()))
        n_max = int(plot_df["Number of first reads"].max())
        n_range = np.linspace(n_min, n_max, 300)

        se = np.sqrt(np.clip(p_bar * (1 - p_bar), a_min=0, a_max=None) / n_range)
        upper_95 = (p_bar + 1.96 * se) * 1000
        lower_95 = np.maximum((p_bar - 1.96 * se) * 1000, 0)

        fig, ax = plt.subplots(figsize=(10, 6.5))

        ax.scatter(
            plot_df["Number of first reads"],
            plot_df["Cancer Detection Rate"],
            color="#1f77b4",
            alpha=0.9,
            s=70,
        )

        for _, row in plot_df.iterrows():
            ax.annotate(
                row["Unique Code"],
                (row["Number of first reads"], row["Cancer Detection Rate"]),
                textcoords="offset points",
                xytext=(4, 4),
                fontsize=8,
                alpha=0.85,
            )

        ax.plot(
            n_range,
            np.full_like(n_range, average_cdr_per_1000),
            linestyle="--",
            linewidth=2,
            color="#d62728",
            label="Average Cancer Detection Rate",
        )
        ax.plot(
            n_range,
            upper_95,
            linestyle="-",
            linewidth=2,
            color="#2ca02c",
            label="Upper 95% limit",
        )
        ax.plot(
            n_range,
            lower_95,
            linestyle="-",
            linewidth=2,
            color="#2ca02c",
            label="Lower 95% limit",
        )

        ax.set_title("Funnel Chart: Cancer Detection Rate vs Number of First Reads")
        ax.set_xlabel("Number of first reads")
        ax.set_ylabel("Cancer Detection Rate (per 1000)")
        ax.grid(True, alpha=0.25)
        ax.legend(loc="best")
        plt.tight_layout()

    return fig
