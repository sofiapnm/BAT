def add_heat_balance_constraints(model, vars_dict, heatdemand_kwhth, n):
    """
    Thermal energy balance: link woodchip heat supply (decision) to thermal demand.
    
    Currently, woodchip boiler is the only heat source. As additional sources are added
    (solar thermal, heat pump, etc.), each will have its own decision variable and share,
    and the constraint will evolve to:
      woodchip_heat[t] + solar_heat[t] + hp_heat[t] + ... == heatdemand_kwhth[t]
    """
    woodchip_heat = vars_dict["woodchip_boiler_heat_kWhth"]
    woodchip_share = vars_dict["woodchip_heat_supply_share"]

    for t in range(n):
        model.addConstr(
            woodchip_heat[t] == woodchip_share[t] * heatdemand_kwhth[t],
            name=f"heat_balance[{t}]",
        )
