import argparse
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import sparse
try:
    from scipy.optimize import linprog
except ModuleNotFoundError as exc:
    raise ModuleNotFoundError(
        "This script now requires SciPy. Install it with: pip install scipy"
    ) from exc


TARIFF_RP_PER_KWH = 1.08
DEFAULT_GRID_EMISSION_KG_PER_KWH = 0.4


@dataclass
class ObjectiveConfig:
    name: str
    import_cost_per_kwh: pd.Series
    export_cost_per_kwh: pd.Series
    curtail_cost_per_kwh: float
    import_emission_per_kwh: float
    export_emission_per_kwh: float


def pick_column(df: pd.DataFrame, candidates: list[str]) -> str:
    for c in candidates:
        if c in df.columns:
            return c
    raise KeyError(f"None of these columns were found: {candidates}")

def run_optimization(df: pd.DataFrame, cfg: ObjectiveConfig, production_col: str, sales_col: str) -> pd.DataFrame:
    production = pd.to_numeric(df[production_col], errors="coerce").to_numpy(dtype=float)
    sales = pd.to_numeric(df[sales_col], errors="coerce").to_numpy(dtype=float)
    c_import = pd.to_numeric(cfg.import_cost_per_kwh.reindex(df.index), errors="coerce").to_numpy(dtype=float)
    c_export = pd.to_numeric(cfg.export_cost_per_kwh.reindex(df.index), errors="coerce").to_numpy(dtype=float)
    c_curtail = float(cfg.curtail_cost_per_kwh)
    e_import = float(cfg.import_emission_per_kwh)
    e_export = float(cfg.export_emission_per_kwh)

    n = len(df.index)
    imp = np.full(n, np.nan, dtype=float)
    exp = np.full(n, np.nan, dtype=float)
    cur = np.full(n, np.nan, dtype=float)
    obj = np.full(n, np.nan, dtype=float)
    emi = np.full(n, np.nan, dtype=float)

    valid = (
        np.isfinite(production)
        & np.isfinite(sales)
        & np.isfinite(c_import)
        & np.isfinite(c_export)
        & np.isfinite(c_curtail)
        & np.isfinite(e_import)
        & np.isfinite(e_export)
    )

    if valid.any():
        rhs = sales[valid] - production[valid]
        shortage = np.maximum(rhs, 0.0)
        surplus = np.maximum(-rhs, 0.0)
        m = int(valid.sum())

        c = np.concatenate(
            [
                c_import[valid],
                c_export[valid],
                np.full(m, c_curtail, dtype=float),
            ]
        )
        eye = sparse.eye(m, format="csr")
        a_eq = sparse.hstack([eye, -eye, -eye], format="csr")
        b_eq = rhs

        bounds = (
            [(0.0, float(v)) for v in shortage]
            + [(0.0, float(v)) for v in surplus]
            + [(0.0, float(v)) for v in surplus]
        )

        result = linprog(c=c, A_eq=a_eq, b_eq=b_eq, bounds=bounds, method="highs")
        if not result.success:
            raise RuntimeError(f"LP solve failed in {cfg.name}: {result.message}")

        x = result.x
        imp_valid = x[:m]
        exp_valid = x[m : 2 * m]
        cur_valid = x[2 * m :]

        imp[valid] = imp_valid
        exp[valid] = exp_valid
        cur[valid] = cur_valid
        obj[valid] = c_import[valid] * imp_valid + c_export[valid] * exp_valid + c_curtail * cur_valid
        emi[valid] = e_import * imp_valid + e_export * exp_valid

    return pd.DataFrame(
        {
            "grid_import_kwh": imp,
            "grid_export_kwh": exp,
            "curtailed_kwh": cur,
            f"{cfg.name}_objective": obj,
            f"{cfg.name}_emissions_kgco2e": emi,
        },
        index=df.index,
    )


def main():
    parser = argparse.ArgumentParser(description="Optimize grid exchange for minimum cost and minimum emissions.")
    parser.add_argument(
        "--input",
        default="/workspaces/BAT/AEM Python Sim/Data Sorting/DATA/AEM TOTAL 2024_corrected.csv",
        help="Input CSV path",
    )
    parser.add_argument(
        "--output",
        default="/workspaces/BAT/AEM Python Sim/V0/optimized_grid_dispatch_2024.csv",
        help="Output CSV path",
    )
    parser.add_argument(
        "--grid-emission-factor",
        type=float,
        default=DEFAULT_GRID_EMISSION_KG_PER_KWH,
        help="Grid emissions factor in kgCO2e/kWh used for both import and export.",
    )
    args = parser.parse_args()

    df = pd.read_csv(args.input)

    sales_col = pick_column(df, ["Sales", "sales", "Demand"])
    production_col = pick_column(
        df,
        ["Total Hydropower Production", "Total Production Hydro", "Production Total", "Hydropower Production"],
    )
    price_col = pick_column(df, ["Spot price [Rp/kWh]", "Spot price", "spot_price_rp_per_kwh"])

    spot = df[price_col].astype(float)

    # Cost objective:
    #   import cost = spot + tariff
    #   export gain = spot  -> cost coefficient = -spot
    cost_cfg = ObjectiveConfig(
        name="min_cost",
        import_cost_per_kwh=spot + TARIFF_RP_PER_KWH,
        export_cost_per_kwh=-spot,
        curtail_cost_per_kwh=0.0,
        import_emission_per_kwh=args.grid_emission_factor,
        export_emission_per_kwh=args.grid_emission_factor,
    )

    # Emissions objective:
    #   minimize emissions; import/export both emit equally, curtailment set to zero emissions.
    emissions_cfg = ObjectiveConfig(
        name="min_emissions",
        import_cost_per_kwh=spot + TARIFF_RP_PER_KWH,
        export_cost_per_kwh=-spot,
        curtail_cost_per_kwh=0.0,
        import_emission_per_kwh=args.grid_emission_factor,
        export_emission_per_kwh=args.grid_emission_factor,
    )

    cost_result = run_optimization(df, cost_cfg, production_col, sales_col)

    # Re-run for emissions objective by using emissions as objective surrogate coefficients.
    # Costs are still calculated after dispatch for reporting.
    emissions_obj_cfg = ObjectiveConfig(
        name="min_emissions",
        import_cost_per_kwh=pd.Series(args.grid_emission_factor, index=df.index),
        export_cost_per_kwh=pd.Series(args.grid_emission_factor, index=df.index),
        curtail_cost_per_kwh=0.0,
        import_emission_per_kwh=args.grid_emission_factor,
        export_emission_per_kwh=args.grid_emission_factor,
    )
    emissions_result = run_optimization(df, emissions_obj_cfg, production_col, sales_col)

    out = df.copy()

    out["cost_opt_grid_import_kwh"] = cost_result["grid_import_kwh"]
    out["cost_opt_grid_export_kwh"] = cost_result["grid_export_kwh"]
    out["cost_opt_curtailed_kwh"] = cost_result["curtailed_kwh"]
    out["cost_opt_total_cost_rp"] = (
        (spot + TARIFF_RP_PER_KWH) * out["cost_opt_grid_import_kwh"] - spot * out["cost_opt_grid_export_kwh"]
    )
    out["cost_opt_total_emissions_kgco2e"] = (
        args.grid_emission_factor * (out["cost_opt_grid_import_kwh"] + out["cost_opt_grid_export_kwh"])
    )

    out["emissions_opt_grid_import_kwh"] = emissions_result["grid_import_kwh"]
    out["emissions_opt_grid_export_kwh"] = emissions_result["grid_export_kwh"]
    out["emissions_opt_curtailed_kwh"] = emissions_result["curtailed_kwh"]
    out["emissions_opt_total_cost_rp"] = (
        (spot + TARIFF_RP_PER_KWH) * out["emissions_opt_grid_import_kwh"] - spot * out["emissions_opt_grid_export_kwh"]
    )
    out["emissions_opt_total_emissions_kgco2e"] = (
        args.grid_emission_factor * (out["emissions_opt_grid_import_kwh"] + out["emissions_opt_grid_export_kwh"])
    )

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(output_path, index=False)

    print(f"Input file       : {args.input}")
    print(f"Output file      : {output_path}")
    print(f"Sales column     : {sales_col}")
    print(f"Production column: {production_col}")
    print(f"Spot price column: {price_col}")
    print("\nSummary (annual):")
    print(f"  Cost-opt total cost [Rp]       : {out['cost_opt_total_cost_rp'].sum():,.2f}")
    print(f"  Cost-opt emissions [kgCO2e]    : {out['cost_opt_total_emissions_kgco2e'].sum():,.2f}")
    print(f"  Emissions-opt total cost [Rp]  : {out['emissions_opt_total_cost_rp'].sum():,.2f}")
    print(f"  Emissions-opt emissions [kgCO2e]: {out['emissions_opt_total_emissions_kgco2e'].sum():,.2f}")


if __name__ == "__main__":
    main()
