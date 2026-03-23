import pandas as pd
import plotly.graph_objects as go


CSV_PATH = "/workspaces/BAT/AEM Python Sim/V1.2 Pareto Front/V1.1 Abstraction (Gurobi)/results/V1 Pareto Front Results.csv"
HTML_OUTPUT_PATH = "/workspaces/BAT/AEM Python Sim/V1.2 Pareto Front/V1.1 Abstraction (Gurobi)/results/plots/V1 pareto front plot.html"


def build_figure(dataframe):
    line_points = dataframe.sort_values("annual_emissions_burden_kgco2")
    anchor_points = dataframe[dataframe["scenario"] != "epsilon_constrained_cost"]

    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=line_points["annual_emissions_burden_kgco2"],
            y=line_points["net_annual_profit_chf"],
            mode="lines+markers",
            name="Pareto front",
            line={"width": 3, "color": "#1f77b4"},
            marker={"size": 8, "color": "#1f77b4"},
            customdata=line_points[["pareto_point", "emissions_cap_kgco2"]],
            hovertemplate=(
                "Pareto point %{customdata[0]}<br>"
                "Annual emissions burden: %{x:,.0f} kgCO2<br>"
                "Net annual profit: %{y:,.0f} CHF<br>"
                "Emissions cap: %{customdata[1]:,.0f} kgCO2<extra></extra>"
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

    for scenario, anchor_df in anchor_points.groupby("scenario"):
        fig.add_trace(
            go.Scatter(
                x=anchor_df["annual_emissions_burden_kgco2"],
                y=anchor_df["net_annual_profit_chf"],
                mode="markers+text",
                name=anchor_labels.get(scenario, scenario),
                marker={"size": 12, "color": anchor_colors.get(scenario, "#111111")},
                text=[anchor_labels.get(scenario, scenario)],
                textposition="top center",
                hovertemplate=(
                    "%{text}<br>"
                    "Annual emissions burden: %{x:,.0f} kgCO2<br>"
                    "Net annual profit: %{y:,.0f} CHF<extra></extra>"
                ),
            )
        )

    fig.update_xaxes(title_text="Annual Emissions Burden [kgCO2]")
    fig.update_yaxes(title_text="Net Annual Profit [CHF]")
    fig.update_layout(
        title="V1 Pareto Front",
        template="plotly_white",
        hovermode="closest",
        height=700,
        legend_title="Series",
    )

    return fig


def main():
    df = pd.read_csv(CSV_PATH).sort_values("annual_emissions_burden_kgco2")
    fig = build_figure(df)
    fig.write_html(
        HTML_OUTPUT_PATH,
        include_plotlyjs="cdn",
        full_html=True,
        config={"displayModeBar": False, "responsive": True},
    )


if __name__ == "__main__":
    main()
