import gurobipy as gp
from gurobipy import GRB

from parameters.battery import BATTERY_ECONOMIC
from parameters.grid_import import IMPORT_EMISSIONS
from parameters.grid_export import EXPORT_EMISSIONS


def add_objective(model, vars_dict, spot_price_rp_per_kwh, objective_mode, n):
    grid_import = vars_dict["grid_import"]
    grid_export = vars_dict["grid_export"]
    batt_charge = vars_dict["batt_charge"]
    batt_discharge = vars_dict["batt_discharge"]

    throughput_cost = BATTERY_ECONOMIC["throughput_cost_rp_per_kwh"]
    grid_emissions = IMPORT_EMISSIONS["grid_emissions_kgco2_per_kwh"]
    export_credit = EXPORT_EMISSIONS["export_emissions_credit_kgco2_per_kwh"]

    if objective_mode == "cost":
        expr = gp.quicksum(
            grid_import[t] * spot_price_rp_per_kwh[t]
            - grid_export[t] * spot_price_rp_per_kwh[t]
            + throughput_cost * (batt_charge[t] + batt_discharge[t])
            for t in range(n)
        )
    elif objective_mode == "emissions":
        expr = gp.quicksum(
            grid_import[t] * grid_emissions
            - grid_export[t] * export_credit
            for t in range(n)
        )
    else:
        raise ValueError(f"Unknown objective_mode: {objective_mode}")

    model.setObjective(expr, GRB.MINIMIZE)