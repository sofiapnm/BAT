import argparse
from pathlib import Path

import pandas as pd

from model_builder import build_model, solve_model
from parameters.battery import BATTERY_TECHNICAL
from parameters.general import GENERAL
from results import (
    extract_monthly_peak_solution,
    extract_solution,
    save_results,
    summarize_solution,
)


RESULTS_DIR = Path(__file__).resolve().parents[1] / "results"


def parse_args():
    parser = argparse.ArgumentParser(
        description="Run Pareto points one at a time or as a full sequence."
    )
    parser.add_argument(
        "--point",
        type=int,
        default=None,
        help="Run only one epsilon point by 1-based index.",
    )
    parser.add_argument(
        "--pause-between-points",
        action="store_true",
        help="Pause for Enter between Pareto points.",
    )
    return parser.parse_args()


def build_pareto_caps(min_emissions_kgco2, max_emissions_kgco2, num_points):
    if num_points <= 2 or max_emissions_kgco2 <= min_emissions_kgco2:
        return []

    step = (max_emissions_kgco2 - min_emissions_kgco2) / (num_points - 1)
    return [float(min_emissions_kgco2 + i * step) for i in range(1, num_points - 1)]


def build_inverse_pareto_caps(min_emissions_kgco2, max_emissions_kgco2, num_points):
    return list(
        reversed(
            build_pareto_caps(
                min_emissions_kgco2=min_emissions_kgco2,
                max_emissions_kgco2=max_emissions_kgco2,
                num_points=num_points,
            )
        )
    )


def load_anchor_summaries():
    cost_kwh_path = RESULTS_DIR / "cost_opt kWh results.csv"
    emis_kwh_path = RESULTS_DIR / "emis_opt kWh results.csv"
    
    if not cost_kwh_path.exists() or not emis_kwh_path.exists():
        missing = []
        if not cost_kwh_path.exists():
            missing.append("cost_opt kWh results.csv")
        if not emis_kwh_path.exists():
            missing.append("emis_opt kWh results.csv")
        raise FileNotFoundError(
            f"Run main.py twice to generate required files: {', '.join(missing)}.\n"
            f"  python main.py cost\n"
            f"  python main.py emission"
        )

    cost_kwh_results = pd.read_csv(cost_kwh_path, parse_dates=["DateTime"])
    emis_kwh_results = pd.read_csv(emis_kwh_path, parse_dates=["DateTime"])

    def compute_monthly_peak(series_kwh, delta_t_h):
        s = pd.Series(series_kwh)
        dt_index = pd.to_datetime(s.index)
        month_labels = dt_index.to_period("M").astype(str)
        kw = s.values / float(delta_t_h)
        df = pd.DataFrame({"month": month_labels, "kw": kw})
        peaks = df.groupby("month")["kw"].max()
        return peaks

    delta_t = GENERAL["delta_t_h"]
    monthly_peak_cost = compute_monthly_peak(cost_kwh_results.set_index(pd.to_datetime(cost_kwh_results["DateTime"]))["grid_import_kWh"], delta_t)
    monthly_peak_emis = compute_monthly_peak(emis_kwh_results.set_index(pd.to_datetime(emis_kwh_results["DateTime"]))["grid_import_kWh"], delta_t)

    cost_summary = summarize_solution(
        solution=cost_kwh_results,
        production=cost_kwh_results["production_kWh"],
        heatdemand=cost_kwh_results["heatdemand_kWhth"],
        spot_price=cost_kwh_results["spot price [Rp/kWh]"],
        monthly_peak=monthly_peak_cost,
        datetime_series=cost_kwh_results["DateTime"],
    )
    emissions_summary = summarize_solution(
        solution=emis_kwh_results,
        production=emis_kwh_results["production_kWh"],
        heatdemand=emis_kwh_results["heatdemand_kWhth"],
        spot_price=emis_kwh_results["spot price [Rp/kWh]"],
        monthly_peak=monthly_peak_emis,
        datetime_series=emis_kwh_results["DateTime"],
    )

    return cost_kwh_results, emis_kwh_results, cost_summary, emissions_summary


def upsert_pareto_row(output_path, new_row):
    output_path = Path(output_path)
    if output_path.exists():
        existing = pd.read_csv(output_path)
        combined = pd.concat([existing, pd.DataFrame([new_row])], ignore_index=True)
        combined = combined.drop_duplicates(subset=["pareto_point"], keep="last")
    else:
        combined = pd.DataFrame([new_row])

    combined = combined.sort_values(by="annual_emissions_burden_kgco2")
    save_results(combined, output_path)


def main():
    args = parse_args()
    cost_kwh_results, emis_kwh_results, cost_summary, emissions_summary = load_anchor_summaries()

    pareto_rows = [
        {
            "pareto_point": 0,
            "scenario": "emissions_anchor",
            "emissions_cap_kgco2": emissions_summary["annual_emissions_burden_kgco2"],
            **emissions_summary,
        }
    ]
    emissions_caps = build_inverse_pareto_caps(
        min_emissions_kgco2=emissions_summary["annual_emissions_burden_kgco2"],
        max_emissions_kgco2=cost_summary["annual_emissions_burden_kgco2"],
        num_points=GENERAL["pareto_num_points"],
    )

    full_horizon_init_soc = (
        BATTERY_TECHNICAL["soc_init_frac"] * BATTERY_TECHNICAL["capacity_kwh"]
    )
    full_horizon_end_soc = (
        BATTERY_TECHNICAL["soc_end_frac"] * BATTERY_TECHNICAL["capacity_kwh"]
    )

    production = cost_kwh_results["production_kWh"]
    elecdemand = cost_kwh_results["load_kWh"]
    heatdemand = cost_kwh_results["heatdemand_kWhth"]
    spot_price = cost_kwh_results["spot price [Rp/kWh]"]
    datetime_series = cost_kwh_results["DateTime"]

    total_epsilon_points = len(emissions_caps)
    if args.point is not None:
        if args.point < 1 or args.point > total_epsilon_points:
            raise ValueError(
                f"--point must be between 1 and {total_epsilon_points}. Got {args.point}."
            )
        emissions_caps = [emissions_caps[args.point - 1]]

    for i, emissions_cap in enumerate(emissions_caps):
        point_number = args.point if args.point is not None else i + 1
        if args.pause_between_points:
            try:
                input(f"Press Enter to run Pareto point {point_number}/{total_epsilon_points}...")
            except EOFError:
                pass

        model_pareto, vars_pareto = build_model(
            production_kwh=production,
            elecdemand_kwh=elecdemand,
            heatdemand_kwhth=heatdemand,
            spot_price_rp_per_kwh=spot_price,
            datetime_series=datetime_series,
            objective_mode="cost",
            init_soc_kwh=full_horizon_init_soc,
            final_soc_kwh=full_horizon_end_soc,
            emissions_cap_kgco2=emissions_cap,
        )
        solve_model(model_pareto, objective_mode=f"pareto_cost_cap_{point_number}")
        sol_pareto = extract_solution(vars_pareto, len(elecdemand))
        monthly_peak_pareto = extract_monthly_peak_solution(vars_pareto)
        pareto_summary = summarize_solution(
            solution=sol_pareto,
            production=production,
            heatdemand=heatdemand,
            spot_price=spot_price,
            monthly_peak=monthly_peak_pareto,
            datetime_series=datetime_series,
        )
        pareto_rows.append(
            {
                "pareto_point": point_number,
                "scenario": "epsilon_constrained_cost",
                "emissions_cap_kgco2": emissions_cap,
                **pareto_summary,
            }
        )
        upsert_pareto_row(GENERAL["pareto_output_path"], pareto_rows[-1])
        print(
            f"Pareto progress: {point_number}/{total_epsilon_points} points saved to {GENERAL['pareto_output_path']}"
        )

        if args.point is not None:
            print("Checkpoint mode complete after one Pareto point.")
            return

    pareto_rows.append(
        {
            "pareto_point": len(pareto_rows),
            "scenario": "cost_anchor",
            "emissions_cap_kgco2": cost_summary["annual_emissions_burden_kgco2"],
            **cost_summary,
        }
    )

    pareto_results = pd.DataFrame(pareto_rows).sort_values(
        by="annual_emissions_burden_kgco2"
    )
    save_results(pareto_results, GENERAL["pareto_output_path"])
    print(f"Pareto front output file: {GENERAL['pareto_output_path']}")


if __name__ == "__main__":
    main()
