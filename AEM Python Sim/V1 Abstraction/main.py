import pandas as pd

from components.battery import BatteryConfig
from components.grid import GridConfig, SolverConfig
from components.profiles import load_profiles
from core.model import GurobiSizeLimitError, build_and_solve, solve_in_windows


DATA_PATH = "/workspaces/BAT/AEM Python Sim/Data Sorting/DATA/AEM TOTAL 2024_corrected.csv"
OUTPUT_PATH = "/workspaces/BAT/AEM Python Sim/V1 Abstraction/battery_optimization_results_2024.csv"


def main():
    battery_cfg = BatteryConfig()
    grid_cfg = GridConfig()
    solver_cfg = SolverConfig()

    df, production, demand, spot_price = load_profiles(DATA_PATH)

    production_arr = production.to_numpy(dtype=float)
    demand_arr = demand.to_numpy(dtype=float)
    spot_price_arr = spot_price.to_numpy(dtype=float)

    try:
        sol_cost, solver_cost = build_and_solve(
            production_kwh=production_arr,
            demand_kwh=demand_arr,
            spot_price_rp_per_kwh=spot_price_arr,
            objective_mode="cost",
            init_soc_kwh=battery_cfg.soc_init_kwh,
            final_soc_kwh=battery_cfg.soc_end_kwh,
            battery_cfg=battery_cfg,
            grid_cfg=grid_cfg,
            solver_cfg=solver_cfg,
        )
        sol_emis, solver_emis = build_and_solve(
            production_kwh=production_arr,
            demand_kwh=demand_arr,
            spot_price_rp_per_kwh=spot_price_arr,
            objective_mode="emissions",
            init_soc_kwh=battery_cfg.soc_init_kwh,
            final_soc_kwh=battery_cfg.soc_end_kwh,
            battery_cfg=battery_cfg,
            grid_cfg=grid_cfg,
            solver_cfg=solver_cfg,
        )
        print(f"Solver used for cost objective: {solver_cost}")
        print(f"Solver used for emissions objective: {solver_emis}")
    except GurobiSizeLimitError:
        print("Gurobi size-limited license detected on full-year solve. Switching to rolling windows.")
        sol_cost, solvers_cost = solve_in_windows(
            production=production_arr,
            demand=demand_arr,
            spot_price=spot_price_arr,
            objective_mode="cost",
            battery_cfg=battery_cfg,
            grid_cfg=grid_cfg,
            solver_cfg=solver_cfg,
            window_steps=192,
        )
        sol_emis, solvers_emis = solve_in_windows(
            production=production_arr,
            demand=demand_arr,
            spot_price=spot_price_arr,
            objective_mode="emissions",
            battery_cfg=battery_cfg,
            grid_cfg=grid_cfg,
            solver_cfg=solver_cfg,
            window_steps=192,
        )
        print(f"Solver(s) used for cost objective (rolling windows): {', '.join(solvers_cost)}")
        print(f"Solver(s) used for emissions objective (rolling windows): {', '.join(solvers_emis)}")

    results = pd.DataFrame({"DateTime": df["DateTime"]})

    for col in sol_cost.columns:
        results[f"cost_opt__{col}"] = sol_cost[col].values
    for col in sol_emis.columns:
        results[f"emissions_opt__{col}"] = sol_emis[col].values

    spot_price_series = pd.Series(spot_price_arr, index=results.index, dtype=float)
    results["cost_opt__step_cost_rp"] = (
        results["cost_opt__grid_import_kWh"] * spot_price_series
        - results["cost_opt__grid_export_kWh"] * spot_price_series
        + battery_cfg.throughput_cost_rp_per_kwh
        * (results["cost_opt__battery_charge_kWh"] + results["cost_opt__battery_discharge_kWh"])
    )
    results["emissions_opt__step_cost_rp"] = (
        results["emissions_opt__grid_import_kWh"] * spot_price_series
        - results["emissions_opt__grid_export_kWh"] * spot_price_series
        + battery_cfg.throughput_cost_rp_per_kwh
        * (results["emissions_opt__battery_charge_kWh"] + results["emissions_opt__battery_discharge_kWh"])
    )
    results["cost_opt__step_emissions_kgco2"] = (
        results["cost_opt__grid_import_kWh"] * grid_cfg.emissions_kgco2_per_kwh
        - results["cost_opt__grid_export_kWh"] * grid_cfg.export_emissions_credit_kgco2_per_kwh
    )
    results["emissions_opt__step_emissions_kgco2"] = (
        results["emissions_opt__grid_import_kWh"] * grid_cfg.emissions_kgco2_per_kwh
        - results["emissions_opt__grid_export_kWh"] * grid_cfg.export_emissions_credit_kgco2_per_kwh
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
