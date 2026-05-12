import gurobipy as gp
from gurobipy import GRB

from parameters.battery import BATTERY_ECONOMIC, BATTERY_TECHNICAL
from parameters.grid_import import IMPORT_ECONOMIC, IMPORT_EMISSIONS
from parameters.general import GENERAL
from parameters.grid_export import EXPORT_ECONOMIC, EXPORT_EMISSIONS, EXPORT_TECHNICAL
from parameters.heat_pump import HEAT_PUMP_ECONOMIC, HEAT_PUMP_EMISSIONS
from parameters.runofriver import RUNOFRIVER_ECONOMIC, RUNOFRIVER_EMISSIONS
from parameters.woodchip_boiler import WOODCHIP_BOILER_ECONOMIC, WOODCHIP_BOILER_EMISSIONS


def build_annual_emissions_expr(vars_dict, production_kwh, n):
    grid_import = vars_dict["grid_import"]
    grid_export = vars_dict["grid_export"]
    woodchip_heat = vars_dict["woodchip_boiler_heat_kWhth"]
    grid_emissions = IMPORT_EMISSIONS["grid_emissions_kgco2_per_kwh"]
    export_emissions = EXPORT_EMISSIONS["export_emissions_kgco2_per_kwh"]
    runofriver_emissions_per_kwh = RUNOFRIVER_EMISSIONS["emissions_kgco2eq_per_kwh_generated"]
    woodchip_emissions_per_kwhth = WOODCHIP_BOILER_EMISSIONS["emissions_kgco2eq_per_kwhth"]

    return gp.quicksum(
        grid_import[t] * grid_emissions
        + grid_export[t] * export_emissions
        + production_kwh[t] * runofriver_emissions_per_kwh
        + woodchip_heat[t] * woodchip_emissions_per_kwhth
        for t in range(n)
    )


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
    heatpump_cost_rp_per_kwth = HEAT_PUMP_ECONOMIC["cost_rp_per_kwth_nominal"]
    heatpump_cost_rp_fixed = HEAT_PUMP_ECONOMIC["cost_rp_fixed"]
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

    if objective_mode == "cost": # - : profit , + = cost
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
        
        # Production revenue split:
        # - prod_for_local_demand[t] gets runofriver_profit_per_kwh
        # - Excess production (production[t] - prod_for_local_demand[t]) gets export revenue
        prod_for_local = vars_dict["prod_for_local_demand"]
        production_revenue = gp.quicksum(
            prod_for_local[t] * runofriver_profit_per_kwh
            + (production_kwh[t] - prod_for_local[t]) * (spot_price_rp_per_kwh[t] - export_high_use_tariff)
            for t in range(n)
        )
        woodchip_net_cost = gp.quicksum(
            woodchip_heat[t] * woodchip_cost_per_kwhth for t in range(n)
        )
        thermal_revenue = gp.quicksum(
            heatdemand_kwhth[t] * thermal_revenue_per_kwhth for t in range(n)
        )
        heatpump_fixed_cost_rp = (
            heatpump_cost_rp_per_kwth * heatpump_nominal + heatpump_cost_rp_fixed
        )
        
        expr = gp.quicksum(
            grid_import[t] * (spot_price_rp_per_kwh[t] + import_high_use_tariff)
            - grid_export[t] * (spot_price_rp_per_kwh[t] - export_high_use_tariff)
            + battery_degradation_cost * (batt_charge[t] + batt_discharge[t])
            for t in range(n)
        ) + (import_low_use_tariff - import_high_use_tariff) * export_low_grid_use * annual_grid_use_kwh + (
            export_low_use_tariff - export_high_use_tariff - (import_low_use_tariff - import_high_use_tariff)
        ) * export_low_grid_use * annual_export_kwh + (
            power_tariff_high_use
            + (power_tariff_low_use - power_tariff_high_use) * export_low_grid_use
        ) * gp.quicksum(
            monthly_peak_kw[month_label] for month_label in unique_month_labels
        ) + battery_installed * (battery_capex + battery_annual_opex) + heatpump_fixed_cost_rp - production_revenue + woodchip_net_cost - thermal_revenue
    elif objective_mode == "emissions":
        expr = build_annual_emissions_expr(vars_dict, production_kwh, n) + gp.quicksum(
            heatpump_heat[t] * heatpump_emissions_per_kwhth for t in range(n)
        )
    else:
        raise ValueError(f"Unknown objective_mode: {objective_mode}")

    model.setObjective(expr, GRB.MINIMIZE)
