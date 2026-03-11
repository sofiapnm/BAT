IMPORT_TECHNICAL = {
    # Arbitrary placeholder value: not used in your original model yet
    "existing_grid_limit_mw": 4.0,
}

IMPORT_ECONOMIC = {
    # The time-varying import price profile still comes from the CSV.
    "expansion_cost_rp_per_mw": 5000000.0,
    "fixed_tariff_rp_per_kwh": 1.08,
    "power_tariff_rp_per_kw_per_month": 1143.0,
}

IMPORT_EMISSIONS = {
    "grid_emissions_kgco2_per_kwh": 0.128, #from William's report+2018, check w Malin
}


def import_price_rp_per_kwh(spot_price_rp_per_kwh):
    return spot_price_rp_per_kwh + IMPORT_ECONOMIC["fixed_tariff_rp_per_kwh"]
