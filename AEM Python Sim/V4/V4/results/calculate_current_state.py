"""
Calculate the current-state baseline directly from the source CSV.

Baseline assumptions:
- no battery
- no PTES
- no heat pump
- hydro production serves electric load first, then exports surplus
- unmet electric load is imported from the grid
- district heat demand is supplied by the woodchip boiler
"""

from pathlib import Path
import sys

import pandas as pd


program_dir = Path(__file__).resolve().parents[1] / "program"
sys.path.insert(0, str(program_dir))

from parameters.general import GENERAL
from parameters.grid_export import EXPORT_EMISSIONS, export_price_rp_per_kwh
from parameters.grid_import import (
    IMPORT_EMISSIONS,
    annual_grid_use_hours,
    import_price_rp_per_kwh,
    power_tariff_rp_per_kw_per_month,
)
from parameters.runofriver import RUNOFRIVER_ECONOMIC, RUNOFRIVER_EMISSIONS
from parameters.woodchip_boiler import WOODCHIP_BOILER_ECONOMIC, WOODCHIP_BOILER_EMISSIONS


DEFAULT_SOURCE_CSV = "/workspaces/BAT/AEM Python Sim/Data Sorting/DATA/maxprod2024.csv"
DEFAULT_OUTPUT_CSV = "/workspaces/BAT/AEM Python Sim/V4/V4/results/pareto_currentstate_annual_summary.csv"


def _load_source_data(source_csv):
    df = pd.read_csv(source_csv)
    df["DateTime"] = pd.to_datetime(df["DateTime"])
    df = df.sort_values("DateTime").reset_index(drop=True)

    required_cols = [
        "Sales",
        "Total Production Hydro",
        "District heating sales",
        "Spot price [Rp/kWh]",
    ]
    missing = [col for col in required_cols if col not in df.columns]
    if missing:
        raise ValueError(f"Missing required source column(s): {', '.join(missing)}")

    for col in required_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df[required_cols] = df[required_cols].interpolate(limit_direction="both").ffill().bfill()
    if df[required_cols].isna().any().any():
        raise ValueError("Source data still contains NaN values after cleaning.")

    return df


def _monthly_peak_kw(datetime_series, grid_import_kwh, grid_export_kwh):
    delta_t_h = GENERAL["delta_t_h"]
    flow_kw = pd.concat(
        [
            grid_import_kwh.astype(float) / delta_t_h,
            grid_export_kwh.astype(float) / delta_t_h,
        ],
        axis=1,
    ).max(axis=1)
    month_labels = pd.to_datetime(datetime_series).dt.to_period("M").astype(str)
    return flow_kw.groupby(month_labels).max()


def calculate_current_state(
    source_csv=DEFAULT_SOURCE_CSV,
    output_path=DEFAULT_OUTPUT_CSV,
):
    """Calculate the no-battery/no-PTES current-state annual summary."""

    df = _load_source_data(source_csv)

    production_kwh = df["Total Production Hydro"].astype(float)
    load_kwh = df["Sales"].astype(float)
    heatdemand_kwhth = df["District heating sales"].astype(float)
    spot_price_rp_per_kwh = df["Spot price [Rp/kWh]"].astype(float)

    grid_import_kwh = (load_kwh - production_kwh).clip(lower=0.0)
    grid_export_kwh = (production_kwh - load_kwh).clip(lower=0.0)
    prod_for_local_kwh = pd.concat([production_kwh, load_kwh], axis=1).min(axis=1)

    annual_grid_import_kwh = float(grid_import_kwh.sum())
    annual_grid_export_kwh = float(grid_export_kwh.sum())
    annual_grid_use_h = annual_grid_use_hours(
        annual_grid_import_kwh,
        annual_grid_export_kwh,
    )

    monthly_peak = _monthly_peak_kw(df["DateTime"], grid_import_kwh, grid_export_kwh)
    power_tariff_rp = power_tariff_rp_per_kw_per_month(annual_grid_use_h)
    annual_power_cost_rp = float(monthly_peak.sum() * power_tariff_rp)

    load_revenue_rp_per_kwh = RUNOFRIVER_ECONOMIC.get("load_revenue_rp_per_kwh", 0.0)
    runofriver_cost_rp_per_kwh = RUNOFRIVER_ECONOMIC.get("cost_rp_per_kwh", 0.0)
    woodchip_cost_rp_per_kwhth = WOODCHIP_BOILER_ECONOMIC["cost_rp_per_kwhth_useful"]
    thermal_revenue_rp_per_kwhth = WOODCHIP_BOILER_ECONOMIC["revenue_rp_per_kwhth_sold"]

    annual_load_revenue_rp = float(load_kwh.sum() * load_revenue_rp_per_kwh)
    annual_export_revenue_rp = float(
        (grid_export_kwh * export_price_rp_per_kwh(spot_price_rp_per_kwh, annual_grid_use_h)).sum()
    )
    annual_thermal_revenue_rp = float(heatdemand_kwhth.sum() * thermal_revenue_rp_per_kwhth)
    annual_revenues_rp = (
        annual_load_revenue_rp
        + annual_export_revenue_rp
        + annual_thermal_revenue_rp
    )

    annual_import_cost_rp = float(
        (grid_import_kwh * import_price_rp_per_kwh(spot_price_rp_per_kwh, annual_grid_use_h)).sum()
    )
    annual_runofriver_cost_rp = float(production_kwh.sum() * runofriver_cost_rp_per_kwh)
    annual_woodchip_cost_rp = float(heatdemand_kwhth.sum() * woodchip_cost_rp_per_kwhth)
    annual_costs_rp = (
        annual_import_cost_rp
        + annual_runofriver_cost_rp
        + annual_woodchip_cost_rp
        + annual_power_cost_rp
    )

    annual_profit_rp = annual_revenues_rp - annual_costs_rp

    grid_emissions_per_kwh = IMPORT_EMISSIONS["grid_emissions_kgco2_per_kwh"]
    export_emissions_per_kwh = EXPORT_EMISSIONS["export_emissions_kgco2_per_kwh"]
    runofriver_emissions_per_kwh = RUNOFRIVER_EMISSIONS["emissions_kgco2eq_per_kwh_generated"]
    woodchip_emissions_per_kwhth = WOODCHIP_BOILER_EMISSIONS["emissions_kgco2eq_per_kwhth"]

    annual_import_emissions_kgco2 = float(grid_import_kwh.sum() * grid_emissions_per_kwh)
    annual_export_emissions_kgco2 = float(grid_export_kwh.sum() * export_emissions_per_kwh)
    annual_runofriver_emissions_kgco2 = float(production_kwh.sum() * runofriver_emissions_per_kwh)
    annual_woodchip_emissions_kgco2 = float(heatdemand_kwhth.sum() * woodchip_emissions_per_kwhth)
    annual_emissions_burden_kgco2 = (
        annual_import_emissions_kgco2
        + annual_export_emissions_kgco2
        + annual_runofriver_emissions_kgco2
        + annual_woodchip_emissions_kgco2
    )

    summary = {
        "source_csv": source_csv,
        "battery_installed": 0.0,
        "ptes_installed": 0.0,
        "heatpump_installed": 0.0,
        "net_annual_profit_chf": annual_profit_rp / 100.0,
        "annual_cost_burden_chf": -annual_profit_rp / 100.0,
        "annual_revenues_chf": annual_revenues_rp / 100.0,
        "annual_costs_chf": annual_costs_rp / 100.0,
        "annual_load_revenue_chf": annual_load_revenue_rp / 100.0,
        "annual_export_revenue_chf": annual_export_revenue_rp / 100.0,
        "annual_thermal_revenue_chf": annual_thermal_revenue_rp / 100.0,
        "annual_import_cost_chf": annual_import_cost_rp / 100.0,
        "annual_runofriver_cost_chf": annual_runofriver_cost_rp / 100.0,
        "annual_woodchip_cost_chf": annual_woodchip_cost_rp / 100.0,
        "annual_power_cost_chf": annual_power_cost_rp / 100.0,
        "power_tariff_chf_per_kw_per_month": power_tariff_rp / 100.0,
        "annual_emissions_burden_kgco2": annual_emissions_burden_kgco2,
        "annual_import_emissions_kgco2": annual_import_emissions_kgco2,
        "annual_export_emissions_kgco2": annual_export_emissions_kgco2,
        "annual_runofriver_emissions_kgco2": annual_runofriver_emissions_kgco2,
        "annual_woodchip_emissions_kgco2": annual_woodchip_emissions_kgco2,
        "annual_battery_throughput_emissions_kgco2": 0.0,
        "annual_ptes_emissions_kgco2": 0.0,
        "annual_heatpump_emissions_kgco2": 0.0,
        "annual_grid_import_kwh": annual_grid_import_kwh,
        "annual_grid_export_kwh": annual_grid_export_kwh,
        "annual_grid_use_h": annual_grid_use_h,
        "annual_production_kwh": float(production_kwh.sum()),
        "annual_load_kwh": float(load_kwh.sum()),
        "annual_prod_for_local_load_kwh": float(prod_for_local_kwh.sum()),
        "annual_woodchip_heat_kwhth": float(heatdemand_kwhth.sum()),
        "annual_battery_charge_kwh": 0.0,
        "annual_battery_discharge_kwh": 0.0,
        "annual_ptes_volume_m3": 0.0,
        "annual_ptes_fixed_cost_rp": 0.0,
        "interval_count": len(df),
    }

    current_state_df = pd.DataFrame([summary])
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    current_state_df.to_csv(output_path, index=False)

    print("Current State Calculation")
    print("=" * 70)
    print(f"Source CSV: {source_csv}")
    print("Assumptions: no battery, no PTES, no heat pump")
    print(f"Annual Production: {summary['annual_production_kwh']:,.2f} kWh")
    print(f"Annual Load: {summary['annual_load_kwh']:,.2f} kWh")
    print(f"Annual Grid Import: {annual_grid_import_kwh:,.2f} kWh")
    print(f"Annual Grid Export: {annual_grid_export_kwh:,.2f} kWh")
    print(f"Annual Grid Use Hours: {annual_grid_use_h:,.2f} h")
    print(f"Annual Revenues: {summary['annual_revenues_chf']:,.2f} CHF")
    print(f"Annual Costs: {summary['annual_costs_chf']:,.2f} CHF")
    print(f"Net Annual Profit: {summary['net_annual_profit_chf']:,.2f} CHF")
    print(f"Annual Emissions Burden: {annual_emissions_burden_kgco2:,.2f} kgCO2")
    print(f"Saved to: {output_path}")
    print("=" * 70)

    return current_state_df


if __name__ == "__main__":
    calculate_current_state()
