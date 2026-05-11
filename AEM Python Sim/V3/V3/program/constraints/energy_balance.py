from parameters.battery import BATTERY_TECHNICAL


def add_energy_balance_constraints(model, vars_dict, production_kwh, demand_kwh, n):
    grid_import = vars_dict["grid_import"]
    grid_export = vars_dict["grid_export"]
    batt_charge = vars_dict["batt_charge"]
    batt_discharge = vars_dict["batt_discharge"]

    discharge_eff = BATTERY_TECHNICAL["discharge_eff"]

    for t in range(n):
        model.addConstr(
            production_kwh[t]
            + grid_import[t]
            + discharge_eff * batt_discharge[t]
            == demand_kwh[t] + grid_export[t] + batt_charge[t],
            name=f"energy_balance[{t}]",
        )