BATTERY_TECHNICAL = {
    "capacity_kwh": 4000.0,
    "soc_min_frac": 0.05,
    "soc_max_frac": 0.95,
    "soc_init_frac": 0.50,
    "soc_end_frac": 0.50,
    "max_charge_power_kw": 2000.0,
    "max_discharge_power_kw": 2000.0,
    "charge_eff": 0.95,
    "discharge_eff": 0.95,
}

BATTERY_ECONOMIC = {
    "throughput_cost_rp_per_kwh": 0.02,
}

BATTERY_EMISSIONS = {
    # Arbitrary placeholder because your original model did not use battery-specific emissions directly
    "lifecycle_emissions_kgco2_per_kwh_throughput": 0.0,
}