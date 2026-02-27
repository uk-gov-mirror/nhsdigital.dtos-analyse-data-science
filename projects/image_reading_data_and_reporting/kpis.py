from __future__ import annotations

from typing import Dict

import pandas as pd


def preprocess_kpi_data(tables: Dict[str, pd.DataFrame]) -> Dict[str, pd.DataFrame]:
    rd_enriched = (
        tables["ReadDecision"]
        .merge(
            tables["ReadEpisode"][["read_episode_id"]],
            on="read_episode_id",
            how="inner",
        )
        .merge(
            tables["Image"][["read_episode_id", "appointment_id", "participant_id"]],
            on="read_episode_id",
            how="left",
        )
        .merge(
            tables["Appointment"][["appointment_id", "screening_episode_id"]],
            on="appointment_id",
            how="left",
        )
        .merge(
            tables["ScreeningEpisode"][
                ["screening_episode_id", "participant_id"]
            ].rename(columns={"participant_id": "screening_participant_id"}),
            on="screening_episode_id",
            how="left",
        )
        .merge(
            tables["Participant"][["participant_id"]],
            left_on="screening_participant_id",
            right_on="participant_id",
            how="left",
            suffixes=("", "_participant"),
        )
    )

    return {
        "rd_enriched": rd_enriched,
    }


def kpi_number_of_images_read(
    tables: Dict[str, pd.DataFrame], preprocessed: Dict[str, pd.DataFrame]
) -> pd.DataFrame:
    reader_decision_counts = (
        tables["Reader"][["reader_id"]]
        .merge(
            preprocessed["rd_enriched"]
            .groupby("reader_id", as_index=False)["read_decision_id"]
            .nunique()
            .rename(columns={"read_decision_id": "read_decision_count"}),
            on="reader_id",
            how="left",
        )
        .fillna({"read_decision_count": 0})
    )
    reader_decision_counts["read_decision_count"] = reader_decision_counts[
        "read_decision_count"
    ].astype(int)

    return reader_decision_counts.sort_values(
        ["read_decision_count", "reader_id"], ascending=[False, True]
    )


def kpi_number_recalled_for_assessment(
    tables: Dict[str, pd.DataFrame], preprocessed: Dict[str, pd.DataFrame]
) -> pd.DataFrame:
    recalled_for_assessment_per_reader = (
        tables["Reader"][["reader_id"]]
        .merge(
            preprocessed["rd_enriched"]
            .loc[
                preprocessed["rd_enriched"]["reader_decision"]
                == "Recall for Assessment"
            ]
            .groupby("reader_id", as_index=False)["read_decision_id"]
            .nunique()
            .rename(columns={"read_decision_id": "recalled_for_assessment_count"}),
            on="reader_id",
            how="left",
        )
        .fillna({"recalled_for_assessment_count": 0})
    )
    recalled_for_assessment_per_reader["recalled_for_assessment_count"] = (
        recalled_for_assessment_per_reader["recalled_for_assessment_count"].astype(int)
    )

    return recalled_for_assessment_per_reader.sort_values(
        ["recalled_for_assessment_count", "reader_id"], ascending=[False, True]
    )


def kpi_percentage_recalled_for_assessment(
    tables: Dict[str, pd.DataFrame],
    preprocessed: Dict[str, pd.DataFrame],
    reader_decision_counts: pd.DataFrame | None = None,
    recalled_for_assessment_per_reader: pd.DataFrame | None = None,
) -> pd.DataFrame:
    if reader_decision_counts is None:
        reader_decision_counts = kpi_number_of_images_read(tables, preprocessed)
    if recalled_for_assessment_per_reader is None:
        recalled_for_assessment_per_reader = kpi_number_recalled_for_assessment(
            tables, preprocessed
        )

    percentage_recalled_for_assessment_per_reader = (
        reader_decision_counts[["reader_id", "read_decision_count"]]
        .merge(
            recalled_for_assessment_per_reader[
                ["reader_id", "recalled_for_assessment_count"]
            ],
            on="reader_id",
            how="left",
        )
        .fillna({"recalled_for_assessment_count": 0})
    )

    percentage_recalled_for_assessment_per_reader["recalled_for_assessment_pct"] = (
        percentage_recalled_for_assessment_per_reader["recalled_for_assessment_count"]
        .div(
            percentage_recalled_for_assessment_per_reader[
                "read_decision_count"
            ].replace(0, pd.NA)
        )
        .mul(100)
        .fillna(0)
        .round(2)
    )

    return percentage_recalled_for_assessment_per_reader.sort_values(
        ["recalled_for_assessment_pct", "reader_id"], ascending=[False, True]
    )


def kpi_ppv_of_recall_for_assessment(
    tables: Dict[str, pd.DataFrame],
    preprocessed: Dict[str, pd.DataFrame],
    recalled_for_assessment_per_reader: pd.DataFrame | None = None,
) -> pd.DataFrame:
    if recalled_for_assessment_per_reader is None:
        recalled_for_assessment_per_reader = kpi_number_recalled_for_assessment(
            tables, preprocessed
        )

    ppv_of_recall_for_assessment_per_reader = (
        preprocessed["rd_enriched"]
        .loc[
            preprocessed["rd_enriched"]["reader_decision"] == "Recall for Assessment",
            ["reader_id", "read_episode_id"],
        ]
        .drop_duplicates()
        .merge(
            tables["CancerPresence"][["read_episode_id", "cancer_present"]],
            on="read_episode_id",
            how="left",
        )
    )

    ppv_numerator_per_reader = (
        ppv_of_recall_for_assessment_per_reader.assign(
            cancer_present=lambda dataframe: dataframe["cancer_present"]
            .astype(str)
            .str.lower()
            .eq("true")
        )
        .loc[lambda dataframe: dataframe["cancer_present"]]
        .groupby("reader_id", as_index=False)["read_episode_id"]
        .nunique()
        .rename(columns={"read_episode_id": "cancers_detected_after_recall_count"})
    )

    ppv_of_recall_for_assessment_per_reader = (
        recalled_for_assessment_per_reader[
            ["reader_id", "recalled_for_assessment_count"]
        ]
        .merge(ppv_numerator_per_reader, on="reader_id", how="left")
        .fillna({"cancers_detected_after_recall_count": 0})
    )

    ppv_of_recall_for_assessment_per_reader["cancers_detected_after_recall_count"] = (
        ppv_of_recall_for_assessment_per_reader[
            "cancers_detected_after_recall_count"
        ].astype(int)
    )

    ppv_of_recall_for_assessment_per_reader["ppv_recall_for_assessment_pct"] = (
        ppv_of_recall_for_assessment_per_reader["cancers_detected_after_recall_count"]
        .div(
            ppv_of_recall_for_assessment_per_reader[
                "recalled_for_assessment_count"
            ].replace(0, pd.NA)
        )
        .mul(100)
        .fillna(0)
        .round(2)
    )

    return ppv_of_recall_for_assessment_per_reader.sort_values(
        ["ppv_recall_for_assessment_pct", "reader_id"], ascending=[False, True]
    )


def kpi_number_cancers_detected(
    tables: Dict[str, pd.DataFrame], preprocessed: Dict[str, pd.DataFrame]
) -> pd.DataFrame:
    number_cancers_detected_per_reader = (
        preprocessed["rd_enriched"]
        .loc[
            preprocessed["rd_enriched"]["reader_decision"] == "Recall for Assessment",
            ["reader_id", "read_episode_id"],
        ]
        .drop_duplicates()
        .merge(
            tables["CancerPresence"][["read_episode_id", "cancer_present"]],
            on="read_episode_id",
            how="left",
        )
        .assign(
            cancer_present=lambda dataframe: dataframe["cancer_present"]
            .astype(str)
            .str.lower()
            .eq("true")
        )
        .loc[lambda dataframe: dataframe["cancer_present"]]
        .groupby("reader_id", as_index=False)["read_episode_id"]
        .nunique()
        .rename(columns={"read_episode_id": "cancers_detected_count"})
    )

    number_cancers_detected_per_reader = (
        tables["Reader"][["reader_id"]]
        .merge(number_cancers_detected_per_reader, on="reader_id", how="left")
        .fillna({"cancers_detected_count": 0})
    )

    number_cancers_detected_per_reader["cancers_detected_count"] = (
        number_cancers_detected_per_reader["cancers_detected_count"].astype(int)
    )

    return number_cancers_detected_per_reader.sort_values(
        ["cancers_detected_count", "reader_id"], ascending=[False, True]
    )


def kpi_cancer_detection_rate_per_1000(
    tables: Dict[str, pd.DataFrame],
    number_cancers_detected_per_reader: pd.DataFrame,
    preprocessed: Dict[str, pd.DataFrame],
    reader_decision_counts: pd.DataFrame | None = None,
) -> pd.DataFrame:
    if reader_decision_counts is None:
        reader_decision_counts = kpi_number_of_images_read(tables, preprocessed)

    cancer_detection_rate_per_1000_per_reader = (
        reader_decision_counts[["reader_id", "read_decision_count"]]
        .merge(
            number_cancers_detected_per_reader[["reader_id", "cancers_detected_count"]],
            on="reader_id",
            how="left",
        )
        .fillna({"cancers_detected_count": 0})
    )

    cancer_detection_rate_per_1000_per_reader["cancers_detected_count"] = (
        cancer_detection_rate_per_1000_per_reader["cancers_detected_count"].astype(int)
    )

    cancer_detection_rate_per_1000_per_reader["cancer_detection_rate_per_1000"] = (
        cancer_detection_rate_per_1000_per_reader["cancers_detected_count"]
        .div(
            cancer_detection_rate_per_1000_per_reader["read_decision_count"].replace(
                0, pd.NA
            )
        )
        .mul(1000)
        .fillna(0)
        .round(2)
    )

    return cancer_detection_rate_per_1000_per_reader.sort_values(
        ["cancer_detection_rate_per_1000", "reader_id"], ascending=[False, True]
    )


def kpi_number_discrepant_cancers(tables: Dict[str, pd.DataFrame]) -> pd.DataFrame:
    cancer_presence_by_episode = (
        tables["CancerPresence"][["read_episode_id", "cancer_present"]]
        .assign(
            cancer_present=lambda dataframe: dataframe["cancer_present"]
            .astype(str)
            .str.lower()
            .eq("true")
        )
        .loc[lambda dataframe: dataframe["cancer_present"]][["read_episode_id"]]
        .drop_duplicates()
    )

    episode_reader_decisions = (
        tables["ReadDecision"][["read_episode_id", "reader_id", "reader_decision"]]
        .drop_duplicates()
        .merge(cancer_presence_by_episode, on="read_episode_id", how="inner")
        .assign(
            reader_recalled=lambda dataframe: dataframe["reader_decision"].eq(
                "Recall for Assessment"
            )
        )
    )

    episode_recall_counts = (
        episode_reader_decisions.groupby("read_episode_id", as_index=False)[
            "reader_recalled"
        ]
        .sum()
        .rename(columns={"reader_recalled": "episode_recall_count"})
    )

    arbitration_recall_by_episode = (
        tables["ArbitrationDecision"][["read_decision_id", "arbitration_decision"]]
        .merge(
            tables["ReadDecision"][["read_decision_id", "read_episode_id"]],
            on="read_decision_id",
            how="left",
        )
        .assign(
            arbitration_recalled=lambda dataframe: dataframe["arbitration_decision"].eq(
                "Recall for Assessment"
            )
        )
        .groupby("read_episode_id", as_index=False)["arbitration_recalled"]
        .any()
    )

    discrepant_reader_decisions = (
        episode_reader_decisions.merge(
            episode_recall_counts, on="read_episode_id", how="left"
        )
        .merge(arbitration_recall_by_episode, on="read_episode_id", how="left")
        .fillna({"arbitration_recalled": False})
    )

    discrepant_reader_decisions["other_reader_recalled"] = (
        discrepant_reader_decisions["episode_recall_count"]
        - discrepant_reader_decisions["reader_recalled"].astype(int)
        > 0
    )

    discrepant_reader_decisions = discrepant_reader_decisions.loc[
        (~discrepant_reader_decisions["reader_recalled"])
        & (
            discrepant_reader_decisions["other_reader_recalled"]
            | discrepant_reader_decisions["arbitration_recalled"]
        )
    ]

    number_discrepant_cancers_per_reader = (
        discrepant_reader_decisions.groupby("reader_id", as_index=False)[
            "read_episode_id"
        ]
        .nunique()
        .rename(columns={"read_episode_id": "discrepant_cancers_count"})
    )

    number_discrepant_cancers_per_reader = (
        tables["Reader"][["reader_id"]]
        .merge(number_discrepant_cancers_per_reader, on="reader_id", how="left")
        .fillna({"discrepant_cancers_count": 0})
    )

    number_discrepant_cancers_per_reader["discrepant_cancers_count"] = (
        number_discrepant_cancers_per_reader["discrepant_cancers_count"].astype(int)
    )

    return number_discrepant_cancers_per_reader.sort_values(
        ["discrepant_cancers_count", "reader_id"], ascending=[False, True]
    )


def kpi_discrepant_cancer_rate(
    number_cancers_detected_per_reader: pd.DataFrame,
    number_discrepant_cancers_per_reader: pd.DataFrame,
) -> pd.DataFrame:
    discrepant_cancer_rate_per_reader = (
        number_cancers_detected_per_reader[["reader_id", "cancers_detected_count"]]
        .merge(
            number_discrepant_cancers_per_reader[
                ["reader_id", "discrepant_cancers_count"]
            ],
            on="reader_id",
            how="left",
        )
        .fillna({"discrepant_cancers_count": 0})
    )

    discrepant_cancer_rate_per_reader["discrepant_cancers_count"] = (
        discrepant_cancer_rate_per_reader["discrepant_cancers_count"].astype(int)
    )

    discrepant_cancer_rate_per_reader["total_cancer_cases_for_reader"] = (
        discrepant_cancer_rate_per_reader["cancers_detected_count"]
        + discrepant_cancer_rate_per_reader["discrepant_cancers_count"]
    )

    discrepant_cancer_rate_per_reader["discrepant_cancer_rate_pct"] = (
        discrepant_cancer_rate_per_reader["discrepant_cancers_count"]
        .div(
            discrepant_cancer_rate_per_reader["total_cancer_cases_for_reader"].replace(
                0, pd.NA
            )
        )
        .mul(100)
        .fillna(0)
        .round(2)
    )

    return discrepant_cancer_rate_per_reader.sort_values(
        ["discrepant_cancer_rate_pct", "reader_id"], ascending=[False, True]
    )


def kpi_number_biopsies(
    tables: Dict[str, pd.DataFrame], preprocessed: Dict[str, pd.DataFrame]
) -> pd.DataFrame:
    number_biopsies_per_reader = (
        preprocessed["rd_enriched"]
        .loc[
            preprocessed["rd_enriched"]["reader_decision"] == "Recall for Assessment",
            ["reader_id", "read_episode_id"],
        ]
        .drop_duplicates()
        .merge(
            tables["Biopsies"][["read_episode_id", "biopsy_result"]],
            on="read_episode_id",
            how="inner",
        )
        .groupby("reader_id", as_index=False)["read_episode_id"]
        .nunique()
        .rename(columns={"read_episode_id": "biopsies_count"})
    )

    number_biopsies_per_reader = (
        tables["Reader"][["reader_id"]]
        .merge(number_biopsies_per_reader, on="reader_id", how="left")
        .fillna({"biopsies_count": 0})
    )
    number_biopsies_per_reader["biopsies_count"] = number_biopsies_per_reader[
        "biopsies_count"
    ].astype(int)

    return number_biopsies_per_reader.sort_values(
        ["biopsies_count", "reader_id"], ascending=[False, True]
    )


def kpi_rate_of_benign_biopsy_per_1000(
    tables: Dict[str, pd.DataFrame],
    preprocessed: Dict[str, pd.DataFrame],
    reader_decision_counts: pd.DataFrame | None = None,
) -> pd.DataFrame:
    if reader_decision_counts is None:
        reader_decision_counts = kpi_number_of_images_read(tables, preprocessed)

    benign_biopsy_count_per_reader = (
        preprocessed["rd_enriched"]
        .loc[
            preprocessed["rd_enriched"]["reader_decision"] == "Recall for Assessment",
            ["reader_id", "read_episode_id"],
        ]
        .drop_duplicates()
        .merge(
            tables["Biopsies"][["read_episode_id", "biopsy_result"]],
            on="read_episode_id",
            how="inner",
        )
        .assign(
            biopsy_result=lambda dataframe: dataframe["biopsy_result"]
            .astype(str)
            .str.lower()
        )
        .loc[lambda dataframe: dataframe["biopsy_result"] == "benign"]
        .groupby("reader_id", as_index=False)["read_episode_id"]
        .nunique()
        .rename(columns={"read_episode_id": "benign_biopsies_count"})
    )

    rate_of_benign_biopsy_per_1000_per_reader = (
        reader_decision_counts[["reader_id", "read_decision_count"]]
        .merge(benign_biopsy_count_per_reader, on="reader_id", how="left")
        .fillna({"benign_biopsies_count": 0})
    )

    rate_of_benign_biopsy_per_1000_per_reader["benign_biopsies_count"] = (
        rate_of_benign_biopsy_per_1000_per_reader["benign_biopsies_count"].astype(int)
    )

    rate_of_benign_biopsy_per_1000_per_reader["benign_biopsy_rate_per_1000"] = (
        rate_of_benign_biopsy_per_1000_per_reader["benign_biopsies_count"]
        .div(
            rate_of_benign_biopsy_per_1000_per_reader["read_decision_count"].replace(
                0, pd.NA
            )
        )
        .mul(1000)
        .fillna(0)
        .round(2)
    )

    return rate_of_benign_biopsy_per_1000_per_reader.sort_values(
        ["benign_biopsy_rate_per_1000", "reader_id"], ascending=[False, True]
    )


def kpi_number_interval_cancers(
    tables: Dict[str, pd.DataFrame], preprocessed: Dict[str, pd.DataFrame]
) -> pd.DataFrame:
    interval_cancer_participants = (
        tables["IntervalCancers"][["participant_id", "interval_cancer_found"]]
        .assign(
            interval_cancer_found=lambda dataframe: dataframe["interval_cancer_found"]
            .astype(str)
            .str.upper()
            .eq("TRUE")
        )
        .loc[lambda dataframe: dataframe["interval_cancer_found"], ["participant_id"]]
        .drop_duplicates()
    )

    reader_participants = (
        preprocessed["rd_enriched"][["reader_id", "screening_participant_id"]]
        .dropna(subset=["screening_participant_id"])
        .drop_duplicates()
        .rename(columns={"screening_participant_id": "participant_id"})
    )

    number_interval_cancers_per_reader = (
        reader_participants.merge(
            interval_cancer_participants, on="participant_id", how="inner"
        )
        .groupby("reader_id", as_index=False)["participant_id"]
        .nunique()
        .rename(columns={"participant_id": "interval_cancers_count"})
    )

    number_interval_cancers_per_reader = (
        tables["Reader"][["reader_id"]]
        .merge(number_interval_cancers_per_reader, on="reader_id", how="left")
        .fillna({"interval_cancers_count": 0})
    )
    number_interval_cancers_per_reader["interval_cancers_count"] = (
        number_interval_cancers_per_reader["interval_cancers_count"].astype(int)
    )

    return number_interval_cancers_per_reader.sort_values(
        ["interval_cancers_count", "reader_id"], ascending=[False, True]
    )


def kpi_average_time_to_read(tables: Dict[str, pd.DataFrame]) -> pd.DataFrame:
    read_episode_times = tables["ReadEpisode"].copy()

    first_reader_times = read_episode_times[
        ["first_reader_id", "first_reader_started_at", "first_reader_ended_at"]
    ].rename(
        columns={
            "first_reader_id": "reader_id",
            "first_reader_started_at": "started_at",
            "first_reader_ended_at": "ended_at",
        }
    )

    second_reader_times = read_episode_times[
        ["second_reader_id", "second_reader_started_at", "second_reader_ended_at"]
    ].rename(
        columns={
            "second_reader_id": "reader_id",
            "second_reader_started_at": "started_at",
            "second_reader_ended_at": "ended_at",
        }
    )

    all_reader_times = pd.concat(
        [first_reader_times, second_reader_times], ignore_index=True
    )
    all_reader_times["started_at"] = pd.to_datetime(all_reader_times["started_at"])
    all_reader_times["ended_at"] = pd.to_datetime(all_reader_times["ended_at"])
    all_reader_times["read_time_minutes"] = (
        (all_reader_times["ended_at"] - all_reader_times["started_at"])
        .dt.total_seconds()
        .div(60)
    )

    average_time_to_read_per_reader = all_reader_times.groupby(
        "reader_id", as_index=False
    ).agg(
        average_read_time_minutes=("read_time_minutes", "mean"),
        read_sessions_count=("read_time_minutes", "count"),
    )

    average_time_to_read_per_reader["average_read_time_minutes"] = (
        average_time_to_read_per_reader["average_read_time_minutes"].round(2)
    )

    average_time_to_read_per_reader = (
        tables["Reader"][["reader_id"]]
        .merge(average_time_to_read_per_reader, on="reader_id", how="left")
        .fillna({"average_read_time_minutes": 0, "read_sessions_count": 0})
    )
    average_time_to_read_per_reader["read_sessions_count"] = (
        average_time_to_read_per_reader["read_sessions_count"].astype(int)
    )

    return average_time_to_read_per_reader.sort_values(
        ["average_read_time_minutes", "reader_id"], ascending=[False, True]
    )
