import sys
from pathlib import Path
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import webbrowser

# Paths for BESS-only results
BASE = Path(__file__).resolve().parents[3] / "results" / "pareto" / "BESS only"
COST_CSV = BASE / "cost_opt kWh results.csv"
EMIS_CSV = BASE / "emis_opt kWh results.csv"
# write HTML to same folder as this script
HTML_OUTPUT_PATH = Path(__file__).resolve().parent / "pareto_bess.html"


def _first_available_numeric(row, column_names):
	for column_name in column_names:
		value = row.get(column_name)
		if pd.notna(value):
			return float(value)
	return None


def compute_monthly_peak(series_kwh, delta_t_h):
	# series_kwh indexed by timestamps (kWh per timestep) -> convert to kW then monthly max
	s = pd.Series(series_kwh)
	dt_index = pd.to_datetime(s.index)
	month_labels = dt_index.to_period("M").astype(str)
	# compute kW
	kw = s.values / float(delta_t_h)
	df = pd.DataFrame({"month": month_labels, "kw": kw})
	peaks = df.groupby("month")["kw"].max()
	return peaks


def build_hover_text_from_solution(sol_df, total_cost_rp, total_emis_kgco2):
	total_load = float(sol_df["load_kWh"].sum())
	grid_import = float(sol_df["grid_import_kWh"].sum())
	grid_export = float(sol_df["grid_export_kWh"].sum())
	prod_local = float(sol_df.get("prod_for_local_demand_kWh", sol_df.get("production_kWh", pd.Series(0))).sum())
	batt_charge = float(sol_df.get("battery_charge_kWh", 0.0).sum() if hasattr(sol_df.get("battery_charge_kWh"), 'sum') else sol_df.get("battery_charge_kWh", 0.0))
	batt_discharge = float(sol_df.get("battery_discharge_kWh", 0.0).sum() if hasattr(sol_df.get("battery_discharge_kWh"), 'sum') else sol_df.get("battery_discharge_kWh", 0.0))

	def pct(x):
		return f"{(x / total_load * 100):.1f}%" if total_load > 0 else "N/A"

	lines = []
	lines.append(f"Total system cost: {total_cost_rp:,.0f} Rp")
	lines.append(f"Total system emissions: {total_emis_kgco2:,.0f} kgCO2")
	lines.append("")
	lines.append("Total energy (kWh):")
	lines.append(f" - Grid import: {grid_import:,.1f} kWh")
	lines.append(f" - Grid export: {grid_export:,.1f} kWh")
	lines.append(f" - Run-of-river (production used locally): {prod_local:,.1f} kWh")
	lines.append(f" - BESS charge: {batt_charge:,.1f} kWh")
	lines.append(f" - BESS discharge: {batt_discharge:,.1f} kWh")
	lines.append("")
	lines.append("Share of load met:")
	lines.append(f" - From grid import: {pct(grid_import)}")
	lines.append(f" - From local production: {pct(prod_local)}")
	lines.append(f" - From BESS discharge: {pct(batt_discharge)}")

	return "<br>".join(lines)


def build_figure(pareto_df, anchors_info):
	pareto_df_sorted = pareto_df.sort_values("annual_emissions_burden_kgco2")

	fig = make_subplots(rows=1, cols=1)

	hover_texts = pareto_df_sorted.apply(
		lambda r: f"Pareto point {int(r['pareto_point'])}<br>Scenario: {r['scenario']}<br>Emissions: {r['annual_emissions_burden_kgco2']:,.0f} kgCO2<br>Profit: {r['net_annual_profit_chf']:,.0f} CHF",
		axis=1,
	)

	fig.add_trace(
		go.Scatter(
			x=pareto_df_sorted["annual_emissions_burden_kgco2"],
			y=pareto_df_sorted["net_annual_profit_chf"],
			mode="lines+markers",
			name="Pareto front",
			line={"width": 3, "color": "#1f77b4"},
			marker={"size": 8, "color": "#1f77b4"},
			hovertext=hover_texts,
			hovertemplate="%{hovertext}<extra></extra>",
		)
	)

	# Add anchors as markers with detailed hover
	for key, info in anchors_info.items():
		dfrow = info["summary_row"]
		hover = info["hover_html"]
		fig.add_trace(
			go.Scatter(
				x=[dfrow["annual_emissions_burden_kgco2"]],
				y=[dfrow["net_annual_profit_chf"]],
				mode="markers+text",
				name=info.get("label", key),
				marker={"size": 13, "color": info.get("color", "#111111"), "line": {"width": 1, "color": "#ffffff"}},
				text=[info.get("label", key)],
				textposition="top center",
				hovertext=[hover],
				hovertemplate="%{hovertext}<extra></extra>",
			)
		)

	fig.update_xaxes(title_text="Annual Emissions Burden [kgCO2]")
	fig.update_yaxes(title_text="Net Annual Profit [CHF]")
	fig.update_layout(
		title="Battery-only Pareto: Net Annual Profit vs Annual Emissions",
		template="plotly_white",
		hovermode="closest",
		height=700,
		legend_title="Series",
	)

	return fig


def main():
	if not COST_CSV.exists() or not EMIS_CSV.exists():
		raise FileNotFoundError("Cost or emissions CSV not found in BESS only folder")

	cost_df = pd.read_csv(COST_CSV, parse_dates=["DateTime"])
	emis_df = pd.read_csv(EMIS_CSV, parse_dates=["DateTime"])

	# compute monthly peaks (kW) from grid_import_kWh
	from pathlib import Path as _P
	# import program helpers (model builder, results, parameters)
	sys.path.append(str(Path(__file__).resolve().parents[3] / "program"))
	try:
		from model_builder import build_model, solve_model
		from results import (
			summarize_solution,
			extract_solution,
			extract_monthly_peak_solution,
			save_results,
		)
		from parameters.general import GENERAL
		from parameters.battery import BATTERY_TECHNICAL
	except Exception:
		# fallback minimal imports
		from results import summarize_solution
		GENERAL = {"delta_t_h": 0.25, "pareto_num_points": 2}
		BATTERY_TECHNICAL = {"soc_init_frac": 0.5, "soc_end_frac": 0.5, "capacity_kwh": 0.0}

	delta_t = GENERAL["delta_t_h"]

	monthly_peak_cost = compute_monthly_peak(cost_df.set_index(pd.to_datetime(cost_df["DateTime"]))["grid_import_kWh"], delta_t)
	monthly_peak_emis = compute_monthly_peak(emis_df.set_index(pd.to_datetime(emis_df["DateTime"]))["grid_import_kWh"], delta_t)

	# Summaries (net profit CHF and annual emissions kgCO2)
	cost_summary = summarize_solution(
		solution=cost_df,
		production=cost_df["production_kWh"],
		heatdemand=cost_df["heatdemand_kWhth"],
		spot_price=cost_df["spot price [Rp/kWh]"],
		monthly_peak=monthly_peak_cost,
		datetime_series=cost_df["DateTime"],
	)

	emis_summary = summarize_solution(
		solution=emis_df,
		production=emis_df["production_kWh"],
		heatdemand=emis_df["heatdemand_kWhth"],
		spot_price=emis_df["spot price [Rp/kWh]"],
		monthly_peak=monthly_peak_emis,
		datetime_series=emis_df["DateTime"],
	)

	# Build pareto rows starting with anchors (emissions anchor first)
	pareto_rows = [
		{"pareto_point": 0, "scenario": "emissions_anchor", "emissions_cap_kgco2": emis_summary["annual_emissions_burden_kgco2"], **emis_summary},
		{"pareto_point": -1, "scenario": "cost_anchor", "emissions_cap_kgco2": cost_summary["annual_emissions_burden_kgco2"], **cost_summary},
	]

	# If a precomputed Pareto CSV exists, prefer that and skip optimization runs
	pareto_csv = BASE / "Pareto Front Results.csv"
	if pareto_csv.exists():
		pareto_df = pd.read_csv(pareto_csv)
	else:
		# helper to build emission caps between anchors
		def build_pareto_caps(min_emis, max_emis, num_points):
			if num_points <= 2 or max_emis <= min_emis:
				return []
			step = (max_emis - min_emis) / (num_points - 1)
			return [float(min_emis + i * step) for i in range(1, num_points - 1)]

		num_points = int(GENERAL.get("pareto_num_points", 2))
		emissions_caps = build_pareto_caps(
			emis_summary["annual_emissions_burden_kgco2"],
			cost_summary["annual_emissions_burden_kgco2"],
			num_points,
		)

		# prepare inputs for model runs (use cost_df as baseline profiles)
		full_horizon_init_soc = (
			BATTERY_TECHNICAL["soc_init_frac"] * BATTERY_TECHNICAL["capacity_kwh"]
		)
		full_horizon_end_soc = (
			BATTERY_TECHNICAL["soc_end_frac"] * BATTERY_TECHNICAL["capacity_kwh"]
		)

		production = cost_df["production_kWh"]
		elecdemand = cost_df["load_kWh"]
		heatdemand = cost_df.get("heatdemand_kWhth", pd.Series([0.0] * len(cost_df)))
		spot_price = cost_df["spot price [Rp/kWh]"]
		datetime_series = cost_df["DateTime"]

		# run optimizer for each intermediate emissions cap
		next_point = 1
		for i, emissions_cap in enumerate(emissions_caps):
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
			solve_model(model_pareto, objective_mode=f"pareto_cost_cap_{i}")
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
					"pareto_point": next_point,
					"scenario": "epsilon_constrained_cost",
					"emissions_cap_kgco2": emissions_cap,
					**pareto_summary,
				}
			)
			next_point += 1
			# save intermediate progress
			save_results(pd.DataFrame(pareto_rows).sort_values(by="annual_emissions_burden_kgco2"), pareto_csv)
			print(f"Pareto progress: {i+1}/{len(emissions_caps)} points saved to {pareto_csv}")

		# append cost anchor and persist final pareto
		pareto_rows.append({"pareto_point": next_point, "scenario": "cost_anchor", "emissions_cap_kgco2": cost_summary["annual_emissions_burden_kgco2"], **cost_summary})
		pareto_df = pd.DataFrame(pareto_rows).sort_values(by="annual_emissions_burden_kgco2")
		save_results(pareto_df, pareto_csv)

	# Build anchors info for detailed hover
	# compute total costs/emissions from cost/emis solutions using formulas in results.build_results_table
	# to avoid heavy imports, compute approximate totals here
	# total cost (Rp) approx = - net_profit_chf * 100 + total_revenues? use step-cost approach is complex; instead compute step cost sums via simple proxy:
	# We will compute annual import cost approx (using spot price * grid_import), and use that as representative for hover.
	cost_total_import_rp = float((cost_df["grid_import_kWh"] * cost_df["spot price [Rp/kWh]"]).sum())
	emis_total_import_rp = float((emis_df["grid_import_kWh"] * emis_df["spot price [Rp/kWh]"]).sum())

	cost_total_emis_kg = float((cost_df["grid_import_kWh"] * 0).sum())

	anchors_info = {
		"emissions_anchor": {
			"label": "Emissions anchor",
			"color": "#d62728",
			"summary_row": {"net_annual_profit_chf": emis_summary["net_annual_profit_chf"], "annual_emissions_burden_kgco2": emis_summary["annual_emissions_burden_kgco2" ]},
			"hover_html": build_hover_text_from_solution(emis_df, emis_total_import_rp, emis_summary["annual_emissions_burden_kgco2"]),
		},
		"cost_anchor": {
			"label": "Cost anchor",
			"color": "#2ca02c",
			"summary_row": {"net_annual_profit_chf": cost_summary["net_annual_profit_chf"], "annual_emissions_burden_kgco2": cost_summary["annual_emissions_burden_kgco2"]},
			"hover_html": build_hover_text_from_solution(cost_df, cost_total_import_rp, cost_summary["annual_emissions_burden_kgco2"]),
		},
	}

	# ensure df has required columns for plotting
	if "annual_emissions_burden_kgco2" not in pareto_df.columns or "net_annual_profit_chf" not in pareto_df.columns:
		raise KeyError("Pareto dataframe must contain 'annual_emissions_burden_kgco2' and 'net_annual_profit_chf' columns")

	fig = build_figure(pareto_df, anchors_info)
	# Match kW dispatch plot behavior: write HTML and show figure
	fig.write_html(HTML_OUTPUT_PATH)
	fig.show()


if __name__ == "__main__":
	main()

