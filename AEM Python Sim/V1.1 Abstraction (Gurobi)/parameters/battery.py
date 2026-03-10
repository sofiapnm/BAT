#WAITING FOR MALINS FRIENDS REPLY!!!!!! (BKW)
#TECHNICAL AND EMISSION FACTORS HAVE TO BE CHANGED, ECONOMIC MUST BE REVISED, since it takes it form the CDB catalogue
BATTERY_TECHNICAL = {
    "capacity_kwh": 5000.0,
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
    "capex_rp": 65700,
    "annual_opex_rp_per_kwh_year": 1600,
    "degradation_cost_rp_per_kwh_throughput": 0.0,
}

BATTERY_EMISSIONS = {
    # Arbitrary placeholder because your original model did not use battery-specific emissions directly
    "lifecycle_emissions_kgco2_per_kwh_throughput": 0.0,
}
