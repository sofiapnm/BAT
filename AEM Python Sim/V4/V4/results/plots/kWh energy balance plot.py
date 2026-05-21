import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import sys


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


HTML_OUTPUT_PATH = "/workspaces/BAT/AEM Python Sim/V4/V4/results/plots/kWh energy balance plot.html"


def build_figure(dataframe, plot_objective_label):
    fig = make_subplots(
        rows=3,
        cols=1,
        specs=[[{"secondary_y": True}], [{"secondary_y": True}], [{"secondary_y": False}]],
        subplot_titles=(
            "Electricity Energy Balance",
            "Thermal Energy Balance",
            "Spot Price",
        ),
        vertical_spacing=0.15,
    )

    # Electricity series
    elec_negative_series = [
        ("production_negative_kWh", "RoR_production_kWh"),
        ("battery_discharge_negative_kWh", "battery_discharge_kWh"),
        ("grid_import_negative_kWh", "grid_import_kWh"),
    ]
    elec_positive_series = [
        ("load_positive_kWh", "load_kWh"),
        ("grid_export_positive_kWh", "grid_export_kWh"),
        ("heatpump_elec_kWh", "heatpump_elec_kWh"),
        ("battery_charge_positive_kWh", "battery_charge_kWh"),
    ]

    # Thermal series - woodchip boiler supply and heat demand
    thermal_negative_series = [
        ("woodchip_boiler_heat_negative_kWhth", "woodchip_boiler_heat_kWhth"),
        ("heatpump_heat_negative_kWhth", "heatpump_heat_kWhth"),
        ("ptes_discharge_negative_kWhth", "ptes_discharge_kWhth"),
    ]
    thermal_positive_series = [
        ("heatdemand_positive_kWhth", "heatdemand_kWhth"),
        ("ptes_charge_positive_kWhth", "ptes_charge_kWhth"),
    ]

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
        "ptes_discharge_negative_kWhth": "#bcbd22",
        "heatdemand_positive_kWhth": "#d62728",
        "ptes_charge_positive_kWhth": "#ff7f0e",
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
        row=3,
        col=1,
        secondary_y=False,
    )

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
            line={"width": 2, "color": "#bcbd22", "dash": "dash"},
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
        title_text="kWh per timestep",
        zeroline=True,
        zerolinewidth=1,
        secondary_y=False,
        row=1,
    )
    fig.update_yaxes(title_text="kWh (Battery SoC)", secondary_y=True, row=1)
    fig.update_yaxes(
        title_text="kWh per timestep",
        zeroline=True,
        zerolinewidth=1,
        secondary_y=False,
        row=2,
    )
    fig.update_yaxes(title_text="kWh (PTES SoC)", secondary_y=True, row=2)
    fig.update_yaxes(
        title_text="Rp/kWh",
        range=[-20, 40],
        zeroline=True,
        zerolinewidth=1,
        secondary_y=False,
        row=3,
    )

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
    df["ptes_discharge_negative_kWhth"] = -df["ptes_discharge_kWhth"]
    df["ptes_charge_positive_kWhth"] = df["ptes_charge_kWhth"]

    fig = build_figure(df, plot_label)
    fig.add_annotation(
        text=f"Source: {objective_mode.capitalize()}-optimized kWh Results.csv",
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
