import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import sys

TIMESTEP_HOURS = 0.25
FLOW_TO_KW = 1.0 / TIMESTEP_HOURS


def _resolve_energy_balance_mode():
    """Prompt user to choose between profit or emission energy balance."""
    mode_raw = sys.argv[1] if len(sys.argv) > 1 else None
    
    if mode_raw is None:
        mode_raw = input("Choose energy balance ('profit' or 'emission'): ")
    
    mode = str(mode_raw).strip().lower()
    mapping = {
        "profit": "cost",
        "cost": "cost",
        "emission": "emissions",
        "emissions": "emissions",
    }
    resolved = mapping.get(mode)
    if resolved is None:
        raise ValueError(
            f"Invalid energy balance mode '{mode_raw}'. Use 'profit' or 'emission'."
        )
    return resolved


def get_csv_path_and_label(objective_mode):
    """Return CSV path and label based on objective mode."""
    results_dir = "/workspaces/BAT/AEM Python Sim/V4/V4/results"
    if objective_mode == "cost":
        return (
            f"{results_dir}/cost_opt kWh results.csv",
            "cost-optimized solution",
        )
    else:
        return (
            f"{results_dir}/emis_opt kWh results.csv",
            "emissions-optimized solution",
        )


HTML_OUTPUT_PATH = "/workspaces/BAT/AEM Python Sim/V4/V4/results/plots/kW dispatch plot.html"


def build_figure(dataframe, plot_objective_label):
    dataframe = dataframe.copy()

    # Convert 15-minute energy flows [kWh per timestep] to average power [kW].
    # Storage states (battery_soc_kWh, ptes_soc_kWhth) remain in kWh.
    dataframe["production_negative_kW"] = -dataframe["production_kWh"] * FLOW_TO_KW
    dataframe["battery_discharge_negative_kW"] = -dataframe["battery_discharge_kWh"] * FLOW_TO_KW
    dataframe["grid_import_negative_kW"] = -dataframe["grid_import_kWh"] * FLOW_TO_KW
    dataframe["load_positive_kW"] = dataframe["load_kWh"] * FLOW_TO_KW
    dataframe["battery_charge_positive_kW"] = dataframe["battery_charge_kWh"] * FLOW_TO_KW
    dataframe["grid_export_positive_kW"] = dataframe["grid_export_kWh"] * FLOW_TO_KW
    dataframe["heatpump_elec_kW"] = dataframe["heatpump_elec_kWh"] * FLOW_TO_KW
    dataframe["woodchip_boiler_heat_negative_kWth"] = -dataframe["woodchip_boiler_heat_kWhth"] * FLOW_TO_KW
    dataframe["heatpump_heat_negative_kWth"] = -dataframe["heatpump_heat_kWhth"] * FLOW_TO_KW
    dataframe["ptes_discharge_negative_kWth"] = -dataframe["ptes_discharge_kWhth"] * FLOW_TO_KW
    dataframe["heatdemand_positive_kWth"] = dataframe["heatdemand_kWhth"] * FLOW_TO_KW
    dataframe["ptes_charge_positive_kWth"] = dataframe["ptes_charge_kWhth"] * FLOW_TO_KW

    fig = make_subplots(
        rows=3,
        cols=1,
        specs=[[{"secondary_y": True}], [{"secondary_y": True}], [{"secondary_y": True}]],
        subplot_titles=(
            "Electricity Dispatch Optimization",
            "Thermal Dispatch Optimization",
            "Spot Price",
        ),
        vertical_spacing=0.15,
    )

    # Electricity series
    elec_negative_series = [
        ("production_negative_kW", "RoR_production_kW"),
        ("battery_discharge_negative_kW", "battery_discharge_kW"),
        ("grid_import_negative_kW", "grid_import_kW"),
    ]
    elec_positive_series = [
        ("load_positive_kW", "load_kW"),
        ("grid_export_positive_kW", "grid_export_kW"),
        ("heatpump_elec_kW", "heatpump_elec_kW"),
        ("battery_charge_positive_kW", "battery_charge_kW"),
    ]

    # Thermal series - woodchip boiler supply and heat demand
    thermal_negative_series = [
        ("woodchip_boiler_heat_negative_kWth", "woodchip_boiler_heat_kWth"),
        ("heatpump_heat_negative_kWth", "heatpump_heat_kWth"),
        ("ptes_discharge_negative_kWth", "ptes_discharge_kWth"),
    ]
    thermal_positive_series = [
        ("heatdemand_positive_kWth", "heatdemand_kWth"),
        ("ptes_charge_positive_kWth", "ptes_charge_kWth"),
    ]

    colors = {
        "production_negative_kW": "#2ca02c",
        "battery_discharge_negative_kW": "#9467bd",
        "grid_import_negative_kW": "#1f77b4",
        "load_positive_kW": "#d62728",
        "battery_charge_positive_kW": "#ff7f0e",
        "grid_export_positive_kW": "#8c564b",
        "heatpump_elec_kW": "#17becf",
        "woodchip_boiler_heat_negative_kWth": "#e377c2",
        "heatpump_heat_negative_kWth": "#7f7f7f",
        "ptes_discharge_negative_kWth": "#bcbd22",
        "heatdemand_positive_kWth": "#d62728",
        "ptes_charge_positive_kWth": "#ff7f0e",
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

    # Add spot price to the electricity subplot (row 1) on a secondary axis
    fig.add_trace(
        go.Scatter(
            x=dataframe["DateTime"],
            y=dataframe["spot price [Rp/kWh]"],
            mode="lines",
            name="spot price [Rp/kWh]",
            line={"width": 1, "color": colors["spot price [Rp/kWh]"], "dash": "dot"},
        ),
        row=1,
        col=1,
        secondary_y=True,
    )

    # Move the spot-price trace to a tertiary y-axis overlaying the electricity subplot
    spot_indices = [i for i, t in enumerate(fig.data) if getattr(t, "name", None) == "spot price [Rp/kWh]"]
    if spot_indices:
        idx = spot_indices[-1]
        fig.data[idx].update(yaxis="y7")

        fig.update_layout(
            yaxis7=dict(
                title="Rp/kWh (spot price)",
                range=[-20, 40],
                overlaying="y",
                side="right",
                position=0.95,
                anchor="x1",
                showgrid=False,
            )
        )

    # (Battery and PTES SoC are plotted in their original subplots below)

    fig.add_trace(
        go.Scatter(
            x=dataframe["DateTime"],
            y=dataframe["battery_soc_kWh"],
            mode="lines",
            name="battery_soc_kWh",
            line={"width": 2, "color": "#BE34E0", "dash": "dash"},
            showlegend=True,
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

    fig.add_trace(
        go.Scatter(
            x=dataframe["DateTime"],
            y=dataframe["ptes_soc_kWhth"],
            mode="lines",
            name="ptes_soc_kWhth",
            line={"width": 2, "color": "#2225bd", "dash": "dash"},
            showlegend=True,
        ),
        row=2,
        col=1,
        secondary_y=True,
    )

    fig.add_hline(
        y=0.0,
        line={"width": 1, "color": "#111111", "dash": "dash"},
        secondary_y=False,
        row=2,
        col=1,
    )

    # Update axes
    fig.update_xaxes(title_text="DateTime", row=3, col=1)
    fig.update_yaxes(
        title_text="kW",
        zeroline=True,
        zerolinewidth=1,
        secondary_y=False,
        row=1,
    )
    # Secondary axis on electricity subplot used for battery SoC
    fig.update_yaxes(title_text="kWh (Battery SoC)", secondary_y=True, row=1)
    fig.update_yaxes(
        title_text="kW",
        zeroline=True,
        zerolinewidth=1,
        secondary_y=False,
        row=2,
    )
    fig.update_yaxes(title_text="kWh (PTES SoC)", secondary_y=True, row=2)
    # (Spot Price subplot left intentionally without price traces; axes controlled in other subplots)

    fig.update_layout(
        title=f"BESS+PTES+HP Energy Balance Analysis ({plot_objective_label})",
        template="plotly_white",
        hovermode="x unified",
        height=1300,
        legend_title="Series",
    )

    return fig


def main():
    objective_mode = _resolve_energy_balance_mode()
    csv_path, plot_label = get_csv_path_and_label(objective_mode)
    
    df = pd.read_csv(csv_path)
    df["DateTime"] = pd.to_datetime(df["DateTime"])

    fig = build_figure(df, plot_label)
    fig.add_annotation(
        text=f"Source: {objective_mode.capitalize()}-optimized kWh results.csv",
        xref="paper",
        yref="paper",
        x=0,
        y=-0.12,
        showarrow=False,
        font={"size": 12, "color": "#444444"},
        align="left",
    )
    fig.write_html(HTML_OUTPUT_PATH)
    fig.show()


if __name__ == "__main__":
    main()
