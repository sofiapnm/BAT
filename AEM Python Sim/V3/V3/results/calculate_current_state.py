"""
Calculate the current state (baseline) without battery implementation.

The current state represents pure run-of-river generation:
- Production that meets load gets runofriver_profit_rp (6.5 RP/kWh)
- Production that exceeds load is exported at grid export prices
- Uses grid export economic parameters for excess generation
"""

import pandas as pd
from pathlib import Path

# Add program directory to path to import modules
program_dir = Path(__file__).resolve().parents[0] / ".." / "program"
import sys
sys.path.insert(0, str(program_dir))

from parameters.runofriver import RUNOFRIVER_ECONOMIC, RUNOFRIVER_EMISSIONS
from parameters.grid_export import EXPORT_EMISSIONS, export_price_rp_per_kwh
from parameters.grid_import import IMPORT_EMISSIONS
from parameters.general import GENERAL


def calculate_current_state(
    kwh_results_path="/workspaces/BAT/AEM Python Sim/V3/V3/results/kWh Results.csv",
    output_path="/workspaces/BAT/AEM Python Sim/V3/V3/results/pareto_currentstate_annual_summary.csv",
):
    """
    Calculate current state economics and emissions without battery.
    
    Current state = run-of-river generation + grid for demand/export management
    - No battery installed
    - Production for local load: earns runofriver_profit_rp
    - Excess production: exported at grid export price
    """
    
    # Load data
    kwh_df = pd.read_csv(kwh_results_path)
    
    production_kwh = kwh_df["production_kWh"].values
    load_kwh = kwh_df["load_kWh"].values
    spot_price_rp_per_kwh = kwh_df["spot price [Rp/kWh]"].values
    
    # Get parameters
    runofriver_profit_rp_per_kwh = RUNOFRIVER_ECONOMIC["profit_rp_per_kwh"]
    runofriver_emissions_per_kwh = RUNOFRIVER_EMISSIONS["emissions_kgco2eq_per_kwh_generated"]
    grid_emissions_per_kwh = IMPORT_EMISSIONS["grid_emissions_kgco2_per_kwh"]
    export_emissions_per_kwh = EXPORT_EMISSIONS["export_emissions_kgco2_per_kwh"]
    
    # Annual grid use hours (for tariff determination)
    # In current state: no battery, so grid use = grid import + grid export directly
    # Estimate: with no battery, import ≈ demand - production (when prod < demand)
    #          export ≈ production - demand (when prod > demand)
    grid_import_kwh = []
    grid_export_kwh = []
    prod_for_local_kwh = []
    prod_for_export_kwh = []
    
    for i in range(len(production_kwh)):
        prod = production_kwh[i]
        demand = load_kwh[i]
        
        # Production allocated to meet local demand
        local_prod = min(prod, demand)
        prod_for_local_kwh.append(local_prod)
        
        # Excess production goes to export
        export_prod = max(0, prod - demand)
        prod_for_export_kwh.append(export_prod)
        
        # Grid import: only if production can't meet demand
        import_kwh = max(0, demand - prod)
        grid_import_kwh.append(import_kwh)
        
        # Grid export: excess production
        grid_export_kwh.append(export_prod)
    
    # Convert to arrays for calculation
    prod_for_local_kwh = pd.Series(prod_for_local_kwh)
    prod_for_export_kwh = pd.Series(prod_for_export_kwh)
    grid_import_kwh = pd.Series(grid_import_kwh)
    grid_export_kwh = pd.Series(grid_export_kwh)
    
    # Annual totals
    annual_production_kwh = float(pd.Series(production_kwh).sum())
    annual_grid_import_kwh = float(grid_import_kwh.sum())
    annual_grid_export_kwh = float(grid_export_kwh.sum())
    annual_grid_use_h = (annual_grid_import_kwh + annual_grid_export_kwh) / (4.0 * 1000.0)  # 4 MW grid limit
    
    # Determine tariff tier
    annual_grid_use_threshold_h = 3500.0
    high_use = annual_grid_use_h > annual_grid_use_threshold_h
    
    # Calculate revenues
    annual_runofriver_profit_rp = float((prod_for_local_kwh * runofriver_profit_rp_per_kwh).sum())
    
    # Grid import cost: spot price + import tariff
    from parameters.grid_import import import_price_rp_per_kwh
    import_price_series = pd.Series(
        [import_price_rp_per_kwh(pd.Series(spot_price_rp_per_kwh), annual_grid_use_h).iloc[i] 
         if hasattr(import_price_rp_per_kwh(pd.Series(spot_price_rp_per_kwh), annual_grid_use_h), 'iloc')
         else import_price_rp_per_kwh(spot_price_rp_per_kwh[i], annual_grid_use_h)
         for i in range(len(spot_price_rp_per_kwh))]
    )
    annual_import_cost_rp = float((grid_import_kwh * import_price_rp_per_kwh(pd.Series(spot_price_rp_per_kwh), annual_grid_use_h)).sum())
    
    # Grid export revenue: spot price - export tariff
    export_price_series = pd.Series(
        [export_price_rp_per_kwh(spot_price_rp_per_kwh[i], annual_grid_use_h)
         for i in range(len(spot_price_rp_per_kwh))]
    )
    annual_export_revenue_rp = float((grid_export_kwh * export_price_series).sum())
    
    # Total cost burden = import cost - export revenue - runofriver profit
    annual_cost_burden_rp = annual_import_cost_rp - annual_export_revenue_rp - annual_runofriver_profit_rp
    annual_cost_burden_chf = annual_cost_burden_rp / 100.0
    
    # Net annual profit (inverse of cost burden)
    net_annual_profit_chf = -annual_cost_burden_chf
    
    # Calculate emissions
    annual_import_emissions_kgco2 = float((grid_import_kwh * grid_emissions_per_kwh).sum())
    annual_export_emissions_kgco2 = float((grid_export_kwh * export_emissions_per_kwh).sum())
    annual_runofriver_emissions_kgco2 = annual_production_kwh * runofriver_emissions_per_kwh
    annual_emissions_burden_kgco2 = (
        annual_import_emissions_kgco2
        + annual_export_emissions_kgco2
        + annual_runofriver_emissions_kgco2
    )
    
    # Power tariff cost (current state has no battery, so no monthly peak charges)
    annual_power_cost_rp = 0.0
    annual_power_cost_chf = 0.0
    
    # Determine power tariff rate (for reference)
    from parameters.grid_import import power_tariff_rp_per_kw_per_month
    power_tariff = power_tariff_rp_per_kw_per_month(annual_grid_use_h)
    power_tariff_chf_per_kw_per_month = power_tariff / 100.0
    
    # Create current state dataframe
    current_state_data = {
        'annual_cost_burden_chf': [annual_cost_burden_chf],
        'net_annual_profit_chf': [net_annual_profit_chf],
        'annual_import_emissions_kgco2': [annual_import_emissions_kgco2],
        'annual_export_emissions_kgco2': [annual_export_emissions_kgco2],
        'annual_runofriver_emissions_kgco2': [annual_runofriver_emissions_kgco2],
        'annual_emissions_burden_kgco2': [annual_emissions_burden_kgco2],
        'annual_grid_import_kwh': [annual_grid_import_kwh],
        'annual_grid_export_kwh': [annual_grid_export_kwh],
        'annual_grid_use_h': [annual_grid_use_h],
        'annual_production_kwh': [annual_production_kwh],
        'annual_import_cost_chf': [annual_import_cost_rp / 100.0],
        'annual_export_revenue_chf': [annual_export_revenue_rp / 100.0],
        'annual_runofriver_profit_chf': [annual_runofriver_profit_rp / 100.0],
        'annual_power_cost_chf': [annual_power_cost_chf],
        'power_tariff_chf_per_kw_per_month': [power_tariff_chf_per_kw_per_month],
        'interval_count': [len(kwh_df)],
    }
    
    current_state_df = pd.DataFrame(current_state_data)
    
    # Save to CSV
    output_parent = Path(output_path).parent
    output_parent.mkdir(parents=True, exist_ok=True)
    current_state_df.to_csv(output_path, index=False)
    
    print("Current State Calculation")
    print("=" * 70)
    print(f"Annual Production: {annual_production_kwh:,.2f} kWh")
    print(f"  - For local load: {prod_for_local_kwh.sum():,.2f} kWh @ {runofriver_profit_rp_per_kwh} RP/kWh")
    print(f"  - For export: {prod_for_export_kwh.sum():,.2f} kWh")
    print()
    print(f"Annual Grid Import: {annual_grid_import_kwh:,.2f} kWh")
    print(f"Annual Grid Export: {annual_grid_export_kwh:,.2f} kWh")
    print(f"Annual Grid Use Hours: {annual_grid_use_h:,.2f} h")
    print(f"Tariff Tier: {'High Use' if high_use else 'Low Use'}")
    print()
    print(f"Annual Import Cost: {annual_import_cost_rp / 100.0:,.2f} CHF")
    print(f"Annual Export Revenue: {annual_export_revenue_rp / 100.0:,.2f} CHF")
    print(f"Annual Run-of-River Profit: {annual_runofriver_profit_rp / 100.0:,.2f} CHF")
    print()
    print(f"Annual Cost Burden: {annual_cost_burden_chf:,.2f} CHF")
    print(f"Net Annual Profit: {net_annual_profit_chf:,.2f} CHF")
    print()
    print(f"Annual Import Emissions: {annual_import_emissions_kgco2:,.2f} kgCO2")
    print(f"Annual Export Emissions: {annual_export_emissions_kgco2:,.2f} kgCO2")
    print(f"Annual Run-of-River Emissions: {annual_runofriver_emissions_kgco2:,.2f} kgCO2")
    print(f"Annual Emissions Burden: {annual_emissions_burden_kgco2:,.2f} kgCO2")
    print()
    print(f"Saved to: {output_path}")
    print("=" * 70)
    
    return current_state_df


if __name__ == "__main__":
    calculate_current_state()
