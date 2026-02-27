from __future__ import annotations

import matplotlib.pyplot as plt
import streamlit as st

from visualisation import (
    build_summary_table,
    filter_by_bso,
    load_tables,
    plot_elliptical_chart,
    plot_funnel_chart,
    plot_quadrant_chart,
)


def apply_compact_layout(max_width_px: int = 1500) -> None:
    st.markdown(
        f"""
        <style>
            .main .block-container {{
                max-width: {max_width_px}px;
                padding-top: 1.25rem;
                padding-bottom: 1.25rem;
            }}
        </style>
        """,
        unsafe_allow_html=True,
    )


@st.cache_data
def get_tables_and_summary() -> tuple[dict, object]:
    tables = load_tables()
    summary = build_summary_table(tables)
    return tables, summary


def bso_selector(tab_label: str, bso_codes: list[str]) -> list[str]:
    return st.multiselect(
        label="Filter by BSO",
        options=bso_codes,
        default=bso_codes,
        key=f"bso_filter_{tab_label.lower().replace(' ', '_')}",
    )


def render_summary_tab(summary, bso_codes: list[str]) -> None:
    selected_bso = bso_selector("summary", bso_codes)
    filtered_summary = filter_by_bso(summary, selected_bso)
    st.dataframe(filtered_summary, width="stretch", hide_index=True)


def render_elliptical_tab(summary, bso_codes: list[str]) -> None:
    selected_bso = bso_selector("elliptical", bso_codes)
    filtered_summary = filter_by_bso(summary, selected_bso)
    fig = plot_elliptical_chart(filtered_summary)
    if fig is not None:
        st.pyplot(fig, width="stretch")
        plt.close(fig)
    else:
        st.info("No data available for the selected BSO filter.")


def render_quadrant_tab(summary, bso_codes: list[str]) -> None:
    selected_bso = bso_selector("quadrant", bso_codes)
    filtered_summary = filter_by_bso(summary, selected_bso)
    fig = plot_quadrant_chart(filtered_summary)
    if fig is not None:
        st.pyplot(fig, width="stretch")
        plt.close(fig)
    else:
        st.info("No data available for the selected BSO filter.")


def render_funnel_tab(tables, summary, bso_codes: list[str]) -> None:
    selected_bso = bso_selector("funnel", bso_codes)
    filtered_summary = filter_by_bso(summary, selected_bso)
    fig = plot_funnel_chart(tables, filtered_summary)
    if fig is not None:
        st.pyplot(fig, width="stretch")
        plt.close(fig)
    else:
        st.info("No data available for the selected BSO filter.")


def main() -> None:
    st.set_page_config(
        page_title="Synthetic Image Reading Visualisations", layout="centered"
    )
    apply_compact_layout()
    st.title("Synthetic Image Reading Visualisations")

    tables, summary = get_tables_and_summary()
    bso_codes = sorted(summary["BSO Code"].dropna().astype(str).unique().tolist())

    tab_summary, tab_elliptical, tab_quadrant, tab_funnel = st.tabs(
        ["Summary Table", "Elliptical Chart", "Quadrant Chart", "Funnel Chart"]
    )

    with tab_summary:
        render_summary_tab(summary, bso_codes)

    with tab_elliptical:
        render_elliptical_tab(summary, bso_codes)

    with tab_quadrant:
        render_quadrant_tab(summary, bso_codes)

    with tab_funnel:
        render_funnel_tab(tables, summary, bso_codes)


if __name__ == "__main__":
    main()
