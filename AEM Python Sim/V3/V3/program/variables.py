from gurobipy import GRB

from parameters.battery import BATTERY_MODE, BATTERY_TECHNICAL


def add_variables(model, n):
    vars_dict = {}

    battery_mode = BATTERY_MODE.lower()
    if battery_mode == "optional":
        vars_dict["battery_installed"] = model.addVar(
            vtype=GRB.BINARY, name="battery_installed"
        )
    elif battery_mode == "always_on":
        vars_dict["battery_installed"] = model.addVar(
            lb=1.0, ub=1.0, vtype=GRB.CONTINUOUS, name="battery_installed"
        )
    elif battery_mode == "always_off":
        vars_dict["battery_installed"] = model.addVar(
            lb=0.0, ub=0.0, vtype=GRB.CONTINUOUS, name="battery_installed"
        )
    else:
        raise ValueError(f"Unknown BATTERY_MODE: {BATTERY_MODE}")

    vars_dict["grid_import"] = model.addVars(
        n, lb=0.0, vtype=GRB.CONTINUOUS, name="grid_import"
    )
    vars_dict["grid_export"] = model.addVars(
        n, lb=0.0, vtype=GRB.CONTINUOUS, name="grid_export"
    )

    vars_dict["batt_charge"] = model.addVars(
        n, lb=0.0, vtype=GRB.CONTINUOUS, name="batt_charge"
    )
    vars_dict["batt_discharge"] = model.addVars(
        n, lb=0.0, vtype=GRB.CONTINUOUS, name="batt_discharge"
    )

    soc_lb = BATTERY_TECHNICAL["soc_min_frac"] * BATTERY_TECHNICAL["capacity_kwh"]
    soc_ub = BATTERY_TECHNICAL["soc_max_frac"] * BATTERY_TECHNICAL["capacity_kwh"]

    vars_dict["soc"] = model.addVars(
        n, lb=0.0, ub=soc_ub, vtype=GRB.CONTINUOUS, name="soc"
    )

    vars_dict["soc_min_kwh"] = soc_lb
    vars_dict["soc_max_kwh"] = soc_ub

    # Production allocated to meet local demand (remainder goes to export/battery)
    vars_dict["prod_for_local_demand"] = model.addVars(
        n, lb=0.0, vtype=GRB.CONTINUOUS, name="prod_for_local_demand"
    )

    # Thermal production from woodchip boiler [kWh_th]
    vars_dict["woodchip_boiler_heat_kWhth"] = model.addVars(
        n, lb=0.0, vtype=GRB.CONTINUOUS, name="woodchip_boiler_heat_kWhth"
    )

    # Heat pump thermal output [kWh_th]
    vars_dict["heatpump_heat_kWhth"] = model.addVars(
        n, lb=0.0, vtype=GRB.CONTINUOUS, name="heatpump_heat_kWhth"
    )

    # Heat pump electrical demand [kWh_el]
    vars_dict["heatpump_elec_kWh"] = model.addVars(
        n, lb=0.0, vtype=GRB.CONTINUOUS, name="heatpump_elec_kWh"
    )

    # Heat pump nominal thermal capacity [kWh_th per timestep]
    vars_dict["heatpump_nominal_kWhth"] = model.addVar(
        lb=0.0, vtype=GRB.CONTINUOUS, name="heatpump_nominal_kWhth"
    )

    return vars_dict