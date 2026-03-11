EXPORT_TECHNICAL = {
    # Arbitrary placeholder value: not used in your original model yet
    "existing_grid_limit_mw": 4.0,
}

EXPORT_ECONOMIC = {
    "fixed_tariff_rp_per_kwh": 1.08,
    "expansion_cost_rp_per_mw": 5000000.0,
    "power_tariff_rp_per_kw_per_month": 1143.0,
}

EXPORT_EMISSIONS = {
    "export_emissions_credit_kgco2_per_kwh": 0.128, #from William's report+2018, check w Malin
}


def export_price_rp_per_kwh(spot_price_rp_per_kwh):
    return spot_price_rp_per_kwh - EXPORT_ECONOMIC["fixed_tariff_rp_per_kwh"]
