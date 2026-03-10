import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots


CSV_PATH = "/workspaces/BAT/AEM Python Sim/V1.1 Abstraction (Gurobi)/results/V1 kWh Results.csv"
HTML_OUTPUT_PATH = "/workspaces/BAT/AEM Python Sim/V1.1 Abstraction (Gurobi)/results/plots/V1 kWh profiles result.html"


def build_figure(dataframe):
    fig = make_subplots(
        rows=2,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.08,
        subplot_titles=("Power and Energy Flows", "Battery State of Charge"),
    )

    flow_columns = [
        "load_kWh",
        "production_kWh",
        "grid_export_import_kWh",
        "battery_charge_discharge_kWh",
    ]

    colors = {
        "load_kWh": "#1f77b4",
        "production_kWh": "#2ca02c",
        "grid_export_import_kWh": "#d62728",
        "battery_charge_discharge_kWh": "#ff7f0e",
        "battery_soc_kWh": "#111111",
    }

    for column in flow_columns:
        fig.add_trace(
            go.Scatter(
                x=dataframe["DateTime"],
                y=dataframe[column],
                mode="lines",
                name=column,
                line={"width": 1.5, "color": colors[column]},
            ),
            row=1,
            col=1,
        )

    fig.add_trace(
        go.Scatter(
            x=dataframe["DateTime"],
            y=dataframe["battery_soc_kWh"],
            mode="lines",
            name="battery_soc_kWh",
            line={"width": 2, "color": colors["battery_soc_kWh"]},
        ),
        row=2,
        col=1,
    )

    fig.update_yaxes(title_text="kWh per timestep", row=1, col=1)
    fig.update_yaxes(title_text="kWh", row=2, col=1)
    fig.update_xaxes(title_text="DateTime", row=2, col=1)

    fig.update_layout(
        title="V1 kWh Profiles",
        template="plotly_white",
        hovermode="x unified",
        height=850,
        legend_title="Series",
    )

    return fig


def main():
    df = pd.read_csv(CSV_PATH)
    df["DateTime"] = pd.to_datetime(df["DateTime"])
    df["grid_export_import_kWh"] = df["grid_import_kWh"] - df["grid_export_kWh"]
    df["battery_charge_discharge_kWh"] = (
        df["battery_charge_kWh"] - df["battery_discharge_kWh"]
    )

    fig = build_figure(df)
    fig.write_html(HTML_OUTPUT_PATH)
    fig.show()


if __name__ == "__main__":
    main()
