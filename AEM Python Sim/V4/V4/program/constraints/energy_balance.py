from parameters.battery import BATTERY_TECHNICAL
from parameters.general import GENERAL


def add_energy_balance_constraints(model, vars_dict, production_kwh, elecdemand_kwh, n):
    grid_import = vars_dict["grid_import"]
    grid_export = vars_dict["grid_export"]
    batt_charge = vars_dict["batt_charge"]
    batt_discharge = vars_dict["batt_discharge"]
    heatpump_elec = vars_dict["heatpump_elec_kWh"]

    discharge_eff = BATTERY_TECHNICAL["discharge_eff"]

    for t in range(n):
        model.addConstr(
            production_kwh[t]
            + grid_import[t]
            + discharge_eff * batt_discharge[t]
            == elecdemand_kwh[t] + grid_export[t] + batt_charge[t] + heatpump_elec[t],
            name=f"energy_balance[{t}]",
        )