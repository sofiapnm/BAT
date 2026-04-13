#for capacity of 1-2MW, the following economic costs can be considered as correct
#TECHNICAL AND EMISSION FACTORS HAVE TO BE REVISED
BATTERY_TECHNICAL = {
    "capacity_kwh": 200.0, 
    "soc_min_frac": 0.05,
    "soc_max_frac": 0.95,
    "soc_init_frac": 0.50,
    "soc_end_frac": 0.50,
    "max_charge_power_kw": 2000.0, #ask bkw for details?
    "max_discharge_power_kw": 2000.0, #ask bkw for details?
    "charge_eff": 0.95,
    "discharge_eff": 0.95,
}

BATTERY_ECONOMIC = {#
    "capex_rp_kwh": 60000,
    "degradation_cost_rp_per_kwh_throughput": 0.0,
}

BATTERY_ECONOMIC["annual_opex_rp_per_kwh_year"] = (
    0.01 * BATTERY_ECONOMIC["capex_rp_kwh"]
)


#turn from kg to g...?
BATTERY_EMISSIONS = {
    # Arbitrary placeholder because your original model did not use battery-specific emissions directly
    "lifecycle_emissions_kgco2_per_kwh_throughput": 0.0,
}
