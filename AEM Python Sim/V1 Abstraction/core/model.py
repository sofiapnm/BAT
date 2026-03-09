import pandas as pd
from pyomo.environ import (
    ConcreteModel,
    TerminationCondition,
    value,
)

from core.constraints import ConstraintBlock
from core.objective import ObjectiveBlock
from core.solver import GurobiSizeLimitError, ModelSolver
from core.variables import VariableBlock


def build_model(
    production_kwh,
    demand_kwh,
    spot_price_rp_per_kwh,
    objective_mode,
    init_soc_kwh,
    final_soc_kwh,
    battery_cfg,
    grid_cfg,
):
    model = ConcreteModel()
    VariableBlock(battery_cfg).attach(
        model,
        production_kwh=production_kwh,
        demand_kwh=demand_kwh,
        spot_price_rp_per_kwh=spot_price_rp_per_kwh,
    )
    ConstraintBlock(
        battery_cfg=battery_cfg,
        init_soc_kwh=init_soc_kwh,
        final_soc_kwh=final_soc_kwh,
    ).attach(model)
    ObjectiveBlock(
        objective_mode=objective_mode,
        battery_cfg=battery_cfg,
        grid_cfg=grid_cfg,
    ).attach(model)
    return model


def build_and_solve(
    production_kwh,
    demand_kwh,
    spot_price_rp_per_kwh,
    objective_mode,
    init_soc_kwh,
    final_soc_kwh,
    battery_cfg,
    grid_cfg,
    solver_cfg,
):
    model = build_model(
        production_kwh=production_kwh,
        demand_kwh=demand_kwh,
        spot_price_rp_per_kwh=spot_price_rp_per_kwh,
        objective_mode=objective_mode,
        init_soc_kwh=init_soc_kwh,
        final_soc_kwh=final_soc_kwh,
        battery_cfg=battery_cfg,
        grid_cfg=grid_cfg,
    )
    results, solver_used = ModelSolver(solver_cfg).solve(model)

    if results.solver.termination_condition != TerminationCondition.optimal:
        raise RuntimeError(
            f"No optimal solution for {objective_mode}. Condition: {results.solver.termination_condition}"
        )

    n = len(demand_kwh)
    out = pd.DataFrame(
        {
            "grid_import_kWh": [value(model.grid_import[t]) for t in range(n)],
            "grid_export_kWh": [value(model.grid_export[t]) for t in range(n)],
            "battery_charge_kWh": [value(model.batt_charge[t]) for t in range(n)],
            "battery_discharge_kWh": [value(model.batt_discharge[t]) for t in range(n)],
            "battery_soc_kWh": [value(model.soc[t]) for t in range(n)],
        }
    )
    return out, solver_used


def solve_in_windows(
    production,
    demand,
    spot_price,
    objective_mode,
    battery_cfg,
    grid_cfg,
    solver_cfg,
    window_steps=192,
):
    if window_steps <= 1:
        raise ValueError("window_steps must be > 1.")

    n = len(demand)
    chunks = []
    solvers_used = set()
    soc_now = battery_cfg.soc_init_kwh

    for start in range(0, n, window_steps):
        stop = min(start + window_steps, n)
        is_last = stop == n
        final_soc = battery_cfg.soc_end_kwh if is_last else None

        chunk, solver_used = build_and_solve(
            production_kwh=production[start:stop],
            demand_kwh=demand[start:stop],
            spot_price_rp_per_kwh=spot_price[start:stop],
            objective_mode=objective_mode,
            init_soc_kwh=soc_now,
            final_soc_kwh=final_soc,
            battery_cfg=battery_cfg,
            grid_cfg=grid_cfg,
            solver_cfg=solver_cfg,
        )
        chunks.append(chunk)
        solvers_used.add(solver_used)
        soc_now = float(chunk["battery_soc_kWh"].iloc[-1])

    return pd.concat(chunks, ignore_index=True), sorted(solvers_used)
