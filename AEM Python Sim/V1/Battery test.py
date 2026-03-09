from pyomo.environ import (
    ConcreteModel,
    Constraint,
    NonNegativeReals,
    Objective,
    Param,
    RangeSet,
    Reals,
    SolverFactory,
    TerminationCondition,
    Var,
    minimize,
    value,
)

import pandas as pd
import gurobipy as gp
from gurobipy import GRB


DATA_PATH = "/workspaces/BAT/AEM Python Sim/Data Sorting/DATA/AEM TOTAL 2024_corrected.csv"
OUTPUT_PATH = "/workspaces/BAT/AEM Python Sim/V1/Results/battery_optimization_results_2024.csv"

# 15-minute intervals
DELTA_T_H = 0.25

# Battery technical limits (create two possible solutions: many small batteries or large 1)
BATTERY_CAPACITY_KWH = 4000.0
BATTERY_SOC_MIN_FRAC = 0.05
BATTERY_SOC_MAX_FRAC = 0.95
BATTERY_SOC_INIT_FRAC = 0.50
BATTERY_SOC_END_FRAC = 0.50
BATTERY_CHARGE_POWER_MAX_KW = 2000.0
BATTERY_DISCHARGE_POWER_MAX_KW = 2000.0
BATTERY_CHARGE_EFF = 0.95
BATTERY_DISCHARGE_EFF = 0.95
BATTERY_THROUGHPUT_COST_RP_PER_KWH = 0.02

# Emissions factors (used in emissions objective)
GRID_EMISSIONS_KGCO2_PER_KWH = 0.35
EXPORT_EMISSIONS_CREDIT_KGCO2_PER_KWH = 0.0
PRIMARY_SOLVER = "gurobi"
FALLBACK_SOLVER = "highs"
GUROBI_OPTIONS = {
    "Method": int(GRB.METHOD_BARRIER),
    "Crossover": 0,
    "OutputFlag": 0,
}


def build_and_solve(
    production_kwh,
    demand_kwh,
    spot_price_rp_per_kwh,
    objective_mode,
    init_soc_kwh,
    final_soc_kwh,
):
    n = len(demand_kwh)
    m = ConcreteModel()
    m.T = RangeSet(0, n - 1)

    m.production = Param(m.T, initialize={t: float(production_kwh[t]) for t in range(n)}, within=Reals)
    m.demand = Param(m.T, initialize={t: float(demand_kwh[t]) for t in range(n)}, within=Reals)
    m.spot = Param(m.T, initialize={t: float(spot_price_rp_per_kwh[t]) for t in range(n)}, within=Reals)

    # Grid flows [kWh per 15-min interval]
    m.grid_import = Var(m.T, within=NonNegativeReals)
    m.grid_export = Var(m.T, within=NonNegativeReals)

    # Battery energy flows [kWh per interval]
    m.batt_charge = Var(m.T, within=NonNegativeReals)
    m.batt_discharge = Var(m.T, within=NonNegativeReals)

    # SOC state [kWh]
    m.soc = Var(
        m.T,
        bounds=(
            BATTERY_SOC_MIN_FRAC * BATTERY_CAPACITY_KWH,
            BATTERY_SOC_MAX_FRAC * BATTERY_CAPACITY_KWH,
        ),
        within=NonNegativeReals,
    )

    # Power-rate limits converted from kW to kWh per interval
    max_charge_kwh = BATTERY_CHARGE_POWER_MAX_KW * DELTA_T_H
    max_discharge_kwh = BATTERY_DISCHARGE_POWER_MAX_KW * DELTA_T_H

    def energy_balance_rule(model, t):
        return (
            model.production[t]
            + model.grid_import[t]
            + model.batt_discharge[t] * BATTERY_DISCHARGE_EFF
            == model.demand[t] + model.grid_export[t] + model.batt_charge[t]
        )

    m.energy_balance = Constraint(m.T, rule=energy_balance_rule)

    def soc_transition_rule(model, t):
        if t == 0:
            return model.soc[t] == (init_soc_kwh + BATTERY_CHARGE_EFF * model.batt_charge[t] - model.batt_discharge[t])
        return model.soc[t] == (
            model.soc[t - 1]
            + BATTERY_CHARGE_EFF * model.batt_charge[t]
            - model.batt_discharge[t]
        )

    m.soc_transition = Constraint(m.T, rule=soc_transition_rule)
    m.charge_rate_limit = Constraint(m.T, rule=lambda model, t: model.batt_charge[t] <= max_charge_kwh)
    m.discharge_rate_limit = Constraint(m.T, rule=lambda model, t: model.batt_discharge[t] <= max_discharge_kwh)
    if final_soc_kwh is not None:
        m.final_soc = Constraint(expr=m.soc[n - 1] == final_soc_kwh)

    if objective_mode == "cost":
        m.objective = Objective(
            expr=sum(
                m.grid_import[t] * m.spot[t]
                - m.grid_export[t] * m.spot[t]
                + BATTERY_THROUGHPUT_COST_RP_PER_KWH * (m.batt_charge[t] + m.batt_discharge[t])
                for t in m.T
            ),
            sense=minimize,
        )
    elif objective_mode == "emissions":
        m.objective = Objective(
            expr=sum(
                m.grid_import[t] * GRID_EMISSIONS_KGCO2_PER_KWH
                - m.grid_export[t] * EXPORT_EMISSIONS_CREDIT_KGCO2_PER_KWH
                for t in m.T
            ),
            sense=minimize,
        )
    else:
        raise ValueError(f"Unknown objective_mode: {objective_mode}")

    primary = SolverFactory(PRIMARY_SOLVER)
    use_fallback = False
    if not primary.available():
        print(f"{PRIMARY_SOLVER} not available, falling back to {FALLBACK_SOLVER}.")
        use_fallback = True

    if use_fallback:
        solver = SolverFactory(FALLBACK_SOLVER)
        if not solver.available():
            raise RuntimeError(f"Neither {PRIMARY_SOLVER} nor {FALLBACK_SOLVER} is available.")
        results = solver.solve(m, tee=False)
        solver_used = FALLBACK_SOLVER
    else:
        try:
            for key, val in GUROBI_OPTIONS.items():
                primary.options[key] = val
            results = primary.solve(m, tee=False)
            solver_used = PRIMARY_SOLVER
        except Exception as exc:
            err_msg = str(exc).lower()
            if "size-limited license" in err_msg:
                raise RuntimeError("GUROBI_SIZE_LIMIT") from exc
            print(f"{PRIMARY_SOLVER} solve failed ({exc}), trying {FALLBACK_SOLVER}.")
            solver = SolverFactory(FALLBACK_SOLVER)
            if not solver.available():
                raise RuntimeError(f"{PRIMARY_SOLVER} failed and {FALLBACK_SOLVER} is unavailable.") from exc
            results = solver.solve(m, tee=False)
            solver_used = FALLBACK_SOLVER
    if results.solver.termination_condition != TerminationCondition.optimal:
        raise RuntimeError(f"No optimal solution for {objective_mode}. Condition: {results.solver.termination_condition}")

    out = pd.DataFrame(
        {
            "grid_import_kWh": [value(m.grid_import[t]) for t in range(n)],
            "grid_export_kWh": [value(m.grid_export[t]) for t in range(n)],
            "battery_charge_kWh": [value(m.batt_charge[t]) for t in range(n)],
            "battery_discharge_kWh": [value(m.batt_discharge[t]) for t in range(n)],
            "battery_soc_kWh": [value(m.soc[t]) for t in range(n)],
        }
    )
    return out, solver_used


def solve_in_windows(production, demand, spot_price, objective_mode, window_steps=192):
    if window_steps <= 1:
        raise ValueError("window_steps must be > 1.")

    n = len(demand)
    chunks = []
    solvers_used = set()
    soc_now = BATTERY_SOC_INIT_FRAC * BATTERY_CAPACITY_KWH

    for start in range(0, n, window_steps):
        stop = min(start + window_steps, n)
        is_last = stop == n
        final_soc = BATTERY_SOC_END_FRAC * BATTERY_CAPACITY_KWH if is_last else None

        chunk, solver_used = build_and_solve(
            production[start:stop],
            demand[start:stop],
            spot_price[start:stop],
            objective_mode=objective_mode,
            init_soc_kwh=soc_now,
            final_soc_kwh=final_soc,
        )
        chunks.append(chunk)
        solvers_used.add(solver_used)
        soc_now = float(chunk["battery_soc_kWh"].iloc[-1])

    return pd.concat(chunks, ignore_index=True), sorted(solvers_used)


def main():
    df = pd.read_csv(DATA_PATH)
    df["DateTime"] = pd.to_datetime(df["DateTime"])
    df = df.sort_values("DateTime").reset_index(drop=True)

    numeric_cols = ["Total Production Hydro", "Sales", "Spot price [Rp/kWh]"]
    for c in numeric_cols:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df[numeric_cols] = df[numeric_cols].interpolate(limit_direction="both")
    df[numeric_cols] = df[numeric_cols].ffill().bfill()
    if df[numeric_cols].isna().any().any():
        raise ValueError("Input data still contains NaN in required numeric columns after cleaning.")

    production = df["Total Production Hydro"].to_numpy(dtype=float)
    demand = df["Sales"].to_numpy(dtype=float)
    spot_price = df["Spot price [Rp/kWh]"].to_numpy(dtype=float)

    full_horizon_init_soc = BATTERY_SOC_INIT_FRAC * BATTERY_CAPACITY_KWH
    full_horizon_end_soc = BATTERY_SOC_END_FRAC * BATTERY_CAPACITY_KWH

    try:
        sol_cost, solver_cost = build_and_solve(
            production,
            demand,
            spot_price,
            objective_mode="cost",
            init_soc_kwh=full_horizon_init_soc,
            final_soc_kwh=full_horizon_end_soc,
        )
        sol_emis, solver_emis = build_and_solve(
            production,
            demand,
            spot_price,
            objective_mode="emissions",
            init_soc_kwh=full_horizon_init_soc,
            final_soc_kwh=full_horizon_end_soc,
        )
        print(f"Solver used for cost objective: {solver_cost}")
        print(f"Solver used for emissions objective: {solver_emis}")
    except RuntimeError as exc:
        if str(exc) != "GUROBI_SIZE_LIMIT":
            raise
        print("Gurobi size-limited license detected on full-year solve. Switching to rolling windows.")
        sol_cost, solvers_cost = solve_in_windows(production, demand, spot_price, objective_mode="cost", window_steps=192)
        sol_emis, solvers_emis = solve_in_windows(production, demand, spot_price, objective_mode="emissions", window_steps=192)
        print(f"Solver(s) used for cost objective (rolling windows): {', '.join(solvers_cost)}")
        print(f"Solver(s) used for emissions objective (rolling windows): {', '.join(solvers_emis)}")

    # Output table is intentionally separate from the source data:
    # only DateTime + optimization results are written.
    results = pd.DataFrame({"DateTime": df["DateTime"]})

    for col in sol_cost.columns:
        results[f"cost_opt__{col}"] = sol_cost[col].values
    for col in sol_emis.columns:
        results[f"emissions_opt__{col}"] = sol_emis[col].values

    # Per-step objective values for direct comparison at each time i
    spot_price_series = pd.Series(spot_price, index=results.index, dtype=float)
    results["cost_opt__step_cost_rp"] = (
        results["cost_opt__grid_import_kWh"] * spot_price_series
        - results["cost_opt__grid_export_kWh"] * spot_price_series
        + BATTERY_THROUGHPUT_COST_RP_PER_KWH
        * (results["cost_opt__battery_charge_kWh"] + results["cost_opt__battery_discharge_kWh"])
    )
    results["emissions_opt__step_cost_rp"] = (
        results["emissions_opt__grid_import_kWh"] * spot_price_series
        - results["emissions_opt__grid_export_kWh"] * spot_price_series
        + BATTERY_THROUGHPUT_COST_RP_PER_KWH
        * (results["emissions_opt__battery_charge_kWh"] + results["emissions_opt__battery_discharge_kWh"])
    )
    results["cost_opt__step_emissions_kgco2"] = (
        results["cost_opt__grid_import_kWh"] * GRID_EMISSIONS_KGCO2_PER_KWH
        - results["cost_opt__grid_export_kWh"] * EXPORT_EMISSIONS_CREDIT_KGCO2_PER_KWH
    )
    results["emissions_opt__step_emissions_kgco2"] = (
        results["emissions_opt__grid_import_kWh"] * GRID_EMISSIONS_KGCO2_PER_KWH
        - results["emissions_opt__grid_export_kWh"] * EXPORT_EMISSIONS_CREDIT_KGCO2_PER_KWH
    )

    results.to_csv(OUTPUT_PATH, index=False, mode="w")

    total_cost_costobj = results["cost_opt__step_cost_rp"].sum()
    total_cost_emisobj = results["emissions_opt__step_cost_rp"].sum()
    total_emis_costobj = results["cost_opt__step_emissions_kgco2"].sum()
    total_emis_emisobj = results["emissions_opt__step_emissions_kgco2"].sum()

    print("Optimization complete.")
    print(f"Rows solved (15-min intervals): {len(results)}")
    print(f"Output file: {OUTPUT_PATH}")
    print("")
    print("Annual totals")
    print(f"Cost objective -> total cost [Rp]: {total_cost_costobj:,.2f}")
    print(f"Cost objective -> total emissions [kgCO2]: {total_emis_costobj:,.2f}")
    print(f"Emissions objective -> total cost [Rp]: {total_cost_emisobj:,.2f}")
    print(f"Emissions objective -> total emissions [kgCO2]: {total_emis_emisobj:,.2f}")


if __name__ == "__main__":
    main()
