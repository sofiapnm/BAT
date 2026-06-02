RUNOFRIVER_ECONOMIC = {
    # Revenue when run-of-river generation is used locally for electrical demand.
    # Export revenue is modeled separately as spot price minus the fixed tariff.
    # RoR has no local 'profit' — it incurs a marginal cost when generated
    "profit_rp_per_kwh": 0.0,
    # Marginal cost incurred by run-of-river generation (Rp/kWh)
    "cost_rp_per_kwh": 6.0,
    # Load revenue paid for meeting electrical demand (source-agnostic), Rp/kWh
    "load_revenue_rp_per_kwh": 12.5,
    # "profit_rp_per_month": 450.0 + 967.0, #967 rp/month uncertain (grid usage)
}

RUNOFRIVER_EMISSIONS = {
    "emissions_kgco2eq_per_kwh_generated": 0.003617,
}
