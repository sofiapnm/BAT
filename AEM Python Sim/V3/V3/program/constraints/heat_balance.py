from parameters.heat_pump import HEAT_PUMP_TECHNICAL


def add_heat_balance_constraints(model, vars_dict, heatdemand_kwhth, n):
    """
    Thermal energy balance: woodchip boiler and heat pump jointly meet thermal demand.

    The heat pump converts electricity to heat with fixed COP.
    """
    woodchip_heat = vars_dict["woodchip_boiler_heat_kWhth"]
    heatpump_heat = vars_dict["heatpump_heat_kWhth"]
    heatpump_elec = vars_dict["heatpump_elec_kWh"]
    heatpump_nominal = vars_dict["heatpump_nominal_kWhth"]
    cop = HEAT_PUMP_TECHNICAL["cop"]

    for t in range(n):
        model.addConstr(
            woodchip_heat[t] + heatpump_heat[t] == heatdemand_kwhth[t],
            name=f"heat_balance[{t}]",
        )
        model.addConstr(
            heatpump_heat[t] == cop * heatpump_elec[t],
            name=f"heatpump_cop[{t}]",
        )
        model.addConstr(
            heatpump_heat[t] <= heatpump_nominal,
            name=f"heatpump_nominal_limit[{t}]",
        )
