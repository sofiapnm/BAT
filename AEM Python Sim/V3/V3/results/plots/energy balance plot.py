import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

CSV_PATH = "/workspaces/BAT/AEM Python Sim/V3/V3/results/kWh Results.csv"
HTML_OUTPUT_PATH = "/workspaces/BAT/AEM Python Sim/V3/V3/results/plots/Energy balance plot.html"
PLOT_OBJECTIVE_LABEL = "cost-optimized solution"


def build_figure(dataframe):
    fig = make_subplots(
        rows=2,
        cols=1,
        specs=[[{"secondary_y": True}], [{"secondary_y": True}]],
        subplot_titles=("Electricity Energy Balance", "Thermal Energy Balance"),
        vertical_spacing=0.15,
    )

    # Electricity series
    elec_negative_series = [
        ("production_negative_kWh", "production_kWh"),
        ("battery_discharge_negative_kWh", "battery_discharge_kWh"),
        ("grid_import_negative_kWh", "grid_import_kWh"),
    ]
    elec_positive_series = [
        ("load_positive_kWh", "load_kWh"),
        ("battery_charge_positive_kWh", "battery_charge_kWh"),
        ("grid_export_positive_kWh", "grid_export_kWh"),
        ("heatpump_elec_kWh", "heatpump_elec_kWh"),
    ]

    # Thermal series - woodchip boiler supply and heat demand
    thermal_negative_series = [
        ("woodchip_boiler_heat_negative_kWhth", "woodchip_boiler_heat_kWhth"),
        ("heatpump_heat_negative_kWhth", "heatpump_heat_kWhth"),
    ]
    thermal_positive_series = [("heatdemand_positive_kWhth", "heatdemand_kWhth")]

    colors = {
        "production_negative_kWh": "#2ca02c",
        "battery_discharge_negative_kWh": "#9467bd",
        "grid_import_negative_kWh": "#1f77b4",
        "load_positive_kWh": "#d62728",
        "battery_charge_positive_kWh": "#ff7f0e",
        "grid_export_positive_kWh": "#8c564b",
        "heatpump_elec_kWh": "#17becf",
        "woodchip_boiler_heat_negative_kWhth": "#e377c2",
        "heatpump_heat_negative_kWhth": "#7f7f7f",
        "heatdemand_positive_kWhth": "#d62728",
        "spot price [Rp/kWh]": "#111111",
    }

    # Electricity plot (Row 1)
    for output_column, label in elec_negative_series:
        fig.add_trace(
            go.Scatter(
                x=dataframe["DateTime"],
                y=dataframe[output_column],
                mode="lines",
                name=label,
                line={"width": 1, "color": colors[output_column]},
                stackgroup="elec_negative",
                showlegend=True,
            ),
            row=1,
            col=1,
            secondary_y=False,
        )

    for output_column, label in elec_positive_series:
        fig.add_trace(
            go.Scatter(
                x=dataframe["DateTime"],
                y=dataframe[output_column],
                mode="lines",
                name=label,
                line={"width": 1, "color": colors[output_column]},
                stackgroup="elec_positive",
                showlegend=True,
            ),
            row=1,
            col=1,
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
        row=1,
        col=1,
        secondary_y=True,
    )

    fig.add_hline(
        y=0.0,
        line={"width": 1, "color": "#111111", "dash": "dash"},
        secondary_y=False,
        row=1,
        col=1,
    )

    # Thermal plot (Row 2)
    if "heatpump_heat_kWhth" in dataframe.columns:
        dataframe = dataframe.copy()
        dataframe["heatpump_heat_negative_kWhth"] = -dataframe["heatpump_heat_kWhth"]

    if "woodchip_boiler_heat_kWhth" in dataframe.columns:
        dataframe = dataframe.copy()
        dataframe["woodchip_boiler_heat_negative_kWhth"] = -dataframe["woodchip_boiler_heat_kWhth"]

    for output_column, label in thermal_negative_series:
        fig.add_trace(
            go.Scatter(
                x=dataframe["DateTime"],
                y=dataframe[output_column],
                mode="lines",
                name=label,
                line={"width": 1, "color": colors[output_column]},
                stackgroup="thermal_negative",
                showlegend=True,
            ),
            row=2,
            col=1,
            secondary_y=False,
        )

    for output_column, label in thermal_positive_series:
        fig.add_trace(
            go.Scatter(
                x=dataframe["DateTime"],
                y=dataframe[output_column],
                mode="lines",
                name=label,
                line={"width": 1, "color": colors[output_column]},
                stackgroup="thermal_positive",
                showlegend=True,
            ),
            row=2,
            col=1,
            secondary_y=False,
        )

    fig.add_hline(
        y=0.0,
        line={"width": 1, "color": "#111111", "dash": "dash"},
        secondary_y=False,
        row=2,
        col=1,
    )

    # Update axes
    fig.update_xaxes(title_text="DateTime", row=2, col=1)
    fig.update_yaxes(
        title_text="kWh per timestep",
        zeroline=True,
        zerolinewidth=1,
        secondary_y=False,
        row=1,
    )
    fig.update_yaxes(title_text="Rp/kWh", secondary_y=True, row=1)
    fig.update_yaxes(
        title_text="kWh per timestep",
        zeroline=True,
        zerolinewidth=1,
        secondary_y=False,
        row=2,
    )

    fig.update_layout(
        title=f"V3 Energy Balance Analysis ({PLOT_OBJECTIVE_LABEL})",
        template="plotly_white",
        hovermode="x unified",
        height=1000,
        legend_title="Series",
    )

    return fig


def main():
    df = pd.read_csv(CSV_PATH)
    df["DateTime"] = pd.to_datetime(df["DateTime"])

    # Create electricity energy columns
    df["production_negative_kWh"] = -df["production_kWh"]
    df["battery_discharge_negative_kWh"] = -df["battery_discharge_kWh"]
    df["grid_import_negative_kWh"] = -df["grid_import_kWh"]
    df["load_positive_kWh"] = df["load_kWh"]
    df["battery_charge_positive_kWh"] = df["battery_charge_kWh"]
    df["grid_export_positive_kWh"] = df["grid_export_kWh"]

    # Create thermal energy columns
    df["woodchip_boiler_heat_negative_kWhth"] = -df["woodchip_boiler_heat_kWhth"]
    df["heatdemand_positive_kWhth"] = df["heatdemand_kWhth"]

    fig = build_figure(df)
    fig.add_annotation(
        text="Source: kWh Results.csv built from the cost objective solution",
        xref="paper",
        yref="paper",
        x=0,
        y=1.08,
        showarrow=False,
        font={"size": 12, "color": "#444444"},
        align="left",
    )
    fig.write_html(HTML_OUTPUT_PATH)
    fig.show()


if __name__ == "__main__":
    main()
