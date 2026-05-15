import pandas as pd
from parameters.general import GENERAL
from parameters.heat_pump import HEAT_PUMP_TECHNICAL
from parameters.ptes import PTES_TECHNICAL


def add_heat_balance_constraints(model, vars_dict, heatdemand_kwhth, n, datetime_series=None):
    """
    Add thermal balance and heat-pump operating constraints.

    Heat balance:

        Q_woodchip[t] + Q_HP[t] + Q_PTES_dis[t] = Q_demand[t] + Q_PTES_ch[t]

    Heat-pump conversion:

        Q_HP[t] = COP[m(t)] · E_HP[t]

    Thermal power cap:

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
    heatpump_nominal_kwth = vars_dict["heatpump_nominal_kwth"]
    woodchip_nominal_kwth = vars_dict.get("woodchip_nominal_kwth")
    
    # PTES variables
    ptes_charge = vars_dict["ptes_charge_kWhth"]
    ptes_discharge = vars_dict["ptes_discharge_kWhth"]
    ptes_soc = vars_dict["ptes_soc_kWhth"]
    ptes_volume = vars_dict["ptes_volume_m3"]
    # PTES charge/discharge mode binary removed; simultaneous charge/discharge allowed
    
    # PTES technical parameters
    ptes_efficiency = PTES_TECHNICAL["efficiency"]
    ptes_discharge_power_kwth = PTES_TECHNICAL.get("discharge_power_kwth", 0.0)
    kwhth_per_m3 = PTES_TECHNICAL["kwhth_per_m3"]
    delta_t_h = GENERAL["delta_t_h"]
    
    # Heat pump parameters
    cop_monthly = HEAT_PUMP_TECHNICAL["cop_monthly"]
    enforce_hp_ramping = HEAT_PUMP_TECHNICAL.get("enforce_hp_ramping", False)
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
        # Note: ptes_charge[t] is the thermal energy actually stored AFTER efficiency losses.
        # The heat input required must be: ptes_charge[t] / ptes_efficiency
        # So the total supply must equal demand plus the heat input needed for charging.
        model.addConstr(
            woodchip_heat[t] + heatpump_heat[t] + ptes_discharge[t] 
            == heatdemand_kwhth[t] + ptes_charge[t] / ptes_efficiency
        )

        # ===== HEAT PUMP CONSTRAINTS =====
        # Q_HP[t] = COP[m(t)] * E_HP[t]
        cop_t = cop_monthly[months[t] - 1]
        model.addConstr(
            heatpump_heat[t] == cop_t * heatpump_elec[t]
        )
        
        # Electric input bound derived from nominal thermal power and COP.
        model.addConstr(
            heatpump_elec[t] <= (heatpump_nominal_kwth / cop_t) * delta_t_h
        )

        # Woodchip boiler thermal output cannot exceed its nominal thermal power (if defined)
        if woodchip_nominal_kwth is not None:
            model.addConstr(
                woodchip_heat[t] <= woodchip_nominal_kwth * delta_t_h
            )
        
        # Inter-temporal ramping on the electrical input (optional).
        if enforce_hp_ramping and t > 0:
            model.addConstr(
                heatpump_elec[t] - heatpump_elec[t - 1] <= ramp_limit_kwh_per_timestep
            )
            model.addConstr(
                heatpump_elec[t - 1] - heatpump_elec[t] <= ramp_limit_kwh_per_timestep
            )
        
        # Optional binary modulation enforcement.
        # When enabled, the unit is either off or operating above a minimum
        # turndown level. When disabled, the model is continuously modulating.
        if enforce_modulation_binary and heatpump_on is not None:
            model.addConstr(
                heatpump_elec[t] <= (heatpump_nominal_kwth / cop_t) * heatpump_on[t]
            )
            model.addConstr(
                heatpump_elec[t] >= modulation_min_frac * (heatpump_nominal_kwth / cop_t) * heatpump_on[t]
            )

        # ===== PTES STATE OF CHARGE DYNAMICS =====
        if t == 0:
            # Initial state: assume starting with 70% charge
            model.addConstr(
                ptes_soc[t] == 0.7 * ptes_volume * kwhth_per_m3 + ptes_charge[t] - ptes_discharge[t]
            )
        else:
            # Recursive state update: SoC[t] = SoC[t-1] + charge - discharge
            model.addConstr(
                ptes_soc[t] == ptes_soc[t - 1] + ptes_charge[t] - ptes_discharge[t]
            )

        # Enforce end-of-horizon state-of-charge requirement: 70% of storage volume
        if t == n - 1:
            model.addConstr(
                ptes_soc[t] == 0.7 * ptes_volume * kwhth_per_m3
            )

        # ===== PTES CAPACITY CONSTRAINTS =====
        # State of charge cannot exceed storage capacity
        model.addConstr(
            ptes_soc[t] <= ptes_volume * kwhth_per_m3
        )

        # PTES discharge power cap per timestep (optional)
        if ptes_discharge_power_kwth > 0:
            model.addConstr(
                ptes_discharge[t] <= ptes_discharge_power_kwth * delta_t_h
            )
        
        # Non-negativity of SoC enforced implicitly by variable bounds
        # ===== PTES CHARGE/DISCHARGE EXCLUSIVITY =====
        # Use indicator constraints to prevent simultaneous charging and discharging
        # No binary exclusivity enforced for PTES (indicators removed)

    # No explicit PTES exclusivity constraints here (handled elsewhere if needed)
