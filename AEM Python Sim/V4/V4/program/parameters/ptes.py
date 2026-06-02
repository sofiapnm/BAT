PTES_MODE = "always_on"
# options for PTES mode: optional, always_on, always_off

# Technical parameters
PTES_TECHNICAL = {
    "kwhth_per_m3": 137.84,  # energy density: kWh_thermal per cubic meter of storage volume
    "volume_m3_min": 10.22,
    "volume_m3_max": 50000.0,
    "efficiency": 0.8,  # round-trip efficiency (applied to charging process)
    "discharge_power_kwth":21464.328,  # Maximum discharge thermal power [kW_th]
    "lifetime_years": 30,  # storage system lifetime for cost amortization
}

# Economic parameters
PTES_ECONOMIC = {
    # specific cost (CHF per m^3) coefficients: specific_cost_chf_per_m3 = coeff * V^exp
    # user-provided specific-cost formula: 6555.58 * V^-0.424 (CHF/m^3)
    "specific_cost_chf_coeff": 6555.58,
    "specific_cost_exp": -0.424,
    # lifetime used to annualize CAPEX (years)
    "lifetime_years": 30,

    # note: total CAPEX CHF = specific_cost_chf_per_m3 * V (m^3)
    # annualized cost in rappen will be computed in objective.py as:
    # (specific_cost_chf_per_m3 * V * 100) / lifetime_years
    # annual OPEX as a percentage of total CAPEX (e.g., 0.01 = 1% per year)
    "annual_opex_percentage_of_capex": 0.01,
}

# small penalty per kWh throughput (charge + discharge) to discourage excessive cycling
PTES_ECONOMIC["throughput_penalty_rp_per_kwh"] = 0.001

# Emissions parameters
PTES_EMISSIONS = {
    "emissions_kgco2eq_per_m3": 0.002385,  # embodied carbon per cubic meter of storage
}
