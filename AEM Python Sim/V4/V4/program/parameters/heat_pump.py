"""
Heat pump technical, economic, and emissions assumptions.

The optimization model uses a linear heat-pump representation:

    Q_HP[t] = COP[m(t)] · E_HP[t]

where:
    - Q_HP[t] is useful heat output [kWh_th per timestep]
    - E_HP[t] is electricity use [kWh_el per timestep]
    - COP[m(t)] is the month-dependent coefficient of performance

The device is also constrained by a maximum thermal output cap, an optional
minimum modulation level, and an inter-temporal ramp limit.
"""

HEAT_PUMP_TECHNICAL = {
    # Monthly COP profile (Jan-Dec), used as COP[m(t)] in the operating equations.
    "cop_monthly": [2.95, 2.9, 3.05, 3.2, 3.35, 3.55, 3.85, 3.85, 3.7, 3.55, 3.35, 3.1],
    
    # If True, enforce inter-temporal ramping on the electrical input.
    # Relaxing this can improve solver speed for large problems.
    "enforce_hp_ramping": False,
    # Maximum change in electric input per timestep [kWh_el per timestep].
    # This creates a continuous ramping limit between adjacent timesteps.
    # Only active when enforce_hp_ramping=True.
    "ramp_limit_kwh_per_timestep": 0.15,
    
    # If True, enforce exact on/off modulation with a binary variable.
    # Kept False by default so full-year solves remain tractable.
    "enforce_modulation_binary": True,
    # Minimum stable electric input fraction while running [0..1].
    # Only active when enforce_modulation_binary=True.
    "modulation_min_frac": 0.2,
}

HEAT_PUMP_ECONOMIC = {
    # NOTE: All CAPEX (variable and fixed) is now calculated from the nonlinear 
    # power-law function in HEAT_PUMP_NONLINEAR (see below).
    # Assumed technical/economic lifetime for amortization [years].
    "heatpump_lifetime_years": 30,  # 20-25
    # Annual O&M cost as a percentage of variable CAPEX (applied in objective function)
    "annual_opex_percentage_of_capex": 0.01,
}

HEAT_PUMP_EMISSIONS = {
    # Direct operational emissions factor on useful heat output.
    "emissions_kgco2eq_per_kwhth": 0.148,
}


# =============================================================================
# NONLINEAR COST FUNCTION FOR VARIABLE CAPACITY HEAT PUMP
# =============================================================================
# Power-law function for nominal thermal power sizing: CAPEX [CHF] = 1100 * (Q_nominal / 100)^(-0.46)
# This represents economies of scale in heat pump installation costs.
# Output: specific cost in CHF/kW, multiply by nominal thermal power Q_nominal [kW_th] for total CAPEX.

HEAT_PUMP_NONLINEAR = {
    # Power-law coefficients (Q in kWth, cost in CHF)
    "capex_coefficient_chf": 1100.0,
    "capacity_scaling_divisor": 100.0,
    "exponent": -0.46,
    # Optimization range (kWth)
    "q_nominal_min_kwth": 100.0,
    "q_nominal_max_kwth": 40000.0,
    # Number of piecewise linear segments
    "num_breakpoints": 10,
}


def heatpump_specific_cost_chf_per_kwth(q_nominal_kwth):
    """
    Compute specific cost (CHF/kW) at a given capacity using the power-law function.
    
    Args:
        q_nominal_kwth (float): Nominal thermal capacity in kWth
    
    Returns:
        float: Specific cost in CHF/kW
    """
    if q_nominal_kwth <= 0:
        return float('inf')
    coeff = HEAT_PUMP_NONLINEAR["capex_coefficient_chf"]
    divisor = HEAT_PUMP_NONLINEAR["capacity_scaling_divisor"]
    exponent = HEAT_PUMP_NONLINEAR["exponent"]
    return coeff * ((q_nominal_kwth / divisor) ** exponent)


def heatpump_total_cost_rp(q_nominal_kwth):
    """
    Compute total CAPEX (rappen) for a given capacity.
    Formula: [1100 * (Q/100)^(-0.46)] * 100 [CHF->Rp] * Q [specific -> total]
    
    Args:
        q_nominal_kwth (float): Nominal thermal capacity in kWth
    
    Returns:
        float: Total CAPEX in rappen
    """
    if q_nominal_kwth <= 0:
        return 0.0
    specific_cost_chf = heatpump_specific_cost_chf_per_kwth(q_nominal_kwth)
    return specific_cost_chf * 100.0 * q_nominal_kwth  # Convert CHF->Rp and multiply by capacity


def generate_heatpump_cost_breakpoints():
    """
    Generate piecewise linear breakpoints for the heat pump cost function.
    Returns arrays of Q values and corresponding costs for SOS2 interpolation.
    
    Returns:
        tuple: (q_breakpoints, cost_breakpoints) both as lists
    """
    try:
        import numpy as np
        q_min = HEAT_PUMP_NONLINEAR["q_nominal_min_kwth"]
        q_max = HEAT_PUMP_NONLINEAR["q_nominal_max_kwth"]
        n_breaks = HEAT_PUMP_NONLINEAR["num_breakpoints"]
        
        # Logarithmic spacing for better fit on power-law curve
        q_breakpoints = np.logspace(
            np.log10(q_min), np.log10(q_max), n_breaks
        ).tolist()
    except ImportError:
        # Fallback without numpy (linear spacing)
        q_min = HEAT_PUMP_NONLINEAR["q_nominal_min_kwth"]
        q_max = HEAT_PUMP_NONLINEAR["q_nominal_max_kwth"]
        n_breaks = HEAT_PUMP_NONLINEAR["num_breakpoints"]
        q_breakpoints = [
            q_min + (q_max - q_min) * i / (n_breaks - 1)
            for i in range(n_breaks)
        ]
    
    cost_breakpoints = [heatpump_total_cost_rp(q) for q in q_breakpoints]
    return q_breakpoints, cost_breakpoints