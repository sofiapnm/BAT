import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from pathlib import Path
import webbrowser


PLOTS_DIR = Path(__file__).resolve().parent
RESULTS_DIR = PLOTS_DIR.parent

CSV_PATH = RESULTS_DIR / "Pareto Front Results.csv"
HTML_OUTPUT_PATH = PLOTS_DIR / "Pareto front plot.html"
PARETO_CURRENT_STATE_CSV_PATH = RESULTS_DIR / "pareto_currentstate_annual_summary.csv"
RP_PER_CHF = 100.0


def load_current_state_point(summary_csv_path):
    summary_df = pd.read_csv(summary_csv_path)

    required_cols = ["annual_emissions_burden_kgco2", "net_annual_profit_chf"]
    missing_cols = [col for col in required_cols if col not in summary_df.columns]
    if missing_cols:
        raise KeyError(
            "Missing required current-state columns in summary CSV: "
            f"{missing_cols}"
        )
    if summary_df.empty:
        raise ValueError("Current-state summary CSV is empty.")

    row = summary_df.iloc[0]
    return row.to_dict()


def _first_available_numeric(row, column_names):
    for column_name in column_names:
        value = row.get(column_name)
        if pd.notna(value):
            return float(value)
    return None


def _append_currency_line(lines, label, value_chf):
    if value_chf is not None:
        lines.append(f"{label}: {value_chf:,.2f} CHF")


def _append_emissions_line(lines, label, value_kgco2):
    if value_kgco2 is not None:
        lines.append(f"{label}: {value_kgco2:,.2f} kgCO2")


def _build_hover_lines_from_row(row, include_annual_economic_burden=True):
    lines = []

    annual_cost_burden_chf = _first_available_numeric(
        row,
        ["annual_cost_burden_chf"],
    )
    if annual_cost_burden_chf is None:
        annual_cost_burden_rp = _first_available_numeric(row, ["annual_cost_burden_rp"])
        if annual_cost_burden_rp is not None:
            annual_cost_burden_chf = annual_cost_burden_rp / RP_PER_CHF

    annual_import_cost_chf = _first_available_numeric(
        row,
        ["annual_import_cost_chf"],
    )
    if annual_import_cost_chf is None:
        annual_import_cost_rp = _first_available_numeric(row, ["annual_import_cost_rp"])
        if annual_import_cost_rp is not None:
            annual_import_cost_chf = annual_import_cost_rp / RP_PER_CHF

    annual_export_revenue_chf = _first_available_numeric(
        row,
        ["annual_export_revenue_chf"],
    )
    if annual_export_revenue_chf is None:
        annual_export_revenue_rp = _first_available_numeric(
            row, ["annual_export_revenue_rp"]
        )
        if annual_export_revenue_rp is not None:
            annual_export_revenue_chf = annual_export_revenue_rp / RP_PER_CHF

    annual_runofriver_profit_chf = _first_available_numeric(
        row,
        ["annual_runofriver_profit_chf"],
    )
    if annual_runofriver_profit_chf is None:
        annual_runofriver_profit_rp = _first_available_numeric(
            row, ["annual_runofriver_profit_rp"]
        )
        if annual_runofriver_profit_rp is not None:
            annual_runofriver_profit_chf = annual_runofriver_profit_rp / RP_PER_CHF

    annual_power_cost_chf = _first_available_numeric(
        row,
        ["annual_power_cost_chf"],
    )
    if annual_power_cost_chf is None:
        annual_power_cost_rp = _first_available_numeric(row, ["annual_power_cost_rp"])
        if annual_power_cost_rp is not None:
            annual_power_cost_chf = annual_power_cost_rp / RP_PER_CHF

    net_annual_profit_chf = _first_available_numeric(row, ["net_annual_profit_chf"])

    annual_import_emissions_kgco2 = _first_available_numeric(
        row,
        ["annual_import_emissions_kgco2"],
    )
    annual_export_emissions_kgco2 = _first_available_numeric(
        row,
        ["annual_export_emissions_kgco2"],
    )
    annual_runofriver_emissions_kgco2 = _first_available_numeric(
        row,
        ["annual_runofriver_emissions_kgco2"],
    )
    annual_emissions_burden_kgco2 = _first_available_numeric(
        row,
        ["annual_emissions_burden_kgco2"],
    )

    _append_currency_line(lines, "Import cost burden", annual_import_cost_chf)
    _append_currency_line(lines, "Export revenue", annual_export_revenue_chf)
    _append_currency_line(lines, "Run-of-river operating profit", annual_runofriver_profit_chf)
    _append_currency_line(lines, "Power tariff cost", annual_power_cost_chf)
    if include_annual_economic_burden:
        _append_currency_line(lines, "Annual economic burden", annual_cost_burden_chf)
    _append_currency_line(lines, "Net annual profit", net_annual_profit_chf)

    _append_emissions_line(lines, "Import emissions", annual_import_emissions_kgco2)
    _append_emissions_line(lines, "Export emissions", annual_export_emissions_kgco2)
    _append_emissions_line(
        lines,
        "Run-of-river emissions",
        annual_runofriver_emissions_kgco2,
    )
    _append_emissions_line(lines, "Annual emissions burden", annual_emissions_burden_kgco2)

    return lines


def _build_pareto_hover_text(row):
    lines = [
        f"Pareto point {int(row['pareto_point'])}",
        f"Scenario: {row['scenario']}",
        f"Emissions cap: {float(row['emissions_cap_kgco2']):,.0f} kgCO2",
    ]
    lines.extend(_build_hover_lines_from_row(row, include_annual_economic_burden=False))
    return "<br>".join(lines)


def _build_anchor_hover_text(row, anchor_label):
    lines = [
        anchor_label,
        f"Pareto point {int(row['pareto_point'])}",
    ]
    lines.extend(_build_hover_lines_from_row(row, include_annual_economic_burden=False))
    return "<br>".join(lines)


def _build_current_state_hover_text(current_state_point):
    lines = ["Current state"]
    lines.extend(_build_hover_lines_from_row(current_state_point))
    return "<br>".join(lines)


def build_figure(dataframe, current_state_point):
    ordered_points = dataframe.sort_values("pareto_point")
    anchor_points = ordered_points[ordered_points["scenario"] != "epsilon_constrained_cost"]
    pareto_hover_text = ordered_points.apply(_build_pareto_hover_text, axis=1)

    fig = make_subplots(rows=1, cols=1)

    fig.add_trace(
        go.Scatter(
            x=ordered_points["annual_emissions_burden_kgco2"],
            y=ordered_points["net_annual_profit_chf"],
            mode="lines+markers",
            name="Pareto front",
            line={"width": 3, "color": "#1f77b4"},
            marker={"size": 8, "color": "#1f77b4"},
            hovertext=pareto_hover_text,
            hovertemplate="%{hovertext}<extra></extra>",
        )
    )

    anchor_colors = {
        "emissions_anchor": "#d62728",
        "cost_anchor": "#2ca02c",
    }
    anchor_labels = {
        "emissions_anchor": "Emissions anchor",
        "cost_anchor": "Cost anchor",
    }

    for scenario, anchor_df in anchor_points.groupby("scenario", sort=False):
        label = anchor_labels.get(scenario, scenario)
        anchor_hover_text = anchor_df.apply(
            lambda row: _build_anchor_hover_text(row, label),
            axis=1,
        )
        fig.add_trace(
            go.Scatter(
                x=anchor_df["annual_emissions_burden_kgco2"],
                y=anchor_df["net_annual_profit_chf"],
                mode="markers+text",
                name=label,
                marker={
                    "size": 13,
                    "color": anchor_colors.get(scenario, "#111111"),
                    "line": {"width": 1, "color": "#ffffff"},
                },
                text=[label],
                textposition="top center",
                hovertext=anchor_hover_text,
                hovertemplate="%{hovertext}<extra></extra>",
            )
        )

    current_state_hover_text = _build_current_state_hover_text(current_state_point)
    fig.add_trace(
        go.Scatter(
            x=[current_state_point["annual_emissions_burden_kgco2"]],
            y=[current_state_point["net_annual_profit_chf"]],
            mode="markers+text",
            name="Current state",
            marker={
                "symbol": "star",
                "size": 18,
                "color": "#9467bd",
                "line": {"width": 1.5, "color": "#ffffff"},
            },
            text=["current state"],
            textposition="top center",
            hovertext=[current_state_hover_text],
            hovertemplate="%{hovertext}<extra></extra>",
        )
    )

    fig.update_xaxes(title_text="Annual Emissions Burden [kgCO2]")
    fig.update_yaxes(title_text="Net Annual Profit [CHF]")
    fig.update_layout(
        title="Pareto Front Optimization of Grid Dispatch considering Technology Candidates, Cost and Emissions Minimization",
        template="plotly_white",
        hovermode="closest",
        height=700,
        legend_title="Series",
    )

    return fig


def open_html_in_browser(html_path):
    html_uri = Path(html_path).resolve().as_uri()
    chrome_candidates = [
        "google-chrome",
        "chrome",
        "chromium",
        "chromium-browser",
    ]

    for browser_name in chrome_candidates:
        try:
            browser = webbrowser.get(browser_name)
            browser.open_new_tab(html_uri)
            return
        except webbrowser.Error:
            continue

    webbrowser.open_new_tab(html_uri)


def main():
    df = pd.read_csv(CSV_PATH)
    current_state_point = load_current_state_point(PARETO_CURRENT_STATE_CSV_PATH)
    fig = build_figure(df, current_state_point)
    fig.write_html(
        HTML_OUTPUT_PATH,
        include_plotlyjs=True,
        full_html=True,
        config={"displayModeBar": False, "responsive": True},
    )
    open_html_in_browser(HTML_OUTPUT_PATH)


if __name__ == "__main__":
    main()
