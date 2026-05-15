"""
Pit Thermal Energy Storage (PTES) Parameters

PTES is an underground thermal energy storage system used to buffer heat supply
and demand, enabling temporal flexibility in the thermal system.
"""

# Technical parameters
PTES_TECHNICAL = {
    "kwhth_per_m3": 137.84,  # Energy density: kWh_thermal per cubic meter of storage volume
    "efficiency": 0.8,  # Round-trip efficiency (applied to charging process)
    "discharge_power_kwth":21464.328,  # Maximum discharge thermal power [kW_th]
    "lifetime_years": 30,  # Storage system lifetime for cost amortization
}

# Economic parameters
PTES_ECONOMIC = {
    # Specific cost (CHF per m^3) coefficients: specific_cost_chf_per_m3 = coeff * V^exp
    # User-provided specific-cost formula: 6555.58 * V^-0.424 (CHF/m^3)
    "specific_cost_chf_coeff": 6555.58,
    "specific_cost_exp": -0.424,
    # Lifetime used to annualize CAPEX (years)
    "lifetime_years": 30,

    # Note: total CAPEX CHF = specific_cost_chf_per_m3 * V (m^3)
    # Annualized cost in rappen will be computed in objective.py as:
    # (specific_cost_chf_per_m3 * V * 100) / lifetime_years
    # Annual OPEX as a percentage of total CAPEX (e.g., 0.01 = 1% per year)
    "annual_opex_percentage_of_capex": 0.01,
}

# Small penalty per kWh throughput (charge + discharge) to discourage excessive cycling
# Units: rappen per kWh
PTES_ECONOMIC["throughput_penalty_rp_per_kwh"] = 0.001

# Emissions parameters
PTES_EMISSIONS = {
    "emissions_kgco2eq_per_m3": 0.002385,  # Embodied carbon per cubic meter of storage
}
