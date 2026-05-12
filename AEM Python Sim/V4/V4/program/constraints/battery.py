from parameters.battery import BATTERY_TECHNICAL
from parameters.general import GENERAL


def add_battery_constraints(model, vars_dict, n, init_soc_kwh, final_soc_kwh):
    battery_installed = vars_dict["battery_installed"]
    batt_charge = vars_dict["batt_charge"]
    batt_discharge = vars_dict["batt_discharge"]
    soc = vars_dict["soc"]

    delta_t_h = GENERAL["delta_t_h"]
    charge_eff = BATTERY_TECHNICAL["charge_eff"]

    max_charge_kwh = BATTERY_TECHNICAL["max_charge_power_kw"] * delta_t_h
    max_discharge_kwh = BATTERY_TECHNICAL["max_discharge_power_kw"] * delta_t_h
    soc_min_kwh = vars_dict["soc_min_kwh"]
    soc_max_kwh = vars_dict["soc_max_kwh"]

    for t in range(n):
        model.addConstr(
            batt_charge[t] <= max_charge_kwh * battery_installed,
            name=f"charge_rate_limit[{t}]",
        )

        model.addConstr(
            batt_discharge[t] <= max_discharge_kwh * battery_installed,
            name=f"discharge_rate_limit[{t}]",
        )

        model.addConstr(
            soc[t] >= soc_min_kwh * battery_installed,
            name=f"soc_min[{t}]",
        )

        model.addConstr(
            soc[t] <= soc_max_kwh * battery_installed,
            name=f"soc_max[{t}]",
        )

        if t == 0:
            model.addConstr(
                soc[t]
                == init_soc_kwh * battery_installed
                + charge_eff * batt_charge[t]
                - batt_discharge[t],
                name=f"soc_transition[{t}]",
            )
        else:
            model.addConstr(
                soc[t]
                == soc[t - 1] + charge_eff * batt_charge[t] - batt_discharge[t],
                name=f"soc_transition[{t}]",
            )

    if final_soc_kwh is not None:
        model.addConstr(
            soc[n - 1] == final_soc_kwh * battery_installed,
            name="final_soc",
        )