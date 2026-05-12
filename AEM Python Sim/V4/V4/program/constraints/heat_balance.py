import pandas as pd
from parameters.heat_pump import HEAT_PUMP_TECHNICAL


def add_heat_balance_constraints(model, vars_dict, heatdemand_kwhth, n, datetime_series=None):
    """
    Thermal energy balance: woodchip boiler and heat pump jointly meet thermal demand.

    The heat pump converts electricity to heat with monthly-varying COP.
    """
    woodchip_heat = vars_dict["woodchip_boiler_heat_kWhth"]
    heatpump_heat = vars_dict["heatpump_heat_kWhth"]
    heatpump_elec = vars_dict["heatpump_elec_kWh"]
    heatpump_nominal = vars_dict["heatpump_nominal_kWhth"]
    cop_monthly = HEAT_PUMP_TECHNICAL["cop_monthly"]
    hp_elec_max = HEAT_PUMP_TECHNICAL["hp_elec_max"]
    ramp_limit_kwh_per_timestep = HEAT_PUMP_TECHNICAL["ramp_limit_kwh_per_timestep"]
    modulation_min_frac = HEAT_PUMP_TECHNICAL["modulation_min_frac"]
    enforce_modulation_binary = HEAT_PUMP_TECHNICAL.get("enforce_modulation_binary", False)
    heatpump_on = vars_dict.get("heatpump_on")

    # Extract month from datetime if provided, otherwise use constant COP
    if datetime_series is not None:
        months_raw = pd.to_datetime(datetime_series).dt.month.values
        # Handle NaN values by defaulting to January
        months = []
        for m in months_raw:
            try:
                if pd.isna(m):
                    months.append(1)
                else:
                    months.append(int(m))
            except:
                months.append(1)
    else:
        months = [1] * n  # Default to January COP if no datetime

    for t in range(n):
        model.addConstr(
            woodchip_heat[t] + heatpump_heat[t] == heatdemand_kwhth[t],
            name=f"heat_balance[{t}]",
        )
        # Use month-dependent COP (month is 1-12, cop_monthly is 0-indexed)
        cop_t = cop_monthly[months[t] - 1]
        model.addConstr(
            heatpump_heat[t] == cop_t * heatpump_elec[t],
            name=f"heatpump_cop[{t}]",
        )
        model.addConstr(
            heatpump_elec[t] <= hp_elec_max,
            name=f"heatpump_pel_max[{t}]",
        )
        if t > 0:
            model.addConstr(
                heatpump_elec[t] - heatpump_elec[t - 1] <= ramp_limit_kwh_per_timestep,
                name=f"heatpump_ramp_up[{t}]",
            )
            model.addConstr(
                heatpump_elec[t - 1] - heatpump_elec[t] <= ramp_limit_kwh_per_timestep,
                name=f"heatpump_ramp_down[{t}]",
            )
        if enforce_modulation_binary and heatpump_on is not None:
            model.addConstr(
                heatpump_elec[t] <= hp_elec_max * heatpump_on[t],
                name=f"heatpump_pel_max_on[{t}]",
            )
            model.addConstr(
                heatpump_elec[t] >= modulation_min_frac * hp_elec_max * heatpump_on[t],
                name=f"heatpump_modulation_min[{t}]",
            )
        model.addConstr(
            heatpump_heat[t] <= cop_t * hp_elec_max,
            name=f"heatpump_qhp_capacity[{t}]",
        )
        model.addConstr(
            heatpump_heat[t] <= heatpump_nominal,
            name=f"heatpump_nominal_limit[{t}]",
        )
