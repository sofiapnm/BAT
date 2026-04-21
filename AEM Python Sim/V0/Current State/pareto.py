import argparse
import importlib.util
import sys
from pathlib import Path

import pandas as pd


THIS_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = THIS_DIR.parents[1]
V1_ABSTRACTION_DIR = (
	PROJECT_ROOT / "V1" / "V1.2 Pareto Front" / "V1.1 Abstraction (Gurobi)"
)

if str(V1_ABSTRACTION_DIR) not in sys.path:
	sys.path.insert(0, str(V1_ABSTRACTION_DIR))


def _load_module_from_path(module_name: str, module_path: Path):
	spec = importlib.util.spec_from_file_location(module_name, module_path)
	if spec is None or spec.loader is None:
		raise ImportError(f"Cannot load module spec from: {module_path}")
	module = importlib.util.module_from_spec(spec)
	spec.loader.exec_module(module)
	return module


grid_import = _load_module_from_path(
	"grid_import_params",
	V1_ABSTRACTION_DIR / "parameters" / "grid_import.py",
)
grid_export = _load_module_from_path(
	"grid_export_params",
	V1_ABSTRACTION_DIR / "parameters" / "grid_export.py",
)
runofriver = _load_module_from_path(
	"runofriver_params",
	V1_ABSTRACTION_DIR / "parameters" / "runofriver.py",
)


DEFAULT_INPUT_PATH = (
	PROJECT_ROOT / "Data Sorting" / "DATA" / "AEM TOTAL 2024_corrected.csv"
)
DEFAULT_OUTPUT_PATH = THIS_DIR / "pareto_annual_summary.csv"
RP_PER_CHF = 100.0


def rp_to_chf(amount_rp: float) -> float:
	return amount_rp / RP_PER_CHF


def load_profiles(input_path: Path) -> pd.DataFrame:
	df = pd.read_csv(input_path)
	required_cols = [
		"DateTime",
		"Demand",
		"Surplus",
		"Spot price [Rp/kWh]",
		"Sales",
	]
	missing = [c for c in required_cols if c not in df.columns]
	if missing:
		raise KeyError(f"Missing required columns: {missing}")

	out = pd.DataFrame(
		{
			"DateTime": pd.to_datetime(df["DateTime"], errors="coerce"),
			"demand_kwh": pd.to_numeric(df["Demand"], errors="coerce"),
			"surplus_kwh": pd.to_numeric(df["Surplus"], errors="coerce"),
			"spot_price_rp_per_kwh": pd.to_numeric(
				df["Spot price [Rp/kWh]"], errors="coerce"
			),
			"production_kwh": pd.to_numeric(df["Sales"], errors="coerce"),
		}
	)

	out = out.dropna(subset=["DateTime"]).sort_values("DateTime").reset_index(drop=True)

	numeric_cols = [
		"demand_kwh",
		"surplus_kwh",
		"spot_price_rp_per_kwh",
		"production_kwh",
	]
	out[numeric_cols] = out[numeric_cols].interpolate(limit_direction="both")
	out[numeric_cols] = out[numeric_cols].ffill().bfill()

	if out[numeric_cols].isna().any().any():
		nan_counts = out[numeric_cols].isna().sum()
		raise ValueError(
			"Input data still contains NaN after cleaning: "
			f"{nan_counts[nan_counts > 0].to_dict()}"
		)

	return out


def calculate_annual_summary(profiles: pd.DataFrame) -> pd.DataFrame:
	annual_import_kwh = float(profiles["demand_kwh"].sum())
	annual_export_kwh = float(profiles["surplus_kwh"].sum())
	annual_production_kwh = float(profiles["production_kwh"].sum())

	annual_grid_use_h = grid_import.annual_grid_use_hours(
		annual_import_kwh, annual_export_kwh
	)

	import_price = grid_import.import_price_rp_per_kwh(
		profiles["spot_price_rp_per_kwh"], annual_grid_use_h
	)
	export_price = grid_export.export_price_rp_per_kwh(
		profiles["spot_price_rp_per_kwh"], annual_grid_use_h
	)

	annual_import_cost_rp = float((profiles["demand_kwh"] * import_price).sum())
	annual_export_revenue_rp = float((profiles["surplus_kwh"] * export_price).sum())

	month_labels = profiles["DateTime"].dt.to_period("M")
	monthly_peak_kw = profiles.groupby(month_labels, sort=True)["demand_kwh"].max()
	power_tariff_rp_per_kw_month = grid_import.power_tariff_rp_per_kw_per_month(
		annual_grid_use_h
	)
	annual_power_cost_rp = float(monthly_peak_kw.sum() * power_tariff_rp_per_kw_month)

	runofriver_profit_rp_per_kwh = runofriver.RUNOFRIVER_ECONOMIC["profit_rp_per_kwh"]
	annual_runofriver_profit_rp = float(
		annual_production_kwh * runofriver_profit_rp_per_kwh
	)

	annual_cost_burden_rp = (
		annual_import_cost_rp
		- annual_export_revenue_rp
		- annual_runofriver_profit_rp
		+ annual_power_cost_rp
	)
	annual_import_cost_chf = rp_to_chf(annual_import_cost_rp)
	annual_export_revenue_chf = rp_to_chf(annual_export_revenue_rp)
	annual_runofriver_profit_chf = rp_to_chf(annual_runofriver_profit_rp)
	annual_power_cost_chf = rp_to_chf(annual_power_cost_rp)
	annual_cost_burden_chf = rp_to_chf(annual_cost_burden_rp)
	power_tariff_chf_per_kw_month = rp_to_chf(power_tariff_rp_per_kw_month)

	annual_import_emissions_kgco2 = float(
		annual_import_kwh
		* grid_import.IMPORT_EMISSIONS["grid_emissions_kgco2_per_kwh"]
	)
	annual_export_emissions_kgco2 = float(
		annual_export_kwh
		* grid_export.EXPORT_EMISSIONS["export_emissions_kgco2_per_kwh"]
	)
	annual_runofriver_emissions_kgco2 = float(
		annual_production_kwh
		* runofriver.RUNOFRIVER_EMISSIONS["emissions_kgco2eq_per_kwh_generated"]
	)
	annual_emissions_burden_kgco2 = float(
		annual_import_emissions_kgco2
		+ annual_export_emissions_kgco2
		+ annual_runofriver_emissions_kgco2
	)

	summary = {
		"annual_cost_burden_chf": annual_cost_burden_chf,
		"net_annual_profit_chf": -annual_cost_burden_chf,
		"annual_import_emissions_kgco2": annual_import_emissions_kgco2,
		"annual_export_emissions_kgco2": annual_export_emissions_kgco2,
		"annual_runofriver_emissions_kgco2": annual_runofriver_emissions_kgco2,
		"annual_emissions_burden_kgco2": annual_emissions_burden_kgco2,
		"annual_grid_import_kwh": annual_import_kwh,
		"annual_grid_export_kwh": annual_export_kwh,
		"annual_grid_use_h": annual_grid_use_h,
		"annual_production_kwh": annual_production_kwh,
		"annual_import_cost_chf": annual_import_cost_chf,
		"annual_export_revenue_chf": annual_export_revenue_chf,
		"annual_runofriver_profit_chf": annual_runofriver_profit_chf,
		"annual_power_cost_chf": annual_power_cost_chf,
		"power_tariff_chf_per_kw_per_month": power_tariff_chf_per_kw_month,
		"interval_count": int(len(profiles)),
	}

	return pd.DataFrame([summary])


def main() -> None:
	parser = argparse.ArgumentParser(
		description=(
			"Deterministic annual economic and environmental accounting (no battery, "
			"no optimization): import=Demand, export=Surplus."
		)
	)
	parser.add_argument(
		"--input",
		default=str(DEFAULT_INPUT_PATH),
		help="Input CSV path with Demand, Surplus, spot price, and production columns.",
	)
	parser.add_argument(
		"--output",
		default=str(DEFAULT_OUTPUT_PATH),
		help="Output CSV path for single-row annual summary.",
	)
	args = parser.parse_args()

	input_path = Path(args.input)
	output_path = Path(args.output)

	profiles = load_profiles(input_path)
	summary_df = calculate_annual_summary(profiles)

	output_path.parent.mkdir(parents=True, exist_ok=True)
	summary_df.to_csv(output_path, index=False)

	row = summary_df.iloc[0]
	print("Annual deterministic summary complete.")
	print(f"Input file: {input_path}")
	print(f"Output file: {output_path}")
	print(f"Intervals: {int(row['interval_count'])}")
	print("")
	print("Economic summary")
	print(f"  Annual import cost burden [CHF]: {row['annual_import_cost_chf']:,.2f}")
	print(f"  Annual export revenue [CHF]: {row['annual_export_revenue_chf']:,.2f}")
	print(
		"  Annual run-of-river operating profit [CHF]: "
		f"{row['annual_runofriver_profit_chf']:,.2f}"
	)
	print(f"  Annual power tariff cost [CHF]: {row['annual_power_cost_chf']:,.2f}")
	print(f"  Annual economic burden [CHF]: {row['annual_cost_burden_chf']:,.2f}")
	print(f"  Net annual profit [CHF]: {row['net_annual_profit_chf']:,.2f}")
	print("")
	print("Environmental summary")
	print(
		"  Annual grid import emissions [kgCO2]: "
		f"{row['annual_import_emissions_kgco2']:,.2f}"
	)
	print(
		"  Annual grid export emissions [kgCO2]: "
		f"{row['annual_export_emissions_kgco2']:,.2f}"
	)
	print(
		"  Annual run-of-river emissions [kgCO2]: "
		f"{row['annual_runofriver_emissions_kgco2']:,.2f}"
	)
	print(
		"  Annual environmental burden [kgCO2]: "
		f"{row['annual_emissions_burden_kgco2']:,.2f}"
	)


if __name__ == "__main__":
	main()
