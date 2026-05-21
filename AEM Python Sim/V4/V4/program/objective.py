import gurobipy as gp
from gurobipy import GRB
import pandas as pd

from parameters.battery import BATTERY_ECONOMIC, BATTERY_EMISSIONS, BATTERY_TECHNICAL
from parameters.grid_import import IMPORT_ECONOMIC, IMPORT_EMISSIONS
from parameters.general import GENERAL
from parameters.grid_export import EXPORT_ECONOMIC, EXPORT_EMISSIONS, EXPORT_TECHNICAL
from parameters.heat_pump import (
    HEAT_PUMP_ECONOMIC,
    HEAT_PUMP_EMISSIONS,
    HEAT_PUMP_TECHNICAL,
    generate_heatpump_cost_breakpoints,
    heatpump_cop_profile,
    heatpump_total_emissions_kgco2,
)
from parameters.runofriver import RUNOFRIVER_ECONOMIC, RUNOFRIVER_EMISSIONS
from parameters.woodchip_boiler import WOODCHIP_BOILER_ECONOMIC, WOODCHIP_BOILER_EMISSIONS
from parameters.ptes import PTES_TECHNICAL, PTES_ECONOMIC, PTES_EMISSIONS


def add_ptes_cost_constraint(model, ptes_volume, ptes_cost_var):
    """
    Add piecewise linear constraint for PTES cost function.
    Cost = (838668.4 * V^(-0.424)) / 30 [rappen/year]
    
    Uses SOS2 (Special Ordered Set type 2) for piecewise linear interpolation.
    """
    # Volume breakpoints (m³)
    v_breakpoints = [0.0, 0.1, 10, 50, 100, 200, 500, 1000, 2000, 5000]
    
    # Compute corresponding costs (rappen/year, annualized)
    def ptes_annual_cost_rp(v):
        if v <= 0:
            return 0
        # Specific cost in CHF per m^3: coeff * V^exp
        coeff = PTES_ECONOMIC.get("specific_cost_chf_coeff")
        exp = PTES_ECONOMIC.get("specific_cost_exp")
        lifetime = PTES_ECONOMIC.get("lifetime_years", PTES_TECHNICAL.get("lifetime_years", 30))
        opex_pct = PTES_ECONOMIC.get("annual_opex_percentage_of_capex", 0.01)

        specific_cost_chf_per_m3 = coeff * (v ** exp)
        # Total CAPEX in CHF = specific_cost_chf_per_m3 * V
        total_capex_chf = specific_cost_chf_per_m3 * v
        # Convert CHF -> rappen
        total_capex_rp = total_capex_chf * 100.0
        # Annualized CAPEX (rappen/year)
        annual_capex_rp = total_capex_rp / lifetime
        # Annual OPEX based on percentage of total CAPEX (rappen/year)
        annual_opex_rp = total_capex_rp * opex_pct

        return annual_capex_rp + annual_opex_rp
    
    costs = [ptes_annual_cost_rp(v) for v in v_breakpoints]
    
    # Create weight variables for piecewise linear interpolation
    weights = model.addVars(len(v_breakpoints), lb=0, ub=1, vtype=GRB.CONTINUOUS, name="ptes_cost_weights")
    
    # Constraint: volume is linear combination of breakpoints
    model.addConstr(
        ptes_volume == gp.quicksum(weights[i] * v_breakpoints[i] for i in range(len(v_breakpoints))),
        name="ptes_volume_interp"
    )
    
    # Constraint: cost is linear combination of costs at breakpoints
    model.addConstr(
        ptes_cost_var == gp.quicksum(weights[i] * costs[i] for i in range(len(v_breakpoints))),
        name="ptes_cost_interp"
    )
    
    # SOS2 constraint: at most two adjacent weights can be non-zero (enforces piecewise linear interpolation)
    model.addSOS(GRB.SOS_TYPE2, [weights[i] for i in range(len(v_breakpoints))])
    
    # Constraint: weights sum to 1
    model.addConstr(
        gp.quicksum(weights) == 1,
        name="ptes_weights_sum"
    )


def add_heatpump_cost_constraint(model, heatpump_nominal_kwth, heatpump_cost_var):
    """
    Add piecewise linear constraint for heat pump nonlinear cost function.
    Cost [rappen] = 1100 * (Q_nominal / 100)^(-0.46) * 100 * Q_nominal
    
    Uses SOS2 (Special Ordered Set type 2) for piecewise linear interpolation.
    Automatically generates breakpoints from the power-law function.
    """
    # Generate breakpoints from the nonlinear cost function
    q_breakpoints, cost_breakpoints = generate_heatpump_cost_breakpoints()
    
    # Create weight variables for piecewise linear interpolation
    weights = model.addVars(
        len(q_breakpoints),
        lb=0,
        ub=1,
        vtype=GRB.CONTINUOUS,
        name="heatpump_cost_weights"
    )
    
    # Constraint: Q_nominal is linear combination of breakpoints
    model.addConstr(
        heatpump_nominal_kwth == gp.quicksum(weights[i] * q_breakpoints[i] for i in range(len(q_breakpoints))),
        name="heatpump_nominal_interp"
    )
    
    # Constraint: cost is linear combination of costs at breakpoints
    model.addConstr(
        heatpump_cost_var == gp.quicksum(weights[i] * cost_breakpoints[i] for i in range(len(cost_breakpoints))),
        name="heatpump_cost_interp"
    )
    
    # SOS2 constraint: at most two adjacent weights can be non-zero (enforces piecewise linear interpolation)
    model.addSOS(GRB.SOS_TYPE2, [weights[i] for i in range(len(q_breakpoints))])
    
    # Constraint: weights sum to 1
    model.addConstr(
        gp.quicksum(weights) == 1,
        name="heatpump_weights_sum"
    )


def build_annual_emissions_expr(vars_dict, production_kwh, n, datetime_series=None):
    grid_import = vars_dict["grid_import"]
    grid_export = vars_dict["grid_export"]
    batt_charge = vars_dict["batt_charge"]
    batt_discharge = vars_dict["batt_discharge"]
    woodchip_heat = vars_dict["woodchip_boiler_heat_kWhth"]
    ptes_volume = vars_dict["ptes_volume_m3"]
    grid_emissions = IMPORT_EMISSIONS["grid_emissions_kgco2_per_kwh"]
    export_emissions = EXPORT_EMISSIONS["export_emissions_kgco2_per_kwh"]
    battery_lifecycle_emissions = BATTERY_EMISSIONS[
        "lifecycle_emissions_kgco2_per_kwh_throughput"
    ]
    battery_throughput_penalty = BATTERY_EMISSIONS.get(
        "battery_throughput_penalty_emissions", 0.0
    )
    battery_throughput_emissions = (
        battery_lifecycle_emissions + battery_throughput_penalty
    )
    runofriver_emissions_per_kwh = RUNOFRIVER_EMISSIONS["emissions_kgco2eq_per_kwh_generated"]
    woodchip_emissions_per_kwhth = WOODCHIP_BOILER_EMISSIONS["emissions_kgco2eq_per_kwhth"]
    ptes_emissions_per_m3 = PTES_EMISSIONS["emissions_kgco2eq_per_m3"]
    heatpump_heat = vars_dict["heatpump_heat_kWhth"]

    electricity_source_emissions = HEAT_PUMP_EMISSIONS.get(
        "electricity_source_emissions_kgco2_per_kwh"
    )
    if electricity_source_emissions is None:
        electricity_source_emissions = grid_emissions

    cop_profile = heatpump_cop_profile(datetime_series) if datetime_series is not None else [HEAT_PUMP_TECHNICAL["cop_monthly"][0]] * n

    return gp.quicksum(
        grid_import[t] * grid_emissions
        + grid_export[t] * export_emissions
        + (batt_charge[t] + batt_discharge[t]) * battery_throughput_emissions
        + production_kwh[t] * runofriver_emissions_per_kwh
        + woodchip_heat[t] * woodchip_emissions_per_kwhth
        + heatpump_total_emissions_kgco2(
            heatpump_heat[t],
            cop_profile[t],
            direct_factor=HEAT_PUMP_EMISSIONS["emissions_kgco2eq_per_kwhth"],
            electricity_source_factor=electricity_source_emissions,
        )
        for t in range(n)
    ) + ptes_volume * ptes_emissions_per_m3  # Annual PTES embodied emissions



def add_objective(
    model,
    vars_dict,
    production_kwh,
    heatdemand_kwhth,
    spot_price_rp_per_kwh,
    objective_mode,
    n,
    datetime_series=None,
):
    grid_import = vars_dict["grid_import"]
    grid_export = vars_dict["grid_export"]
    woodchip_heat = vars_dict["woodchip_boiler_heat_kWhth"]
    heatpump_heat = vars_dict["heatpump_heat_kWhth"]
    heatpump_nominal_kwth = vars_dict["heatpump_nominal_kwth"]
    ptes_volume = vars_dict["ptes_volume_m3"]
    batt_charge = vars_dict["batt_charge"]
    batt_discharge = vars_dict["batt_discharge"]
    battery_installed = vars_dict["battery_installed"]
    monthly_peak_kw = vars_dict["monthly_peak_kw"]
    unique_month_labels = vars_dict["unique_month_labels"]

    # Use the sizing variable for battery capacity when computing fixed costs
    battery_capacity_var = vars_dict.get("battery_capacity_kwh")
    per_kwh_capex = BATTERY_ECONOMIC["annual_capex_rp_per_kwh_amortized"]
    per_kwh_opex = BATTERY_ECONOMIC["annual_opex_rp_per_kwh_year"]
    battery_capex = per_kwh_capex
    battery_annual_opex = per_kwh_opex
    battery_degradation_cost = BATTERY_ECONOMIC["degradation_cost_rp_per_kwh_throughput"]
    grid_emissions = IMPORT_EMISSIONS["grid_emissions_kgco2_per_kwh"]
    export_emissions = EXPORT_EMISSIONS["export_emissions_kgco2_per_kwh"]
    runofriver_profit_per_kwh = RUNOFRIVER_ECONOMIC["profit_rp_per_kwh"]
    runofriver_emissions_per_kwh = RUNOFRIVER_EMISSIONS["emissions_kgco2eq_per_kwh_generated"]
    woodchip_cost_per_kwhth = WOODCHIP_BOILER_ECONOMIC["cost_rp_per_kwhth_useful"]
    thermal_revenue_per_kwhth = WOODCHIP_BOILER_ECONOMIC["revenue_rp_per_kwhth_sold"]
    heatpump_lifetime_years = HEAT_PUMP_ECONOMIC["heatpump_lifetime_years"]
    heatpump_opex_percentage = HEAT_PUMP_ECONOMIC["annual_opex_percentage_of_capex"]
    heatpump_emissions_per_kwhth = HEAT_PUMP_EMISSIONS["emissions_kgco2eq_per_kwhth"]
    heatpump_electricity_source_emissions = HEAT_PUMP_EMISSIONS.get(
        "electricity_source_emissions_kgco2_per_kwh"
    )
    if heatpump_electricity_source_emissions is None:
        heatpump_electricity_source_emissions = grid_emissions
    cop_profile = heatpump_cop_profile(datetime_series) if datetime_series is not None else [HEAT_PUMP_TECHNICAL["cop_monthly"][0]] * n
    import_fixed_tariff = IMPORT_ECONOMIC["fixed_tariff_high_grid_use_rp_per_kwh"]
    export_fixed_tariff = EXPORT_ECONOMIC["fixed_tariff_high_grid_use_rp_per_kwh"]
    import_power_tariff = IMPORT_ECONOMIC["power_tariff_high_grid_use_rp_per_kw_per_month"]
    export_power_tariff = EXPORT_ECONOMIC["power_tariff_high_grid_use_rp_per_kw_per_month"]

    # Build techno-economic cost framework for both modes so emissions runs
    # remain techno-emissions optimizations with full cost accounting active.
    ptes_cost_var = model.addVar(lb=0.0, vtype=GRB.CONTINUOUS, name="ptes_annual_cost_rp")
    add_ptes_cost_constraint(model, ptes_volume, ptes_cost_var)

    # Small throughput penalty to discourage excessive PTES cycling
    ptes_throughput_penalty = PTES_ECONOMIC.get("throughput_penalty_rp_per_kwh", 0.0)
    ptes_throughput_cost = gp.quicksum(
        ptes_throughput_penalty * (vars_dict["ptes_charge_kWhth"][t] + vars_dict["ptes_discharge_kWhth"][t])
        for t in range(n)
    )

    # Add piecewise linear heat pump cost for nominal thermal power
    heatpump_capex_var = model.addVar(lb=0.0, vtype=GRB.CONTINUOUS, name="heatpump_annual_capex_rp")
    add_heatpump_cost_constraint(model, heatpump_nominal_kwth, heatpump_capex_var)

    # Amortize the CAPEX over the heat pump lifetime
    heatpump_annual_capex_amortized = heatpump_capex_var / heatpump_lifetime_years

    prod_for_local = vars_dict["prod_for_local_demand"]
    local_production_revenue = gp.quicksum(
        prod_for_local[t] * runofriver_profit_per_kwh
        for t in range(n)
    )
    export_revenue = gp.quicksum(
        grid_export[t] * (spot_price_rp_per_kwh[t] - export_fixed_tariff)
        for t in range(n)
    )
    thermal_revenue = gp.quicksum(
        heatdemand_kwhth[t] * thermal_revenue_per_kwhth for t in range(n)
    )
    annual_revenues = (
        local_production_revenue
        + export_revenue
        + thermal_revenue
    )

    grid_import_cost = gp.quicksum(
        grid_import[t] * (spot_price_rp_per_kwh[t] + import_fixed_tariff)
        for t in range(n)
    )
    battery_cycling_cost = gp.quicksum(
        battery_degradation_cost * (batt_charge[t] + batt_discharge[t])
        for t in range(n)
    )
    woodchip_cost = gp.quicksum(
        woodchip_heat[t] * woodchip_cost_per_kwhth for t in range(n)
    )
    power_tariff_cost = export_power_tariff * gp.quicksum(
        monthly_peak_kw[month_label] for month_label in unique_month_labels
    )
    # Battery fixed cost scales linearly with chosen capacity (kWh)
    if battery_capacity_var is not None:
        battery_fixed_cost = battery_capacity_var * (battery_capex + battery_annual_opex)
    else:
        # Fallback to previous behavior using installed flag and nominal capacity
        battery_capacity_kwh = BATTERY_TECHNICAL["capacity_kwh"]
        battery_fixed_cost = battery_installed * (
            battery_capex * battery_capacity_kwh + battery_annual_opex * battery_capacity_kwh
        )
    # Heat pump costs from piecewise linear CAPEX approximation
    # OPEX is calculated as a percentage of the variable CAPEX
    heatpump_opex_cost = heatpump_capex_var * heatpump_opex_percentage
    heatpump_fixed_cost = (
        heatpump_annual_capex_amortized
        + heatpump_opex_cost
    )
    ptes_storage_cost = ptes_cost_var

    annual_costs = (
        grid_import_cost
        + battery_cycling_cost
        + woodchip_cost
        + power_tariff_cost
        + battery_fixed_cost
        + heatpump_fixed_cost
        + ptes_storage_cost
        + ptes_throughput_cost
    )

    annual_profit = annual_revenues - annual_costs

    if objective_mode == "cost":
        model.setObjective(annual_profit, GRB.MAXIMIZE)
    elif objective_mode == "emissions":
        expr = build_annual_emissions_expr(
            vars_dict,
            production_kwh,
            n,
            datetime_series=datetime_series,
        )
        model.setObjective(expr, GRB.MINIMIZE)
    else:
        raise ValueError(f"Unknown objective_mode: {objective_mode}")
