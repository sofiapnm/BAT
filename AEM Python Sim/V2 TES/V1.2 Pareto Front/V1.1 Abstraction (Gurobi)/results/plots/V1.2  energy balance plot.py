import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

#need to change csv path for v1.2
CSV_PATH = "/workspaces/BAT/AEM Python Sim/V1.2 Pareto Front/V1.1 Abstraction (Gurobi)/results/V1 kWh Results.csv"
HTML_OUTPUT_PATH = "/workspaces/BAT/AEM Python Sim/V1.2 Pareto Front/V1.1 Abstraction (Gurobi)/results/plots/V1.2 energy balance plot.html"


def build_figure(dataframe):
    fig = make_subplots(specs=[[{"secondary_y": True}]])

    negative_series = [
        ("production_negative_kWh", "production_kWh"),
        ("battery_discharge_negative_kWh", "battery_discharge_kWh"),
        ("grid_import_negative_kWh", "grid_import_kWh"),
    ]
    positive_series = [
        ("load_positive_kWh", "load_kWh"),
        ("battery_charge_positive_kWh", "battery_charge_kWh"),
        ("grid_export_positive_kWh", "grid_export_kWh"),
    ]

    colors = {
        "production_negative_kWh": "#2ca02c",
        "battery_discharge_negative_kWh": "#9467bd",
        "grid_import_negative_kWh": "#1f77b4",
        "load_positive_kWh": "#d62728",
        "battery_charge_positive_kWh": "#ff7f0e",
        "grid_export_positive_kWh": "#8c564b",
        "spot price [Rp/kWh]": "#111111",
    }

    for output_column, label in negative_series:
        fig.add_trace(
            go.Scatter(
                x=dataframe["DateTime"],
                y=dataframe[output_column],
                mode="lines",
                name=label,
                line={"width": 1, "color": colors[output_column]},
                stackgroup="negative",
            ),
            secondary_y=False,
        )

    for output_column, label in positive_series:
        fig.add_trace(
            go.Scatter(
                x=dataframe["DateTime"],
                y=dataframe[output_column],
                mode="lines",
                name=label,
                line={"width": 1, "color": colors[output_column]},
                stackgroup="positive",
            ),
            secondary_y=False,
        )

    fig.add_trace(
        go.Scatter(
            x=dataframe["DateTime"],
            y=dataframe["spot price [Rp/kWh]"],
            mode="lines",
            name="spot price [Rp/kWh]",
            line={"width": 1, "color": colors["spot price [Rp/kWh]"]},
        ),
        secondary_y=True,
    )

    fig.add_hline(
        y=0.0,
        line={"width": 1, "color": "#111111", "dash": "dash"},
        secondary_y=False,
    )
    fig.update_xaxes(title_text="DateTime")
    fig.update_yaxes(
        title_text="kWh per timestep",
        zeroline=True,
        zerolinewidth=1,
        secondary_y=False,
    )
    fig.update_yaxes(title_text="Rp/kWh", secondary_y=True)
    fig.update_layout(
        title="V1 Energy Balance",
        template="plotly_white",
        hovermode="x unified",
        height=700,
        legend_title="Series",
    )

    return fig


def main():
    df = pd.read_csv(CSV_PATH)
    df["DateTime"] = pd.to_datetime(df["DateTime"])

    df["production_negative_kWh"] = -df["production_kWh"]
    df["battery_discharge_negative_kWh"] = -df["battery_discharge_kWh"]
    df["grid_import_negative_kWh"] = -df["grid_import_kWh"]
    df["load_positive_kWh"] = df["load_kWh"]
    df["battery_charge_positive_kWh"] = df["battery_charge_kWh"]
    df["grid_export_positive_kWh"] = df["grid_export_kWh"]

    fig = build_figure(df)
    fig.write_html(HTML_OUTPUT_PATH)
    fig.show()


if __name__ == "__main__":
    main()
