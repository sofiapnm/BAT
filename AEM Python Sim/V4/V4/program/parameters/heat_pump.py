"""
Heat pump technical, economic, and emissions assumptions.

The optimization model uses a linear heat-pump representation:

    Q_HP[t] = COP[m(t)] · E_HP[t]

where:
    - Q_HP[t] is useful heat output [kWh_th per timestep]
    - E_HP[t] is electricity use [kWh_el per timestep]
    - COP[m(t)] is the month-dependent coefficient of performance

The device is also constrained by a maximum thermal output cap, an optional
minimum modulation level, and an inter-temporal ramp limit.
"""

HEAT_PUMP_TECHNICAL = {
    # Monthly COP profile (Jan-Dec), used as COP[m(t)] in the operating equations.
    "cop_monthly": [2.95, 2.9, 3.05, 3.2, 3.35, 3.55, 3.85, 3.85, 3.7, 3.55, 3.35, 3.1],
    # Maximum thermal output per timestep [kWh_th per timestep].
    # With delta_t = 0.25 h, this corresponds to 7000 kW_th.
    "hp_heat_max": 1750.0,
    # Maximum change in electric input per timestep [kWh_el per timestep].
    # This creates a continuous ramping limit between adjacent timesteps.
    "ramp_limit_kwh_per_timestep": 0.125,
    
    # If True, enforce exact on/off modulation with a binary variable.
    # Kept False by default so full-year solves remain tractable.
    "enforce_modulation_binary": False,
    # Minimum stable electric input fraction while running [0..1].
    # Only active when enforce_modulation_binary=True.
    "modulation_min_frac": 0.2,
}

HEAT_PUMP_ECONOMIC = {
    # One-off CAPEX in rappen, proportional to nominal thermal capacity.
    "cost_rp_per_kwth_nominal": 56759.718,
    # One-off fixed CAPEX in rappen.
    "cost_rp_fixed": 17233.943,
    # Assumed technical/economic lifetime for amortization [years].
    "heatpump_lifetime_years": 30,
}

HEAT_PUMP_ECONOMIC["annual_opex_rp_per_kwth_year"] = (
    0.01 * HEAT_PUMP_ECONOMIC["cost_rp_per_kwth_nominal"]
)

HEAT_PUMP_ECONOMIC["annual_capex_rp_per_kwth_amortized"] = (
    HEAT_PUMP_ECONOMIC["cost_rp_per_kwth_nominal"]
    / HEAT_PUMP_ECONOMIC["heatpump_lifetime_years"]
)

HEAT_PUMP_ECONOMIC["annual_capex_rp_fixed_amortized"] = (
    HEAT_PUMP_ECONOMIC["cost_rp_fixed"]
    / HEAT_PUMP_ECONOMIC["heatpump_lifetime_years"]
)

HEAT_PUMP_EMISSIONS = {
    # Direct operational emissions factor on useful heat output.
    "emissions_kgco2eq_per_kwhth": 0.148,
}