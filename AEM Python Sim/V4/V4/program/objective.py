import gurobipy as gp
from gurobipy import GRB

from parameters.battery import BATTERY_ECONOMIC, BATTERY_TECHNICAL
from parameters.grid_import import IMPORT_ECONOMIC, IMPORT_EMISSIONS
from parameters.general import GENERAL
from parameters.grid_export import EXPORT_ECONOMIC, EXPORT_EMISSIONS, EXPORT_TECHNICAL
from parameters.heat_pump import (
    HEAT_PUMP_ECONOMIC,
    HEAT_PUMP_EMISSIONS,
    generate_heatpump_cost_breakpoints,
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
    v_breakpoints = [0.1, 10, 50, 100, 200, 500, 1000, 2000, 5000]
    
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


def add_heatpump_cost_constraint(model, heatpump_nominal, heatpump_cost_var):
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
        heatpump_nominal == gp.quicksum(weights[i] * q_breakpoints[i] for i in range(len(q_breakpoints))),
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


def build_annual_emissions_expr(vars_dict, production_kwh, n):
    grid_import = vars_dict["grid_import"]
    grid_export = vars_dict["grid_export"]
    woodchip_heat = vars_dict["woodchip_boiler_heat_kWhth"]
    ptes_volume = vars_dict["ptes_volume_m3"]
    grid_emissions = IMPORT_EMISSIONS["grid_emissions_kgco2_per_kwh"]
    export_emissions = EXPORT_EMISSIONS["export_emissions_kgco2_per_kwh"]
    runofriver_emissions_per_kwh = RUNOFRIVER_EMISSIONS["emissions_kgco2eq_per_kwh_generated"]
    woodchip_emissions_per_kwhth = WOODCHIP_BOILER_EMISSIONS["emissions_kgco2eq_per_kwhth"]
    ptes_emissions_per_m3 = PTES_EMISSIONS["emissions_kgco2eq_per_m3"]

    return gp.quicksum(
        grid_import[t] * grid_emissions
        + grid_export[t] * export_emissions
        + production_kwh[t] * runofriver_emissions_per_kwh
        + woodchip_heat[t] * woodchip_emissions_per_kwhth
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
):
    grid_import = vars_dict["grid_import"]
    grid_export = vars_dict["grid_export"]
    woodchip_heat = vars_dict["woodchip_boiler_heat_kWhth"]
    heatpump_heat = vars_dict["heatpump_heat_kWhth"]
    heatpump_nominal = vars_dict["heatpump_nominal_kWhth"]
    ptes_volume = vars_dict["ptes_volume_m3"]
    batt_charge = vars_dict["batt_charge"]
    batt_discharge = vars_dict["batt_discharge"]
    battery_installed = vars_dict["battery_installed"]
    monthly_peak_kw = vars_dict["monthly_peak_kw"]
    unique_month_labels = vars_dict["unique_month_labels"]

    battery_capacity_kwh = BATTERY_TECHNICAL["capacity_kwh"]
    battery_capex = BATTERY_ECONOMIC["annual_capex_rp_per_kwh_amortized"] * battery_capacity_kwh
    battery_annual_opex = (
        BATTERY_ECONOMIC["annual_opex_rp_per_kwh_year"] * battery_capacity_kwh
    )
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
    import_high_use_tariff = IMPORT_ECONOMIC["fixed_tariff_high_grid_use_rp_per_kwh"]
    import_low_use_tariff = IMPORT_ECONOMIC["fixed_tariff_low_grid_use_rp_per_kwh"]
    export_high_use_tariff = EXPORT_ECONOMIC["fixed_tariff_high_grid_use_rp_per_kwh"]
    export_low_use_tariff = EXPORT_ECONOMIC["fixed_tariff_low_grid_use_rp_per_kwh"]
    power_tariff_high_use = IMPORT_ECONOMIC["power_tariff_high_grid_use_rp_per_kw_per_month"]
    power_tariff_low_use = IMPORT_ECONOMIC["power_tariff_low_grid_use_rp_per_kw_per_month"]
    annual_grid_use_threshold_kwh = (
        EXPORT_ECONOMIC["annual_grid_use_threshold_h"]
        * EXPORT_TECHNICAL["existing_grid_limit_mw"]
        * 1000.0
    )
    annual_grid_use_upper_bound_kwh = (
        2.0
        * n
        * EXPORT_TECHNICAL["existing_grid_limit_mw"]
        * 1000.0
        * GENERAL["delta_t_h"]
    )

    if objective_mode == "cost":
        ptes_cost_var = model.addVar(lb=0.0, vtype=GRB.CONTINUOUS, name="ptes_annual_cost_rp")
        add_ptes_cost_constraint(model, ptes_volume, ptes_cost_var)

        # Add piecewise linear heat pump cost (amortized annual CAPEX)
        heatpump_capex_var = model.addVar(lb=0.0, vtype=GRB.CONTINUOUS, name="heatpump_annual_capex_rp")
        add_heatpump_cost_constraint(model, heatpump_nominal, heatpump_capex_var)
        
        # Amortize the CAPEX over the heat pump lifetime
        heatpump_lifetime_years = HEAT_PUMP_ECONOMIC["heatpump_lifetime_years"]
        heatpump_annual_capex_amortized = heatpump_capex_var / heatpump_lifetime_years

        annual_grid_use_kwh = gp.quicksum(
            grid_import[t] + grid_export[t] for t in range(n)
        )
        annual_export_kwh = gp.quicksum(grid_export[t] for t in range(n))
        export_low_grid_use = model.addVar(
            vtype=GRB.BINARY, name="export_low_grid_use_tariff_active"
        )
        model.addConstr(
            annual_grid_use_kwh
            <= annual_grid_use_threshold_kwh
            + annual_grid_use_upper_bound_kwh * (1 - export_low_grid_use),
            name="export_low_grid_use_upper_bound",
        )
        model.addConstr(
            annual_grid_use_kwh
            >= annual_grid_use_threshold_kwh
            - annual_grid_use_upper_bound_kwh * export_low_grid_use,
            name="export_low_grid_use_lower_bound",
        )

        prod_for_local = vars_dict["prod_for_local_demand"]
        local_production_revenue = gp.quicksum(
            prod_for_local[t] * runofriver_profit_per_kwh
            for t in range(n)
        )
        export_revenue = gp.quicksum(
            grid_export[t] * (spot_price_rp_per_kwh[t] - export_high_use_tariff)
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
            grid_import[t] * (spot_price_rp_per_kwh[t] + import_high_use_tariff)
            for t in range(n)
        )
        battery_cycling_cost = gp.quicksum(
            battery_degradation_cost * (batt_charge[t] + batt_discharge[t])
            for t in range(n)
        )
        woodchip_cost = gp.quicksum(
            woodchip_heat[t] * woodchip_cost_per_kwhth for t in range(n)
        )
        tariff_adjustment_cost = (
            (import_low_use_tariff - import_high_use_tariff) * export_low_grid_use * annual_grid_use_kwh
            + (export_low_use_tariff - export_high_use_tariff - (import_low_use_tariff - import_high_use_tariff))
            * export_low_grid_use * annual_export_kwh
        )
        power_tariff_cost = (
            power_tariff_high_use
            + (power_tariff_low_use - power_tariff_high_use) * export_low_grid_use
        ) * gp.quicksum(
            monthly_peak_kw[month_label] for month_label in unique_month_labels
        )
        battery_fixed_cost = battery_installed * (battery_capex + battery_annual_opex)
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
            + tariff_adjustment_cost
            + power_tariff_cost
            + battery_fixed_cost
            + heatpump_fixed_cost
            + ptes_storage_cost
        )

        annual_profit = annual_revenues - annual_costs
        model.setObjective(annual_profit, GRB.MAXIMIZE)
    elif objective_mode == "emissions":
        expr = build_annual_emissions_expr(vars_dict, production_kwh, n) + gp.quicksum(
            heatpump_heat[t] * heatpump_emissions_per_kwhth for t in range(n)
        )
        model.setObjective(expr, GRB.MINIMIZE)
    else:
        raise ValueError(f"Unknown objective_mode: {objective_mode}")
