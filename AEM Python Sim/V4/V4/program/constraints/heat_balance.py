import pandas as pd
from parameters.heat_pump import HEAT_PUMP_TECHNICAL
from parameters.ptes import PTES_TECHNICAL


def add_heat_balance_constraints(model, vars_dict, heatdemand_kwhth, n, datetime_series=None):
    """
    Add thermal balance and heat-pump operating constraints.

    Heat balance:

        Q_woodchip[t] + Q_HP[t] + Q_PTES_dis[t] = Q_demand[t] + Q_PTES_ch[t]

    Heat-pump conversion:

        Q_HP[t] = COP[m(t)] · E_HP[t]

    Thermal cap:

        0 ≤ Q_HP[t] ≤ Q_HP,max

    Equivalent electric input bound:

        0 ≤ E_HP[t] ≤ Q_HP,max / COP[m(t)]

    Ramp constraint:

        |E_HP[t] - E_HP[t-1]| ≤ ramp_limit

    Optional exact modulation (disabled by default):

        modulation_min_frac · (Q_HP,max / COP[m(t)]) · y[t] ≤ E_HP[t] ≤ (Q_HP,max / COP[m(t)]) · y[t]

    With enforce_modulation_binary=False, the model behaves as a continuous
    modulating unit that can operate anywhere between zero and its upper limit.
    """
    woodchip_heat = vars_dict["woodchip_boiler_heat_kWhth"]
    heatpump_heat = vars_dict["heatpump_heat_kWhth"]
    heatpump_elec = vars_dict["heatpump_elec_kWh"]
    heatpump_nominal = vars_dict["heatpump_nominal_kWhth"]
    
    # PTES variables
    ptes_charge = vars_dict["ptes_charge_kWhth"]
    ptes_discharge = vars_dict["ptes_discharge_kWhth"]
    ptes_soc = vars_dict["ptes_soc_kWhth"]
    ptes_volume = vars_dict["ptes_volume_m3"]
    
    # PTES technical parameters
    ptes_efficiency = PTES_TECHNICAL["efficiency"]
    kwhth_per_m3 = PTES_TECHNICAL["kwhth_per_m3"]
    
    # Heat pump parameters
    cop_monthly = HEAT_PUMP_TECHNICAL["cop_monthly"]
    hp_heat_max = HEAT_PUMP_TECHNICAL["hp_heat_max"]
    ramp_limit_kwh_per_timestep = HEAT_PUMP_TECHNICAL["ramp_limit_kwh_per_timestep"]
    modulation_min_frac = HEAT_PUMP_TECHNICAL["modulation_min_frac"]
    enforce_modulation_binary = HEAT_PUMP_TECHNICAL.get("enforce_modulation_binary", False)
    heatpump_on = vars_dict.get("heatpump_on")

    # Extract month from datetime if provided, otherwise use constant COP.
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
        # ===== HEAT BALANCE WITH PTES =====
        model.addConstr(
            woodchip_heat[t] + heatpump_heat[t] + ptes_discharge[t] 
            == heatdemand_kwhth[t] + ptes_charge[t],
            name=f"heat_balance_with_ptes[{t}]",
        )

        # ===== HEAT PUMP CONSTRAINTS =====
        # Q_HP[t] = COP[m(t)] * E_HP[t]
        cop_t = cop_monthly[months[t] - 1]
        model.addConstr(
            heatpump_heat[t] == cop_t * heatpump_elec[t],
            name=f"heatpump_cop[{t}]",
        )
        
        # Heat-pump output cap: the variable name is legacy, but the
        # parameter now represents maximum thermal output per timestep.
        # Enforce both Q_HP[t] <= Q_HP,max and the equivalent electric bound
        # E_HP[t] <= Q_HP,max / COP[m(t)].
        model.addConstr(
            heatpump_heat[t] <= hp_heat_max,
            name=f"heatpump_qhp_max[{t}]",
        )

        # Equivalent electric input bound derived from the thermal cap.
        model.addConstr(
            heatpump_elec[t] <= hp_heat_max / cop_t,
            name=f"heatpump_pel_max[{t}]",
        )
        
        # Inter-temporal ramping on the electrical input.
        if t > 0:
            model.addConstr(
                heatpump_elec[t] - heatpump_elec[t - 1] <= ramp_limit_kwh_per_timestep,
                name=f"heatpump_ramp_up[{t}]",
            )
            model.addConstr(
                heatpump_elec[t - 1] - heatpump_elec[t] <= ramp_limit_kwh_per_timestep,
                name=f"heatpump_ramp_down[{t}]",
            )
        
        # Optional binary modulation enforcement.
        # When enabled, the unit is either off or operating above a minimum
        # turndown level. When disabled, the model is continuously modulating.
        if enforce_modulation_binary and heatpump_on is not None:
            model.addConstr(
                heatpump_elec[t] <= (hp_heat_max / cop_t) * heatpump_on[t],
                name=f"heatpump_pel_max_on[{t}]",
            )
            model.addConstr(
                heatpump_elec[t] >= modulation_min_frac * (hp_heat_max / cop_t) * heatpump_on[t],
                name=f"heatpump_modulation_min[{t}]",
            )
        
        # Nominal capacity cap: the optimized size still limits the heat output.
        model.addConstr(
            heatpump_heat[t] <= heatpump_nominal,
            name=f"heatpump_nominal_limit[{t}]",
        )

        # ===== PTES STATE OF CHARGE DYNAMICS =====
        if t == 0:
            # Initial state: assume starting with 50% charge
            model.addConstr(
                ptes_soc[t] == 0.5 * ptes_volume * kwhth_per_m3 + ptes_charge[t] * ptes_efficiency - ptes_discharge[t],
                name=f"ptes_soc_initial[{t}]",
            )
        else:
            # Recursive state update: SoC[t] = SoC[t-1] + charge*eff - discharge
            model.addConstr(
                ptes_soc[t] == ptes_soc[t - 1] + ptes_charge[t] * ptes_efficiency - ptes_discharge[t],
                name=f"ptes_soc_dynamics[{t}]",
            )

        # ===== PTES CAPACITY CONSTRAINTS =====
        # State of charge cannot exceed storage capacity
        model.addConstr(
            ptes_soc[t] <= ptes_volume * kwhth_per_m3,
            name=f"ptes_soc_max[{t}]",
        )
        
        # Non-negativity of SoC enforced implicitly by variable bounds

