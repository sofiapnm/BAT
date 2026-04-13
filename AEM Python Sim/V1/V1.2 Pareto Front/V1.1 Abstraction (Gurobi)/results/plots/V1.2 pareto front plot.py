import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from pathlib import Path
import webbrowser


CSV_PATH = "/workspaces/BAT/AEM Python Sim/V1.2 Pareto Front/V1.1 Abstraction (Gurobi)/results/V1.2 Pareto 50 steps.csv"
HTML_OUTPUT_PATH = "/workspaces/BAT/AEM Python Sim/V1.2 Pareto Front/V1.1 Abstraction (Gurobi)/results/plots/V1.2 pareto front plot.html"


def build_figure(dataframe):
    ordered_points = dataframe.sort_values("pareto_point")
    anchor_points = ordered_points[ordered_points["scenario"] != "epsilon_constrained_cost"]

    fig = make_subplots(rows=1, cols=1)

    fig.add_trace(
        go.Scatter(
            x=ordered_points["annual_emissions_burden_kgco2"],
            y=ordered_points["net_annual_profit_chf"],
            mode="lines+markers",
            name="Pareto front",
            line={"width": 3, "color": "#1f77b4"},
            marker={"size": 8, "color": "#1f77b4"},
            customdata=ordered_points[["pareto_point", "scenario", "emissions_cap_kgco2"]],
            hovertemplate=(
                "Pareto point %{customdata[0]}<br>"
                "Scenario: %{customdata[1]}<br>"
                "Annual emissions burden: %{x:,.0f} kgCO2<br>"
                "Net annual profit: %{y:,.0f} CHF<br>"
                "Emissions cap: %{customdata[2]:,.0f} kgCO2<extra></extra>"
            ),
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
        fig.add_trace(
            go.Scatter(
                x=anchor_df["annual_emissions_burden_kgco2"],
                y=anchor_df["net_annual_profit_chf"],
                mode="markers+text",
                name=anchor_labels.get(scenario, scenario),
                marker={
                    "size": 13,
                    "color": anchor_colors.get(scenario, "#111111"),
                    "line": {"width": 1, "color": "#ffffff"},
                },
                text=[anchor_labels.get(scenario, scenario)],
                textposition="top center",
                customdata=anchor_df[["pareto_point"]],
                hovertemplate=(
                    "%{text}<br>"
                    "Pareto point %{customdata[0]}<br>"
                    "Annual emissions burden: %{x:,.0f} kgCO2<br>"
                    "Net annual profit: %{y:,.0f} CHF<extra></extra>"
                ),
            )
        )

    fig.update_xaxes(title_text="Annual Emissions Burden [kgCO2]")
    fig.update_yaxes(title_text="Net Annual Profit [CHF]")
    fig.update_layout(
        title="V1.2 Pareto Front",
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
    fig = build_figure(df)
    fig.write_html(
        HTML_OUTPUT_PATH,
        include_plotlyjs=True,
        full_html=True,
        config={"displayModeBar": False, "responsive": True},
    )
    open_html_in_browser(HTML_OUTPUT_PATH)


if __name__ == "__main__":
    main()
