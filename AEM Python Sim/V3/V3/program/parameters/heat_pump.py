HEAT_PUMP_TECHNICAL = {
    # Constant COP (deprecated: use monthly profile instead)
    "cop": 3.0,
    # Monthly COP profile (jan-dec)
    "cop_monthly": [2.95, 2.9, 3.05, 3.2, 3.35, 3.55, 3.85, 3.85, 3.7, 3.55, 3.35, 3.1],
    # Maximum electric input per timestep [kWh_el].
    # For nominal power output, this can be reverse engineered from COP values.
    "hp_elec_max": 1644.3333333333,
    # Minimum stable electric input fraction while running [0..1]
    "modulation_min_frac": 0.2,
    # Maximum change in electric input per timestep [kWh_el].
    "ramp_limit_kwh_per_timestep": 0.125,
    # If True, enforce exact modulation with binary on/off per timestep.
    # Keep False for full-year runs to avoid very large MILP solve times.
    "enforce_modulation_binary": False,
}

HEAT_PUMP_ECONOMIC = {
    # Annual fixed cost in rappen based on nominal thermal capacity.
    "cost_rp_per_kwth_nominal": 67.744,
    "cost_rp_fixed": 18.831,
}

HEAT_PUMP_EMISSIONS = {
    # Direct emissions factor on useful heat output.
    "emissions_kgco2eq_per_kwhth": 0.148,
}