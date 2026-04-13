import gurobipy as gp
from gurobipy import GRB
import pandas as pd

from constraints.battery import add_battery_constraints
from constraints.energy_balance import add_energy_balance_constraints
from objective import add_objective, build_annual_emissions_expr
from parameters.general import GENERAL
from variables import add_variables


def build_model(
    production_kwh,
    demand_kwh,
    spot_price_rp_per_kwh,
    datetime_series,
    objective_mode,
    init_soc_kwh,
    final_soc_kwh,
    emissions_cap_kgco2=None,
):
    n = len(demand_kwh)

    model = gp.Model(GENERAL["solver_name"])
    model.Params.OutputFlag = GENERAL["gurobi_output_flag"]

    vars_dict = add_variables(model, n)
    month_labels = pd.to_datetime(datetime_series).dt.to_period("M").astype(str).tolist()
    unique_month_labels = list(dict.fromkeys(month_labels))
    vars_dict["monthly_peak_kw"] = model.addVars(
        unique_month_labels, lb=0.0, vtype=GRB.CONTINUOUS, name="monthly_peak_kw"
    )
    vars_dict["month_labels"] = month_labels
    vars_dict["unique_month_labels"] = unique_month_labels

    add_energy_balance_constraints(
        model=model,
        vars_dict=vars_dict,
        production_kwh=production_kwh,
        demand_kwh=demand_kwh,
        n=n,
    )

    add_battery_constraints(
        model=model,
        vars_dict=vars_dict,
        n=n,
        init_soc_kwh=init_soc_kwh,
        final_soc_kwh=final_soc_kwh,
    )

    annual_emissions_expr = build_annual_emissions_expr(
        vars_dict=vars_dict,
        production_kwh=production_kwh,
        n=n,
    )
    vars_dict["annual_emissions_expr"] = annual_emissions_expr

    if emissions_cap_kgco2 is not None:
        model.addConstr(
            annual_emissions_expr <= emissions_cap_kgco2,
            name="annual_emissions_cap",
        )

    add_objective(
        model=model,
        vars_dict=vars_dict,
        production_kwh=production_kwh,
        spot_price_rp_per_kwh=spot_price_rp_per_kwh,
        objective_mode=objective_mode,
        n=n,
    )

    delta_t_h = GENERAL["delta_t_h"]
    for t, month_label in enumerate(month_labels):
        model.addConstr(
            vars_dict["monthly_peak_kw"][month_label] >= vars_dict["grid_import"][t] / delta_t_h,
            name=f"monthly_import_peak[{t}]",
        )
        model.addConstr(
            vars_dict["monthly_peak_kw"][month_label] >= vars_dict["grid_export"][t] / delta_t_h,
            name=f"monthly_export_peak[{t}]",
        )

    model.update()
    return model, vars_dict


def solve_model(model, objective_mode="unknown"):
    model.optimize()

    if model.Status != GRB.OPTIMAL:
        raise RuntimeError(
            f"No optimal solution for {objective_mode}. Gurobi status code: {model.Status}"
        )

    return model
