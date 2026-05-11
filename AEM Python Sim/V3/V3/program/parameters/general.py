from pathlib import Path


THIS_DIR = Path(__file__).resolve().parent
ABSTRACTION_DIR = THIS_DIR.parents[1]
SIM_ROOT = THIS_DIR.parents[3]
RESULTS_DIR = ABSTRACTION_DIR / "results"


GENERAL = {
    "data_path": str(
        SIM_ROOT / "Data Sorting" / "DATA" / "maxprod2024.csv"
    ),
    "output_path": str(RESULTS_DIR / "Cost+Emi Results.csv"),
    "kwh_output_path": str(RESULTS_DIR / "kWh Results.csv"),
    "pareto_output_path": str(RESULTS_DIR / "Pareto Front Results.csv"),
    "delta_t_h": 0.25,   # 15 minutes
    "solver_name": "gurobi",
    "gurobi_output_flag": 0,
    "pareto_num_points": 21,
    "emissions_penalty": 0.0, #120 CHF/ton CO2eq. for thermal fuels, need to find renewable elec generation tax (if any)
}
