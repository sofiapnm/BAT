import pandas as pd
from pathlib import Path

from parameters.battery import BATTERY_ECONOMIC, BATTERY_TECHNICAL
from parameters.battery import BATTERY_EMISSIONS
from parameters.general import GENERAL
from parameters.grid_import import (
    IMPORT_EMISSIONS,
    annual_grid_use_hours as annual_import_grid_use_hours,
    import_price_rp_per_kwh,
    power_tariff_rp_per_kw_per_month,
)
from parameters.grid_export import (
    EXPORT_EMISSIONS,
    export_price_rp_per_kwh,
)
from parameters.heat_pump import (
    HEAT_PUMP_TECHNICAL,
    HEAT_PUMP_ECONOMIC,
    HEAT_PUMP_EMISSIONS,
    heatpump_cop_profile,
    heatpump_total_cost_rp,
)
from parameters.runofriver import RUNOFRIVER_ECONOMIC, RUNOFRIVER_EMISSIONS
from parameters.woodchip_boiler import WOODCHIP_BOILER_ECONOMIC, WOODCHIP_BOILER_EMISSIONS
from parameters.ptes import PTES_TECHNICAL, PTES_ECONOMIC, PTES_EMISSIONS


def clean_zero(value, tol=1e-6):
    return 0.0 if abs(value) < tol else float(value)


def clean_binary(value, tol=1e-6):
    cleaned = clean_zero(value, tol=tol)
    return float(round(cleaned))


def extract_solution(vars_dict, n):
    battery_installed = clean_binary(vars_dict["battery_installed"].X)
    ptes_installed = clean_binary(vars_dict["ptes_installed"].X)
    battery_capacity = clean_zero(
        vars_dict["battery_capacity_kwh"].X
    ) if "battery_capacity_kwh" in vars_dict else BATTERY_TECHNICAL["capacity_kwh"]
    heatpump_nominal = float(
        vars_dict.get("heatpump_nominal_kwth", vars_dict.get("heatpump_nominal_kWhth")).X
    )
    ptes_volume = float(vars_dict["ptes_volume_m3"].X)
    heatpump_on_vals = (
        [vars_dict["heatpump_on"][t].X for t in range(n)]
        if "heatpump_on" in vars_dict
        else [1.0 if vars_dict["heatpump_elec_kWh"][t].X > 1e-6 else 0.0 for t in range(n)]
    )
    return pd.DataFrame(
        {
            "battery_installed": [battery_installed for _ in range(n)],
            "ptes_installed": [ptes_installed for _ in range(n)],
            "battery_capacity_kwh": [battery_capacity for _ in range(n)],
            "grid_import_kWh": [vars_dict["grid_import"][t].X for t in range(n)],
            "grid_export_kWh": [vars_dict["grid_export"][t].X for t in range(n)],
            "battery_charge_kWh": [vars_dict["batt_charge"][t].X for t in range(n)],
            "battery_discharge_kWh": [vars_dict["batt_discharge"][t].X for t in range(n)],
            "battery_soc_kWh": [vars_dict["soc"][t].X for t in range(n)],
            # `prod_for_local_demand` removed: production is reported directly
            "woodchip_boiler_heat_kWhth": [vars_dict["woodchip_boiler_heat_kWhth"][t].X for t in range(n)],
            "heatpump_heat_kWhth": [vars_dict["heatpump_heat_kWhth"][t].X for t in range(n)],
            "heatpump_elec_kWh": [vars_dict["heatpump_elec_kWh"][t].X for t in range(n)],
            "heatpump_on": heatpump_on_vals,
            "heatpump_nominal_kwth": [heatpump_nominal for _ in range(n)],
            "heatpump_nominal_kWhth": [heatpump_nominal * GENERAL["delta_t_h"] for _ in range(n)],
            "Q_HP_kWhth": [vars_dict["heatpump_heat_kWhth"][t].X for t in range(n)],
            "E_elec_HP_kWh": [vars_dict["heatpump_elec_kWh"][t].X for t in range(n)],
            "ptes_charge_kWhth": [vars_dict["ptes_charge_kWhth"][t].X for t in range(n)],
            "ptes_discharge_kWhth": [vars_dict["ptes_discharge_kWhth"][t].X for t in range(n)],
            "ptes_soc_kWhth": [vars_dict["ptes_soc_kWhth"][t].X for t in range(n)],
            "ptes_volume_m3": [ptes_volume for _ in range(n)],
        }
    )


def extract_monthly_peak_solution(vars_dict):
    monthly_peak = vars_dict["monthly_peak_kw"]
    unique_month_labels = vars_dict["unique_month_labels"]
    return pd.Series(
        {month_label: monthly_peak[month_label].X for month_label in unique_month_labels},
        dtype=float,
    )


def build_kwh_results_table(
    datetime_series,
    load_profile,
    heatdemand_profile,
    production_profile,
    spot_price_profile,
    solution,
):
    from parameters.heat_pump import HEAT_PUMP_TECHNICAL
    results = pd.DataFrame({"DateTime": datetime_series})
    results["load_kWh"] = pd.Series(load_profile, index=results.index, dtype=float)
    results["heatdemand_kWhth"] = pd.Series(
        heatdemand_profile, index=results.index, dtype=float
    )
    results["production_kWh"] = pd.Series(production_profile, index=results.index, dtype=float)
    results["spot price [Rp/kWh]"] = pd.Series(
        spot_price_profile, index=results.index, dtype=float
    )

    # Add monthly COP profile
    datetime_s = pd.to_datetime(datetime_series)
    months = datetime_s.dt.month.values
    cop_monthly = HEAT_PUMP_TECHNICAL["cop_monthly"]
    results["cop_monthly"] = [cop_monthly[int(m) - 1] if not pd.isna(m) else cop_monthly[0] for m in months]

    for col in solution.columns:
        results[col] = solution[col].values

    heatdemand_nonzero = results["heatdemand_kWhth"].replace(0.0, pd.NA)
    results["woodchip_heat_supply_share"] = (
        results["woodchip_boiler_heat_kWhth"].div(heatdemand_nonzero).fillna(0.0)
    )
    results["heatpump_heat_supply_share"] = (
        results["heatpump_heat_kWhth"].div(heatdemand_nonzero).fillna(0.0)
    )
    results["ptes_discharge_supply_share"] = (
        results["ptes_discharge_kWhth"].div(heatdemand_nonzero).fillna(0.0)
    )

    # Simple self-sufficiency metric: fraction of load met without grid imports
    # Per-step: 1 - grid_import / load (if load == 0 => set to 1.0)
    load_series = results["load_kWh"]
    grid_import_series = results.get("grid_import_kWh", pd.Series(0.0, index=results.index, dtype=float))
    # Avoid division by zero: where load==0, define self-sufficiency as 1.0
    self_suff = 1.0 - grid_import_series.div(load_series.replace(0.0, pd.NA))
    self_suff = self_suff.fillna(1.0).clip(lower=0.0, upper=1.0)
    results["self_sufficiency"] = self_suff

    # Production-traced self-sufficiency: account for direct production to load
    # and battery discharge that originated from production.
    # Assumptions:
    # - Production is prioritized to meet local load, then to charge the battery, then exported.
    # - Battery SOC is tracked in same units as `battery_soc_kWh` in solution.
    # - Charging stores `charge_eff * batt_charge` in SOC; discharging removes `batt_discharge` from SOC
    #   and delivers `discharge_eff * batt_discharge` to the load (matching model conventions).
    from parameters.battery import BATTERY_TECHNICAL
    charge_eff = BATTERY_TECHNICAL.get("charge_eff", 1.0)
    discharge_eff = BATTERY_TECHNICAL.get("discharge_eff", 1.0)

    # Prepare series (ensure present)
    prod = results["production_kWh"].fillna(0.0)
    load = results["load_kWh"].fillna(0.0)
    batt_charge = results.get("battery_charge_kWh", pd.Series(0.0, index=results.index)).fillna(0.0)
    batt_discharge = results.get("battery_discharge_kWh", pd.Series(0.0, index=results.index)).fillna(0.0)
    grid_import = results.get("grid_import_kWh", pd.Series(0.0, index=results.index)).fillna(0.0)

    # Initialize tracing state
    n_steps = len(results)
    soc_from_prod = [0.0] * n_steps
    soc_from_grid = [0.0] * n_steps
    direct_prod_to_load = [0.0] * n_steps
    prod_to_batt_charge = [0.0] * n_steps
    prod_via_batt_to_load = [0.0] * n_steps

    # Initial SOC split: assume starting SOC entirely from grid (conservative)
    prev_soc_prod = 0.0
    prev_soc_grid = results["battery_soc_kWh"].iloc[0] if "battery_soc_kWh" in results and len(results) > 0 else 0.0

    for t in range(n_steps):
        p = float(prod.iloc[t])
        L = float(load.iloc[t])
        bc = float(batt_charge.iloc[t])
        bd = float(batt_discharge.iloc[t])
        gi = float(grid_import.iloc[t])

        # 1) Production directly to load
        direct = min(p, L)
        direct_prod_to_load[t] = direct
        remaining_prod = max(0.0, p - direct)

        # 2) Production used to charge battery (up to batt_charge)
        prod_charge = min(remaining_prod, bc)
        prod_to_batt_charge[t] = prod_charge
        grid_to_batt_charge = max(0.0, bc - prod_charge)

        # 3) Update SOC pools after charging (stored amount is charge_eff * charge_energy)
        soc_prod_after_charge = prev_soc_prod + charge_eff * prod_charge
        soc_grid_after_charge = prev_soc_grid + charge_eff * grid_to_batt_charge

        soc_total_after_charge = soc_prod_after_charge + soc_grid_after_charge

        # 4) On discharge, draw from SOC pools proportionally
        if soc_total_after_charge > 0 and bd > 0:
            frac_prod = soc_prod_after_charge / soc_total_after_charge
            draw_prod = frac_prod * bd
            draw_grid = bd - draw_prod
        else:
            draw_prod = 0.0
            draw_grid = 0.0

        # Energy delivered to load from battery that originated from production
        prod_via_batt_to_load[t] = discharge_eff * draw_prod

        # 5) Update SOC for next step (after discharge)
        next_soc_prod = max(0.0, soc_prod_after_charge - draw_prod)
        next_soc_grid = max(0.0, soc_grid_after_charge - draw_grid)

        soc_from_prod[t] = soc_prod_after_charge if t == 0 else next_soc_prod
        soc_from_grid[t] = soc_grid_after_charge if t == 0 else next_soc_grid

        prev_soc_prod = next_soc_prod
        prev_soc_grid = next_soc_grid

    results["direct_prod_to_load_kWh"] = pd.Series(direct_prod_to_load, index=results.index, dtype=float)
    results["prod_to_batt_charge_kWh"] = pd.Series(prod_to_batt_charge, index=results.index, dtype=float)
    results["prod_via_batt_to_load_kWh"] = pd.Series(prod_via_batt_to_load, index=results.index, dtype=float)
    results["own_production_supply_kWh"] = results["direct_prod_to_load_kWh"] + results["prod_via_batt_to_load_kWh"]
    # Production-traced per-step self-sufficiency
    own_supply = results["own_production_supply_kWh"]
    per_step_ss = own_supply.div(results["load_kWh"].replace(0.0, pd.NA)).fillna(1.0).clip(lower=0.0, upper=1.0)
    results["self_sufficiency_production_traced"] = per_step_ss

    # Annual production-traced metric
    annual_own_supply = float(results["own_production_supply_kWh"].sum())
    annual_load = float(results["load_kWh"].sum())
    annual_prod_traced_ss = 1.0 if annual_load == 0 else max(0.0, min(1.0, annual_own_supply / annual_load))
    if len(results) > 0:
        results.loc[results.index[0], "cost_opt__annual_prod_traced_self_sufficiency_fraction"] = annual_prod_traced_ss
        results.loc[results.index[0], "cost_opt__annual_own_production_supply_kwh"] = annual_own_supply

    return results


def build_results_table(
    datetime_series,
    sol_cost,
    sol_emis,
    production,
    heatdemand_profile,
    spot_price,
    monthly_peak_cost,
    monthly_peak_emis,
):
    results = pd.DataFrame({"DateTime": datetime_series})
    results["heatdemand_kWhth"] = pd.Series(
        heatdemand_profile, index=results.index, dtype=float
    )

    for col in sol_cost.columns:
        results[f"cost_opt__{col}"] = sol_cost[col].values

    for col in sol_emis.columns:
        results[f"emissions_opt__{col}"] = sol_emis[col].values

    # Use chosen capacity from solution (kWh) and per-kWh economic params
    battery_capacity_kwh_cost = float(sol_cost["battery_capacity_kwh"].iloc[0]) if "battery_capacity_kwh" in sol_cost else BATTERY_TECHNICAL["capacity_kwh"]
    battery_capacity_kwh_emis = float(sol_emis["battery_capacity_kwh"].iloc[0]) if "battery_capacity_kwh" in sol_emis else BATTERY_TECHNICAL["capacity_kwh"]
    battery_capex = BATTERY_ECONOMIC["annual_capex_rp_per_kwh_amortized"]
    battery_annual_opex = BATTERY_ECONOMIC["annual_opex_rp_per_kwh_year"]
    battery_degradation_cost = BATTERY_ECONOMIC["degradation_cost_rp_per_kwh_throughput"]
    grid_emissions = IMPORT_EMISSIONS["grid_emissions_kgco2_per_kwh"]
    export_emissions = EXPORT_EMISSIONS["export_emissions_kgco2_per_kwh"]
    runofriver_cost_per_kwh = RUNOFRIVER_ECONOMIC.get("cost_rp_per_kwh", 0.0)
    runofriver_emissions_per_kwh = RUNOFRIVER_EMISSIONS["emissions_kgco2eq_per_kwh_generated"]
    woodchip_cost_per_kwhth = WOODCHIP_BOILER_ECONOMIC["cost_rp_per_kwhth_useful"]
    thermal_revenue_per_kwhth = WOODCHIP_BOILER_ECONOMIC["revenue_rp_per_kwhth_sold"]
    woodchip_emissions_per_kwhth = WOODCHIP_BOILER_EMISSIONS["emissions_kgco2eq_per_kwhth"]
    ptes_emissions_per_m3 = PTES_EMISSIONS["emissions_kgco2eq_per_m3"]
    battery_emissions_per_kwh = BATTERY_EMISSIONS["lifecycle_emissions_kgco2_per_kwh_throughput"]
    battery_throughput_emissions_per_kwh = (
        battery_emissions_per_kwh
        + BATTERY_EMISSIONS.get("battery_throughput_penalty_emissions", 0.0)
    )
    heatpump_electricity_emissions_factor = HEAT_PUMP_EMISSIONS.get(
        "electricity_source_emissions_kgco2_per_kwh"
    )
    if heatpump_electricity_emissions_factor is None:
        heatpump_electricity_emissions_factor = grid_emissions

    def heatpump_source_emissions_series(prefix):
        return pd.Series(
            heatpump_electricity_emissions_factor,
            index=results.index,
            dtype=float,
        )

    spot_price_series = pd.Series(spot_price, index=results.index, dtype=float)
    production_series = pd.Series(production, index=results.index, dtype=float)
    # Annual fixed cost scales with chosen capacity (kWh)
    annual_grid_use_hours_cost = annual_import_grid_use_hours(
        sol_cost["grid_import_kWh"].sum(),
        sol_cost["grid_export_kWh"].sum(),
    )
    annual_grid_use_hours_emis = annual_import_grid_use_hours(
        sol_emis["grid_import_kWh"].sum(),
        sol_emis["grid_export_kWh"].sum(),
    )
    power_tariff_cost = power_tariff_rp_per_kw_per_month(annual_grid_use_hours_cost)
    power_tariff_emis = power_tariff_rp_per_kw_per_month(annual_grid_use_hours_emis)
    month_labels = pd.to_datetime(datetime_series).dt.to_period("M").astype(str)
    first_step_in_month = ~month_labels.duplicated()
    monthly_power_cost_cost = month_labels.map(monthly_peak_cost).astype(float) * power_tariff_cost
    monthly_power_cost_emis = month_labels.map(monthly_peak_emis).astype(float) * power_tariff_emis
    annual_battery_fixed_cost_cost = (battery_capex + battery_annual_opex) * battery_capacity_kwh_cost
    annual_battery_fixed_cost_emis = (battery_capex + battery_annual_opex) * battery_capacity_kwh_emis
    # Annual self-sufficiency: compute from solution series and production
    annual_import_kwh = float(sol_cost["grid_import_kWh"].sum())
    annual_export_kwh = float(sol_cost["grid_export_kWh"].sum())
    batt_charge = float(sol_cost["battery_charge_kWh"].sum()) if "battery_charge_kWh" in sol_cost else 0.0
    batt_discharge = float(sol_cost["battery_discharge_kWh"].sum()) if "battery_discharge_kWh" in sol_cost else 0.0
    heatpump_elec = float(sol_cost["heatpump_elec_kWh"].sum()) if "heatpump_elec_kWh" in sol_cost else 0.0
    # Reconstruct annual load from energy balance: load = production + grid_import + batt_discharge - grid_export - batt_charge - heatpump_elec
    annual_load_kwh = float(production_series.sum() + annual_import_kwh + batt_discharge - annual_export_kwh - batt_charge - heatpump_elec)
    if annual_load_kwh > 0:
        annual_self_sufficiency = 1.0 - (annual_import_kwh / annual_load_kwh)
        annual_self_sufficiency = max(0.0, min(1.0, annual_self_sufficiency))
    else:
        annual_self_sufficiency = 1.0
    # Expose annual metrics as columns on the first row for easy reporting
    if len(results) > 0:
        results.loc[results.index[0], "cost_opt__annual_self_sufficiency_fraction"] = annual_self_sufficiency
        results.loc[results.index[0], "cost_opt__annual_load_kwh"] = annual_load_kwh
        results.loc[results.index[0], "cost_opt__annual_grid_import_kwh"] = annual_import_kwh
    # `prod_for_local_demand` removed. Run-of-river cost/emissions are derived from production.
    if "woodchip_boiler_heat_kWhth" in sol_cost:
        cost_woodchip_heat_series = pd.Series(
            sol_cost["woodchip_boiler_heat_kWhth"], index=results.index, dtype=float
        )
    else:
        cost_woodchip_heat_series = pd.Series(0.0, index=results.index, dtype=float)

    if "woodchip_boiler_heat_kWhth" in sol_emis:
        emis_woodchip_heat_series = pd.Series(
            sol_emis["woodchip_boiler_heat_kWhth"], index=results.index, dtype=float
        )
    else:
        emis_woodchip_heat_series = pd.Series(0.0, index=results.index, dtype=float)

    cost_heatpump_heat_series = pd.Series(
        sol_cost["heatpump_heat_kWhth"], index=results.index, dtype=float
    ) if "heatpump_heat_kWhth" in sol_cost else pd.Series(0.0, index=results.index, dtype=float)
    emis_heatpump_heat_series = pd.Series(
        sol_emis["heatpump_heat_kWhth"], index=results.index, dtype=float
    ) if "heatpump_heat_kWhth" in sol_emis else pd.Series(0.0, index=results.index, dtype=float)

    thermal_revenue_series = pd.Series(
        heatdemand_profile, index=results.index, dtype=float
    ) * thermal_revenue_per_kwhth

    results["cost_opt__monthly_power_tariff_rp"] = 0.0
    results["emissions_opt__monthly_power_tariff_rp"] = 0.0
    results["cost_opt__battery_fixed_cost_rp"] = 0.0
    results["emissions_opt__battery_fixed_cost_rp"] = 0.0
    results["cost_opt__heatpump_fixed_cost_rp"] = 0.0
    results["emissions_opt__heatpump_fixed_cost_rp"] = 0.0
    results["cost_opt__ptes_fixed_cost_rp"] = 0.0
    results["emissions_opt__ptes_fixed_cost_rp"] = 0.0
    results["cost_opt__ptes_emissions_kgco2"] = 0.0
    results["emissions_opt__ptes_emissions_kgco2"] = 0.0
    results["cost_opt__heatpump_emissions_kgco2"] = 0.0
    results["emissions_opt__heatpump_emissions_kgco2"] = 0.0
    results["cost_opt__battery_throughput_emissions_kgco2"] = (
        (
            results["cost_opt__battery_charge_kWh"]
            + results["cost_opt__battery_discharge_kWh"]
        )
        * battery_throughput_emissions_per_kwh
    )
    results["emissions_opt__battery_throughput_emissions_kgco2"] = (
        (
            results["emissions_opt__battery_charge_kWh"]
            + results["emissions_opt__battery_discharge_kWh"]
        )
        * battery_throughput_emissions_per_kwh
    )
    results["cost_opt__woodchip_cost_rp"] = (
        cost_woodchip_heat_series * woodchip_cost_per_kwhth
    )
    results["cost_opt__heatpump_heat_kWhth"] = cost_heatpump_heat_series
    results["cost_opt__Q_HP_kWhth"] = cost_heatpump_heat_series
    results["cost_opt__E_elec_HP_kWh"] = pd.Series(
        sol_cost["heatpump_elec_kWh"], index=results.index, dtype=float
    ) if "heatpump_elec_kWh" in sol_cost else pd.Series(0.0, index=results.index, dtype=float)
    cost_heatpump_source_emissions = heatpump_source_emissions_series("cost_opt")
    results["cost_opt__heatpump_electricity_source_emissions_kgco2_per_kwh"] = cost_heatpump_source_emissions
    results["cost_opt__heatpump_electricity_emissions_kgco2"] = (
        results["cost_opt__heatpump_elec_kWh"] * cost_heatpump_source_emissions
    ) if "cost_opt__heatpump_elec_kWh" in results else pd.Series(0.0, index=results.index, dtype=float)
    results["cost_opt__heatpump_emissions_kgco2"] = (
        cost_heatpump_heat_series * HEAT_PUMP_EMISSIONS["emissions_kgco2eq_per_kwhth"]
        + results["cost_opt__heatpump_electricity_emissions_kgco2"]
    )
    results["cost_opt__ptes_charge_kWhth"] = pd.Series(
        sol_cost["ptes_charge_kWhth"], index=results.index, dtype=float
    ) if "ptes_charge_kWhth" in sol_cost else pd.Series(0.0, index=results.index, dtype=float)
    results["cost_opt__ptes_discharge_kWhth"] = pd.Series(
        sol_cost["ptes_discharge_kWhth"], index=results.index, dtype=float
    ) if "ptes_discharge_kWhth" in sol_cost else pd.Series(0.0, index=results.index, dtype=float)
    results["cost_opt__ptes_soc_kWhth"] = pd.Series(
        sol_cost["ptes_soc_kWhth"], index=results.index, dtype=float
    ) if "ptes_soc_kWhth" in sol_cost else pd.Series(0.0, index=results.index, dtype=float)
    results["cost_opt__woodchip_heat_supply_share"] = (
        results["cost_opt__woodchip_boiler_heat_kWhth"]
        .div(results["heatdemand_kWhth"].replace(0.0, pd.NA))
        .fillna(0.0)
    )
    results["cost_opt__heatpump_heat_supply_share"] = (
        results["cost_opt__heatpump_heat_kWhth"]
        .div(results["heatdemand_kWhth"].replace(0.0, pd.NA))
        .fillna(0.0)
    )
    results["cost_opt__ptes_discharge_supply_share"] = (
        results["cost_opt__ptes_discharge_kWhth"]
        .div(results["heatdemand_kWhth"].replace(0.0, pd.NA))
        .fillna(0.0)
    )
    results["cost_opt__thermal_revenue_rp"] = thermal_revenue_series
    results["emissions_opt__woodchip_cost_rp"] = (
        emis_woodchip_heat_series * woodchip_cost_per_kwhth
    )
    results["emissions_opt__heatpump_heat_kWhth"] = emis_heatpump_heat_series
    results["emissions_opt__Q_HP_kWhth"] = emis_heatpump_heat_series
    results["emissions_opt__E_elec_HP_kWh"] = pd.Series(
        sol_emis["heatpump_elec_kWh"], index=results.index, dtype=float
    ) if "heatpump_elec_kWh" in sol_emis else pd.Series(0.0, index=results.index, dtype=float)
    emis_heatpump_source_emissions = heatpump_source_emissions_series("emissions_opt")
    results["emissions_opt__heatpump_electricity_source_emissions_kgco2_per_kwh"] = emis_heatpump_source_emissions
    results["emissions_opt__heatpump_electricity_emissions_kgco2"] = (
        results["emissions_opt__heatpump_elec_kWh"] * emis_heatpump_source_emissions
    ) if "emissions_opt__heatpump_elec_kWh" in results else pd.Series(0.0, index=results.index, dtype=float)
    results["emissions_opt__heatpump_emissions_kgco2"] = (
        emis_heatpump_heat_series * HEAT_PUMP_EMISSIONS["emissions_kgco2eq_per_kwhth"]
        + results["emissions_opt__heatpump_electricity_emissions_kgco2"]
    )
    results["emissions_opt__ptes_charge_kWhth"] = pd.Series(
        sol_emis["ptes_charge_kWhth"], index=results.index, dtype=float
    ) if "ptes_charge_kWhth" in sol_emis else pd.Series(0.0, index=results.index, dtype=float)
    results["emissions_opt__ptes_discharge_kWhth"] = pd.Series(
        sol_emis["ptes_discharge_kWhth"], index=results.index, dtype=float
    ) if "ptes_discharge_kWhth" in sol_emis else pd.Series(0.0, index=results.index, dtype=float)
    results["emissions_opt__ptes_soc_kWhth"] = pd.Series(
        sol_emis["ptes_soc_kWhth"], index=results.index, dtype=float
    ) if "ptes_soc_kWhth" in sol_emis else pd.Series(0.0, index=results.index, dtype=float)
    results["emissions_opt__woodchip_heat_supply_share"] = (
        results["emissions_opt__woodchip_boiler_heat_kWhth"]
        .div(results["heatdemand_kWhth"].replace(0.0, pd.NA))
        .fillna(0.0)
    )
    results["emissions_opt__heatpump_heat_supply_share"] = (
        results["emissions_opt__heatpump_heat_kWhth"]
        .div(results["heatdemand_kWhth"].replace(0.0, pd.NA))
        .fillna(0.0)
    )
    results["emissions_opt__ptes_discharge_supply_share"] = (
        results["emissions_opt__ptes_discharge_kWhth"]
        .div(results["heatdemand_kWhth"].replace(0.0, pd.NA))
        .fillna(0.0)
    )
    results["emissions_opt__thermal_revenue_rp"] = thermal_revenue_series
    # Run-of-river generation cost (per-kWh cost applied to production)
    runofriver_emis_per_kwh = RUNOFRIVER_EMISSIONS["emissions_kgco2eq_per_kwh_generated"]
    results["cost_opt__runofriver_cost_rp"] = production_series * runofriver_cost_per_kwh
    results["emissions_opt__runofriver_cost_rp"] = production_series * runofriver_cost_per_kwh
    results["emissions_opt__runofriver_kgco2"] = production_series * runofriver_emis_per_kwh
    results.loc[first_step_in_month, "cost_opt__monthly_power_tariff_rp"] = monthly_power_cost_cost[first_step_in_month].values
    results.loc[first_step_in_month, "emissions_opt__monthly_power_tariff_rp"] = monthly_power_cost_emis[first_step_in_month].values
    if len(results) > 0:
        results.loc[results.index[0], "cost_opt__battery_fixed_cost_rp"] = annual_battery_fixed_cost_cost
        results.loc[results.index[0], "emissions_opt__battery_fixed_cost_rp"] = annual_battery_fixed_cost_emis
        heatpump_nominal = float(sol_cost["heatpump_nominal_kWhth"].iloc[0]) if "heatpump_nominal_kWhth" in sol_cost else 0.0
        heatpump_lifetime_years = HEAT_PUMP_ECONOMIC.get("heatpump_lifetime_years", 30)
        heatpump_annual_opex_pct = HEAT_PUMP_ECONOMIC.get("annual_opex_percentage_of_capex", 0.01)
        heatpump_capex_rp = heatpump_total_cost_rp(heatpump_nominal)
        heatpump_fixed_cost_rp = (
            heatpump_capex_rp / heatpump_lifetime_years
            + heatpump_capex_rp * heatpump_annual_opex_pct
        )
        results.loc[results.index[0], "cost_opt__heatpump_fixed_cost_rp"] = heatpump_fixed_cost_rp
        results.loc[results.index[0], "emissions_opt__heatpump_fixed_cost_rp"] = heatpump_fixed_cost_rp
        
        # PTES costs and emissions
        ptes_volume_cost = float(sol_cost["ptes_volume_m3"].iloc[0]) if "ptes_volume_m3" in sol_cost else 0.0
        ptes_volume_emis = float(sol_emis["ptes_volume_m3"].iloc[0]) if "ptes_volume_m3" in sol_emis else 0.0
        
        # Compute PTES cost using the cost function (annualized over 30 years)
        # Cost formula: CAPEX = specific_cost_chf_per_m3 * V, where specific_cost = coeff * V^exp
        def ptes_annual_cost_rp(volume):
            if volume <= 0:
                return 0.0
            coeff = PTES_ECONOMIC["specific_cost_chf_coeff"]
            exp = PTES_ECONOMIC["specific_cost_exp"]
            lifetime = PTES_ECONOMIC.get("lifetime_years", PTES_TECHNICAL.get("lifetime_years", 30))
            opex_pct = PTES_ECONOMIC.get("annual_opex_percentage_of_capex", 0.01)
            
            specific_cost_chf_per_m3 = coeff * (volume ** exp)
            total_capex_chf = specific_cost_chf_per_m3 * volume  # MULTIPLY by volume
            total_capex_rp = total_capex_chf * 100.0
            annual_capex_rp = total_capex_rp / lifetime
            annual_opex_rp = total_capex_rp * opex_pct
            return annual_capex_rp + annual_opex_rp
        
        ptes_cost_rp_cost = ptes_annual_cost_rp(ptes_volume_cost)
        ptes_cost_rp_emis = ptes_annual_cost_rp(ptes_volume_emis)
        # PTES emissions: embodied carbon per m³ per year
        ptes_emissions_cost = ptes_volume_cost * PTES_EMISSIONS["emissions_kgco2eq_per_m3"]
        ptes_emissions_emis = ptes_volume_emis * PTES_EMISSIONS["emissions_kgco2eq_per_m3"]
        
        results.loc[results.index[0], "cost_opt__ptes_fixed_cost_rp"] = ptes_cost_rp_cost
        results.loc[results.index[0], "emissions_opt__ptes_fixed_cost_rp"] = ptes_cost_rp_emis
        results.loc[results.index[0], "cost_opt__ptes_emissions_kgco2"] = ptes_emissions_cost
        results.loc[results.index[0], "emissions_opt__ptes_emissions_kgco2"] = ptes_emissions_emis

    results["cost_opt__step_cost_rp"] = (
        results["cost_opt__grid_import_kWh"]
        * import_price_rp_per_kwh(spot_price_series, annual_grid_use_hours_cost)
        - results["cost_opt__grid_export_kWh"]
        * export_price_rp_per_kwh(spot_price_series, annual_grid_use_hours_cost)
        + battery_degradation_cost
        * (
            results["cost_opt__battery_charge_kWh"]
            + results["cost_opt__battery_discharge_kWh"]
        )
        + results["cost_opt__runofriver_cost_rp"]
        + results["cost_opt__woodchip_cost_rp"]
        - results["cost_opt__thermal_revenue_rp"]
        + results["cost_opt__monthly_power_tariff_rp"]
        + results["cost_opt__battery_fixed_cost_rp"]
        + results["cost_opt__heatpump_fixed_cost_rp"]
        + results["cost_opt__ptes_fixed_cost_rp"]
    )

    results["emissions_opt__step_cost_rp"] = (
        results["emissions_opt__grid_import_kWh"]
        * import_price_rp_per_kwh(spot_price_series, annual_grid_use_hours_emis)
        - results["emissions_opt__grid_export_kWh"]
        * export_price_rp_per_kwh(spot_price_series, annual_grid_use_hours_emis)
        + battery_degradation_cost
        * (
            results["emissions_opt__battery_charge_kWh"]
            + results["emissions_opt__battery_discharge_kWh"]
        )
        + results["emissions_opt__runofriver_cost_rp"]
        + results["emissions_opt__woodchip_cost_rp"]
        - results["emissions_opt__thermal_revenue_rp"]
        + results["emissions_opt__monthly_power_tariff_rp"]
        + results["emissions_opt__battery_fixed_cost_rp"]
        + results["emissions_opt__heatpump_fixed_cost_rp"]
        + results["emissions_opt__ptes_fixed_cost_rp"]
    )

    results["cost_opt__step_emissions_kgco2"] = (
        results["cost_opt__grid_import_kWh"] * grid_emissions
        + results["cost_opt__grid_export_kWh"] * export_emissions
        + production_series * runofriver_emissions_per_kwh
        + cost_woodchip_heat_series * woodchip_emissions_per_kwhth
        + results["cost_opt__heatpump_emissions_kgco2"]
        + results["cost_opt__ptes_emissions_kgco2"]
        + results["cost_opt__battery_throughput_emissions_kgco2"]
    )

    results["emissions_opt__step_emissions_kgco2"] = (
        results["emissions_opt__grid_import_kWh"] * grid_emissions
        + results["emissions_opt__grid_export_kWh"] * export_emissions
        + production_series * runofriver_emissions_per_kwh
        + emis_woodchip_heat_series * woodchip_emissions_per_kwhth
        + results["emissions_opt__heatpump_emissions_kgco2"]
        + results["emissions_opt__ptes_emissions_kgco2"]
        + results["emissions_opt__battery_throughput_emissions_kgco2"]
    )

    return results


def summarize_solution(
    solution,
    production,
    heatdemand,
    spot_price,
    monthly_peak,
    datetime_series=None,
):
    battery_degradation_cost = BATTERY_ECONOMIC["degradation_cost_rp_per_kwh_throughput"]
    grid_emissions = IMPORT_EMISSIONS["grid_emissions_kgco2_per_kwh"]
    export_emissions = EXPORT_EMISSIONS["export_emissions_kgco2_per_kwh"]
    runofriver_cost_per_kwh = RUNOFRIVER_ECONOMIC.get("cost_rp_per_kwh", 0.0)
    runofriver_emissions_per_kwh = RUNOFRIVER_EMISSIONS["emissions_kgco2eq_per_kwh_generated"]
    woodchip_cost_per_kwhth = WOODCHIP_BOILER_ECONOMIC["cost_rp_per_kwhth_useful"]
    thermal_revenue_per_kwhth = WOODCHIP_BOILER_ECONOMIC["revenue_rp_per_kwhth_sold"]
    woodchip_emissions_per_kwhth = WOODCHIP_BOILER_EMISSIONS["emissions_kgco2eq_per_kwhth"]
    ptes_emissions_per_m3 = PTES_EMISSIONS["emissions_kgco2eq_per_m3"]
    heatpump_lifetime_years = HEAT_PUMP_ECONOMIC.get("heatpump_lifetime_years", 30)
    heatpump_annual_opex_pct = HEAT_PUMP_ECONOMIC.get("annual_opex_percentage_of_capex", 0.01)
    heatpump_emissions_per_kwhth = HEAT_PUMP_EMISSIONS["emissions_kgco2eq_per_kwhth"]
    production_series = pd.Series(production, dtype=float)
    heatpump_cop_series = (
        pd.Series(heatpump_cop_profile(datetime_series), dtype=float)
        if datetime_series is not None
        else pd.Series([HEAT_PUMP_TECHNICAL["cop_monthly"][0]] * len(solution), dtype=float)
    )
    heatpump_source_emissions = HEAT_PUMP_EMISSIONS.get("electricity_source_emissions_kgco2_per_kwh")
    if heatpump_source_emissions is None:
        heatpump_source_emissions = grid_emissions

    spot_price_series = pd.Series(spot_price, dtype=float)
    battery_capacity = clean_zero(solution["battery_capacity_kwh"].iloc[0]) if "battery_capacity_kwh" in solution else BATTERY_TECHNICAL["capacity_kwh"]
    annual_import_kwh = float(solution["grid_import_kWh"].sum())
    annual_export_kwh = float(solution["grid_export_kWh"].sum())
    annual_grid_use_h = annual_import_grid_use_hours(annual_import_kwh, annual_export_kwh)
    power_tariff = power_tariff_rp_per_kw_per_month(annual_grid_use_h)
    annual_power_cost_rp = float(monthly_peak.astype(float).sum() * power_tariff)
    annual_battery_fixed_cost_rp = (BATTERY_ECONOMIC["annual_capex_rp_per_kwh_amortized"] + BATTERY_ECONOMIC["annual_opex_rp_per_kwh_year"]) * battery_capacity
    # RoR is charged a marginal cost per kWh produced (applies to full production series)
    runofriver_cost_per_kwh = RUNOFRIVER_ECONOMIC.get("cost_rp_per_kwh", 0.0)
    annual_runofriver_cost_rp = float(production_series.sum() * runofriver_cost_per_kwh)
    annual_battery_degradation_rp = float(
        battery_degradation_cost
        * (solution["battery_charge_kWh"].sum() + solution["battery_discharge_kWh"].sum())
    )
    annual_import_cost_rp = float(
        (
            solution["grid_import_kWh"]
            * import_price_rp_per_kwh(spot_price_series, annual_grid_use_h)
        ).sum()
    )
    annual_export_revenue_rp = float(
        (
            solution["grid_export_kWh"]
            * export_price_rp_per_kwh(spot_price_series, annual_grid_use_h)
        ).sum()
    )
    if "woodchip_boiler_heat_kWhth" in solution:
        annual_woodchip_heat_kwhth = float(solution["woodchip_boiler_heat_kWhth"].sum())
    else:
        annual_woodchip_heat_kwhth = 0.0
    if "heatpump_nominal_kWhth" in solution:
        annual_heatpump_nominal_kwhth = float(solution["heatpump_nominal_kWhth"].iloc[0])
    else:
        annual_heatpump_nominal_kwhth = 0.0
    if "heatpump_heat_kWhth" in solution:
        annual_heatpump_heat_kwhth = float(solution["heatpump_heat_kWhth"].sum())
    else:
        annual_heatpump_heat_kwhth = 0.0
    if "ptes_volume_m3" in solution:
        annual_ptes_volume_m3 = float(solution["ptes_volume_m3"].iloc[0])
    else:
        annual_ptes_volume_m3 = 0.0
    annual_woodchip_cost_rp = annual_woodchip_heat_kwhth * woodchip_cost_per_kwhth
    annual_heatpump_capex_rp = heatpump_total_cost_rp(annual_heatpump_nominal_kwhth)
    annual_heatpump_fixed_cost_rp = (
        annual_heatpump_capex_rp / heatpump_lifetime_years
        + annual_heatpump_capex_rp * heatpump_annual_opex_pct
    )
    
    # Compute PTES cost using the cost function (annualized over 30 years)
    def ptes_annual_cost_rp(volume):
        if volume <= 0:
            return 0.0
        coeff = PTES_ECONOMIC["specific_cost_chf_coeff"]
        exp = PTES_ECONOMIC["specific_cost_exp"]
        lifetime = PTES_ECONOMIC.get("lifetime_years", PTES_TECHNICAL.get("lifetime_years", 30))
        opex_pct = PTES_ECONOMIC.get("annual_opex_percentage_of_capex", 0.01)
        
        specific_cost_chf_per_m3 = coeff * (volume ** exp)
        total_capex_chf = specific_cost_chf_per_m3 * volume
        total_capex_rp = total_capex_chf * 100.0
        annual_capex_rp = total_capex_rp / lifetime
        annual_opex_rp = total_capex_rp * opex_pct
        return annual_capex_rp + annual_opex_rp
    
    annual_ptes_fixed_cost_rp = ptes_annual_cost_rp(annual_ptes_volume_m3)
    annual_heatpump_heat_series = pd.Series(solution["heatpump_heat_kWhth"], dtype=float) if "heatpump_heat_kWhth" in solution else pd.Series(0.0, dtype=float)
    if isinstance(heatpump_source_emissions, pd.Series):
        annual_heatpump_emissions_kgco2 = float(
            (annual_heatpump_heat_series * heatpump_emissions_per_kwhth
             + annual_heatpump_heat_series * heatpump_source_emissions / heatpump_cop_series).sum()
        )
    else:
        annual_heatpump_emissions_kgco2 = float(
            (annual_heatpump_heat_series * (
                heatpump_emissions_per_kwhth + float(heatpump_source_emissions) / heatpump_cop_series
            )).sum()
        )
    annual_ptes_emissions_kgco2 = annual_ptes_volume_m3 * ptes_emissions_per_m3
    annual_battery_throughput_kwh = float(
        solution["battery_charge_kWh"].sum() + solution["battery_discharge_kWh"].sum()
    )
    annual_battery_throughput_emissions_kgco2 = annual_battery_throughput_kwh * (
        BATTERY_EMISSIONS["lifecycle_emissions_kgco2_per_kwh_throughput"]
        + BATTERY_EMISSIONS.get("battery_throughput_penalty_emissions", 0.0)
    )
    annual_thermal_revenue_rp = float(pd.Series(heatdemand, dtype=float).sum()) * thermal_revenue_per_kwhth
    battery_installed = clean_binary(solution["battery_installed"].iloc[0]) if "battery_installed" in solution else 0.0
    ptes_installed = clean_binary(solution["ptes_installed"].iloc[0]) if "ptes_installed" in solution else 0.0
    
    # Calculate annual profit = revenues - costs (aligned with profit-maximization objective)
    annual_profit_rp = (
        + annual_export_revenue_rp         # export revenue
        + annual_thermal_revenue_rp        # heat sales revenue
        - annual_import_cost_rp            # grid import cost
        - annual_runofriver_cost_rp        # run-of-river production cost
        - annual_battery_degradation_rp    # battery cycling wear
        - annual_woodchip_cost_rp          # woodchip fuel cost
        - annual_power_cost_rp             # monthly power tariff
        - annual_battery_fixed_cost_rp     # battery amortized CAPEX/OPEX
        - annual_heatpump_fixed_cost_rp    # heat pump amortized CAPEX/OPEX
        - annual_ptes_fixed_cost_rp        # thermal storage amortized cost
    )
    net_annual_profit_chf = annual_profit_rp / 100.0
    annual_emissions_burden_kgco2 = float(
        annual_import_kwh * grid_emissions
        + annual_export_kwh * export_emissions
        + production_series.sum() * runofriver_emissions_per_kwh
        + annual_woodchip_heat_kwhth * woodchip_emissions_per_kwhth
        + annual_heatpump_emissions_kgco2
        + annual_ptes_emissions_kgco2
        + annual_battery_throughput_emissions_kgco2
    )

    return {
        "battery_installed": battery_installed,
        "ptes_installed": ptes_installed,
        "net_annual_profit_chf": net_annual_profit_chf,
        "annual_emissions_burden_kgco2": annual_emissions_burden_kgco2,
        "annual_grid_import_kwh": annual_import_kwh,
        "annual_grid_export_kwh": annual_export_kwh,
        "annual_grid_use_h": annual_grid_use_h,
        "annual_battery_charge_kwh": float(solution["battery_charge_kWh"].sum()),
        "annual_battery_discharge_kwh": float(solution["battery_discharge_kWh"].sum()),
        "annual_battery_throughput_emissions_kgco2": annual_battery_throughput_emissions_kgco2,
        "annual_woodchip_heat_kwhth": annual_woodchip_heat_kwhth,
        "annual_heatpump_heat_kwhth": annual_heatpump_heat_kwhth,
        "annual_heatpump_nominal_kwhth": annual_heatpump_nominal_kwhth,
        "annual_heatpump_fixed_cost_rp": annual_heatpump_fixed_cost_rp,
        "annual_ptes_volume_m3": annual_ptes_volume_m3,
        "annual_ptes_fixed_cost_rp": annual_ptes_fixed_cost_rp,
        "annual_thermal_revenue_chf": annual_thermal_revenue_rp / 100.0,
    }


def save_results(results, output_path, update_prefix=None):
    """Save results to CSV.

    If `update_prefix` is provided and the output file exists, only columns
    starting with that prefix will be replaced/added in the existing file
    (rows matched on `DateTime`). If the file does not exist, the full
    `results` DataFrame is written.
    """
    output_parent = Path(output_path).parent
    output_parent.mkdir(parents=True, exist_ok=True)

    # If no selective update requested or file doesn't exist, write normally
    out_path = Path(output_path)
    if update_prefix is None or not out_path.exists():
        results.to_csv(output_path, index=False)
        return

    # Merge: read existing file and replace only prefixed columns
    existing = pd.read_csv(output_path, parse_dates=["DateTime"]) if out_path.exists() else pd.DataFrame()
    if existing.empty:
        results.to_csv(output_path, index=False)
        return

    new = results.copy()
    # Ensure DateTime is present and parsed
    if "DateTime" not in existing.columns or "DateTime" not in new.columns:
        # Fallback: overwrite if DateTime missing
        results.to_csv(output_path, index=False)
        return

    existing["DateTime"] = pd.to_datetime(existing["DateTime"])
    new["DateTime"] = pd.to_datetime(new["DateTime"])

    existing = existing.set_index("DateTime")
    new = new.set_index("DateTime")

    cols_to_update = [c for c in new.columns if c.startswith(update_prefix)]
    if not cols_to_update:
        # Nothing to update; leave file as-is
        existing.reset_index().to_csv(output_path, index=False)
        return

    # Assign/update prefixed columns (alignment by DateTime index)
    for col in cols_to_update:
        existing[col] = new[col]

    # Ensure DateTime is first column when writing
    merged = existing.reset_index()
    # Keep original column order as much as possible: DateTime then existing cols
    merged.to_csv(output_path, index=False)


def print_summary(results, output_path):
    total_cost_costobj = results["cost_opt__step_cost_rp"].sum()
    total_cost_emisobj = results["emissions_opt__step_cost_rp"].sum()
    total_emis_costobj = results["cost_opt__step_emissions_kgco2"].sum()
    total_emis_emisobj = results["emissions_opt__step_emissions_kgco2"].sum()
    total_emis_costobj_tco2eq = total_emis_costobj / 1000.0
    total_emis_emisobj_tco2eq = total_emis_emisobj / 1000.0
    emissions_penalty = GENERAL["emissions_penalty"]
    net_profit_costobj_chf = -total_cost_costobj / 100.0
    net_profit_emisobj_chf = -total_cost_emisobj / 100.0
    cost_with_emission_penalty_costobj_chf = (
        net_profit_costobj_chf - (total_emis_costobj_tco2eq * emissions_penalty)
    )
    cost_with_emission_penalty_emisobj_chf = (
        net_profit_emisobj_chf - (total_emis_emisobj_tco2eq * emissions_penalty)
    )

    print("Optimization complete.")
    print(f"Rows solved (15-min intervals): {len(results)}")
    print(f"Output file: {output_path}")
    print("")
    print("Annual totals")
    print(f"Profit objective -> net annual profit [CHF]: {net_profit_costobj_chf:,.2f}")
    print(
        f"Profit objective -> annual emissions burden [tCO2eq]: {total_emis_costobj_tco2eq:,.2f}"
    )
    print(
        "Profit objective -> cost considering emission penalty [CHF]: "
        f"{cost_with_emission_penalty_costobj_chf:,.2f}"
    )
    print(f"Emissions objective -> net annual profit [CHF]: {net_profit_emisobj_chf:,.2f}")
    print(
        "Emissions objective -> annual emissions burden "
        f"[tCO2eq]: {total_emis_emisobj_tco2eq:,.2f}"
    )
    print(
        "Emissions objective -> profit considering emission penalty [CHF]: "
        f"{cost_with_emission_penalty_emisobj_chf:,.2f}"
    )
    # Annual self-sufficiency (fraction of load met without grid imports)
    if "cost_opt__annual_self_sufficiency_fraction" in results.columns:
        ss = results["cost_opt__annual_self_sufficiency_fraction"].iloc[0]
    else:
        # Fallback: compute from summed columns if present
        try:
            annual_import = results["cost_opt__grid_import_kWh"].sum()
            # Try reconstruct annual load using available columns
            production = results.get("production_kWh", pd.Series(0.0, index=results.index)).sum()
            batt_charge = results.get("cost_opt__battery_charge_kWh", pd.Series(0.0, index=results.index)).sum()
            batt_discharge = results.get("cost_opt__battery_discharge_kWh", pd.Series(0.0, index=results.index)).sum()
            annual_export = results.get("cost_opt__grid_export_kWh", pd.Series(0.0, index=results.index)).sum()
            heatpump_elec = results.get("cost_opt__heatpump_elec_kWh", pd.Series(0.0, index=results.index)).sum()
            annual_load = production + annual_import + batt_discharge - annual_export - batt_charge - heatpump_elec
            ss = 1.0 - (annual_import / annual_load) if annual_load > 0 else 1.0
        except Exception:
            ss = None
    if ss is not None:
        print(f"Annual self-sufficiency (no-grid fraction): {ss*100:.2f}%")
