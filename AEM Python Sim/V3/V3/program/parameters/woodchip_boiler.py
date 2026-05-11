WOODCHIP_BOILER_TECHNICAL = {
    # NOTE: heat_supply_share_of_demand is now a decision variable (woodchip_heat_supply_share[t])
    # This allows the optimization to choose the woodchip contribution to thermal demand.
    # As additional heat sources are added (solar thermal, heat pump, etc.), they will each
    # have their own share variables, and together they will optimize to meet thermal demand.
}

WOODCHIP_BOILER_ECONOMIC = {
    # Cost of woodchip heat production per useful heat output [Rp/kWh_th]
    "cost_rp_per_kwhth_useful": 5.539,
}

WOODCHIP_BOILER_EMISSIONS = {
    "emissions_kgco2eq_per_kwhth": 0.3272,
}
