import gurobipy as gp
from gurobipy import GRB

from constraints.battery import add_battery_constraints
from constraints.energy_balance import add_energy_balance_constraints
from objective import add_objective
from parameters.general import GENERAL
from variables import add_variables


def build_model(
    production_kwh,
    demand_kwh,
    spot_price_rp_per_kwh,
    objective_mode,
    init_soc_kwh,
    final_soc_kwh,
):
    n = len(demand_kwh)

    model = gp.Model(GENERAL["solver_name"])
    model.Params.OutputFlag = GENERAL["gurobi_output_flag"]

    vars_dict = add_variables(model, n)

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

    add_objective(
        model=model,
        vars_dict=vars_dict,
        spot_price_rp_per_kwh=spot_price_rp_per_kwh,
        objective_mode=objective_mode,
        n=n,
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