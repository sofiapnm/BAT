from parameters.battery import BATTERY_TECHNICAL
from parameters.general import GENERAL


def add_battery_constraints(model, vars_dict, n, init_soc_kwh, final_soc_kwh):
    battery_installed = vars_dict["battery_installed"]
    batt_charge = vars_dict["batt_charge"]
    batt_discharge = vars_dict["batt_discharge"]
    soc = vars_dict["soc"]

    delta_t_h = GENERAL["delta_t_h"]
    charge_eff = BATTERY_TECHNICAL["charge_eff"]

    # Use variable capacity to derive power and SOC bounds.
    capacity = vars_dict["battery_capacity_kwh"]
    # Power is half the energy capacity (kW). Convert to kWh per timestep by multiplying delta_t_h.
    charge_coeff = 0.5 * delta_t_h
    discharge_coeff = 0.5 * delta_t_h
    soc_min_frac = BATTERY_TECHNICAL["soc_min_frac"]
    soc_max_frac = BATTERY_TECHNICAL["soc_max_frac"]

    for t in range(n):

        # Charge/discharge limits scale with capacity variable (linear constraints)
        model.addConstr(
            batt_charge[t] <= charge_coeff * capacity,
            name=f"charge_rate_limit[{t}]",
        )

        model.addConstr(
            batt_discharge[t] <= discharge_coeff * capacity,
            name=f"discharge_rate_limit[{t}]",
        )

        # SOC bounds as fractions of capacity
        model.addConstr(
            soc[t] >= soc_min_frac * capacity,
            name=f"soc_min[{t}]",
        )

        model.addConstr(
            soc[t] <= soc_max_frac * capacity,
            name=f"soc_max[{t}]",
        )

        if t == 0:
            # Initial SOC expressed as fraction of the chosen capacity
            model.addConstr(
                soc[t]
                == BATTERY_TECHNICAL["soc_init_frac"] * capacity
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

    # Enforce end SOC as fraction of capacity if requested
    if BATTERY_TECHNICAL.get("soc_end_frac", None) is not None:
        model.addConstr(
            soc[n - 1] == BATTERY_TECHNICAL["soc_end_frac"] * capacity,
            name="final_soc",
        )