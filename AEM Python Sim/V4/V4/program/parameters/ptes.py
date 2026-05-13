"""
Pit Thermal Energy Storage (PTES) Parameters

PTES is an underground thermal energy storage system used to buffer heat supply
and demand, enabling temporal flexibility in the thermal system.
"""

# Technical parameters
PTES_TECHNICAL = {
    "kwhth_per_m3": 137.84,  # Energy density: kWh_thermal per cubic meter of storage volume
    "efficiency": 0.8,  # Round-trip efficiency (applied to charging process)
    "lifetime_years": 30,  # Storage system lifetime for cost amortization
}

# Economic parameters
PTES_ECONOMIC = {
    "cost_chf_coeff": 8386.684,  # CHF coefficient for cost function
    "cost_chf_exp": -0.424,  # Exponent for cost function: cost_CHF = coeff * V^exp
    "cost_rp_per_year_factor": 838668.4 / 30,  # Converted to rappen and annualized

    # Positive exponent ensures larger storage gets cheaper per-unit cost, but total cost increases
}

# Emissions parameters
PTES_EMISSIONS = {
    "emissions_kgco2eq_per_m3": 0.002385,  # Embodied carbon per cubic meter of storage
}
