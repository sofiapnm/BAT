import pandas as pd
from parameters.heat_pump import HEAT_PUMP_TECHNICAL
from parameters.ptes import PTES_TECHNICAL


def add_heat_balance_constraints(model, vars_dict, heatdemand_kwhth, n, datetime_series=None):
    """
    Thermal energy balance: woodchip boiler, heat pump, and PTES storage jointly meet thermal demand.

    Heat Balance: Q_woodchip + Q_HP + Q_PTES_discharge = Q_demand + Q_PTES_charge

    The heat pump converts electricity to heat with monthly-varying COP.
    PTES provides temporal flexibility with charge/discharge efficiency and capacity limits.
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
        # ===== HEAT BALANCE WITH PTES =====
        # Q_woodchip + Q_HP + Q_PTES_discharge = Q_demand + Q_PTES_charge
        model.addConstr(
            woodchip_heat[t] + heatpump_heat[t] + ptes_discharge[t] 
            == heatdemand_kwhth[t] + ptes_charge[t],
            name=f"heat_balance_with_ptes[{t}]",
        )

        # ===== HEAT PUMP CONSTRAINTS =====
        # Heat pump COP relation
        cop_t = cop_monthly[months[t] - 1]
        model.addConstr(
            heatpump_heat[t] == cop_t * heatpump_elec[t],
            name=f"heatpump_cop[{t}]",
        )
        
        # Heat pump electrical limit
        model.addConstr(
            heatpump_elec[t] <= hp_elec_max,
            name=f"heatpump_pel_max[{t}]",
        )
        
        # Heat pump ramp rate limits
        if t > 0:
            model.addConstr(
                heatpump_elec[t] - heatpump_elec[t - 1] <= ramp_limit_kwh_per_timestep,
                name=f"heatpump_ramp_up[{t}]",
            )
            model.addConstr(
                heatpump_elec[t - 1] - heatpump_elec[t] <= ramp_limit_kwh_per_timestep,
                name=f"heatpump_ramp_down[{t}]",
            )
        
        # Optional binary modulation enforcement
        if enforce_modulation_binary and heatpump_on is not None:
            model.addConstr(
                heatpump_elec[t] <= hp_elec_max * heatpump_on[t],
                name=f"heatpump_pel_max_on[{t}]",
            )
            model.addConstr(
                heatpump_elec[t] >= modulation_min_frac * hp_elec_max * heatpump_on[t],
                name=f"heatpump_modulation_min[{t}]",
            )
        
        # Heat pump thermal capacity limits
        model.addConstr(
            heatpump_heat[t] <= cop_t * hp_elec_max,
            name=f"heatpump_qhp_capacity[{t}]",
        )
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

