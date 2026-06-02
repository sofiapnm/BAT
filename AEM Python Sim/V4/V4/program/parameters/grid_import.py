IMPORT_TECHNICAL = {
    "existing_grid_limit_mw": 4.0,
}

IMPORT_ECONOMIC = {
    "expansion_cost_rp_per_mw": 5000000.0,
    "fixed_tariff_high_grid_use_rp_per_kwh": 1.08,
    "fixed_tariff_low_grid_use_rp_per_kwh": 3.28,
    "annual_grid_use_threshold_h": 3500.0,
    "power_tariff_high_grid_use_rp_per_kw_per_month": 1143.0,
    "power_tariff_low_grid_use_rp_per_kw_per_month": 502.0,
}

IMPORT_EMISSIONS = {
    "grid_emissions_kgco2_per_kwh": 0.128, #from William's report+2018, check w Malin
}


def annual_grid_use_hours(total_import_kwh, total_export_kwh):
    grid_capacity_kw = IMPORT_TECHNICAL["existing_grid_limit_mw"] * 1000.0
    return (total_import_kwh + total_export_kwh) / grid_capacity_kw


def import_fixed_tariff_rp_per_kwh(annual_grid_use_h):
    return IMPORT_ECONOMIC["fixed_tariff_high_grid_use_rp_per_kwh"]


def power_tariff_rp_per_kw_per_month(annual_grid_use_h):
    return IMPORT_ECONOMIC["power_tariff_high_grid_use_rp_per_kw_per_month"]


def import_price_rp_per_kwh(spot_price_rp_per_kwh, annual_grid_use_h):
    return spot_price_rp_per_kwh + import_fixed_tariff_rp_per_kwh(annual_grid_use_h)
