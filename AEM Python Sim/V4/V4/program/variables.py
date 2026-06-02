from gurobipy import GRB

from parameters.battery import BATTERY_MODE, BATTERY_TECHNICAL
from parameters.general import GENERAL
from parameters.heat_pump import HEAT_PUMP_TECHNICAL
from parameters.ptes import PTES_MODE, PTES_TECHNICAL


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

    # Battery capacity sizing variable [kWh]
    cap_min = BATTERY_TECHNICAL.get("capacity_kwh_min", BATTERY_TECHNICAL["capacity_kwh"])
    cap_max = BATTERY_TECHNICAL.get("capacity_kwh_max", BATTERY_TECHNICAL["capacity_kwh"])
    vars_dict["battery_capacity_kwh"] = model.addVar(
        lb=0.0, ub=cap_max, vtype=GRB.CONTINUOUS, name="battery_capacity_kwh"
    )

    # Link capacity to install decision: if not installed capacity == 0,
    # if installed enforce min capacity and allow up to max.
    model.addConstr(
        vars_dict["battery_capacity_kwh"] <= vars_dict["battery_installed"] * cap_max,
        name="battery_capacity_upper_if_installed",
    )
    model.addConstr(
        vars_dict["battery_capacity_kwh"] >= vars_dict["battery_installed"] * cap_min,
        name="battery_capacity_lower_if_installed",
    )

    vars_dict["grid_import"] = model.addVars(
        n, lb=0.0, vtype=GRB.CONTINUOUS, name="grid_import"
    )
    vars_dict["grid_export"] = model.addVars(
        n, lb=0.0, vtype=GRB.CONTINUOUS, name="grid_export"
    )
    if GENERAL.get("use_grid_exclusivity", False):
        vars_dict["grid_mode"] = model.addVars(
            n, vtype=GRB.BINARY, name="grid_mode"
        )

    vars_dict["batt_charge"] = model.addVars(
        n, lb=0.0, vtype=GRB.CONTINUOUS, name="batt_charge"
    )
    vars_dict["batt_discharge"] = model.addVars(
        n, lb=0.0, vtype=GRB.CONTINUOUS, name="batt_discharge"
    )
    if GENERAL.get("use_battery_exclusivity", False):
        vars_dict["batt_charge_mode"] = model.addVars(
            n, vtype=GRB.BINARY, name="batt_charge_mode"
        )

    # SOC variables: allow up to the maximum possible capacity
    cap_max = BATTERY_TECHNICAL.get("capacity_kwh_max", BATTERY_TECHNICAL["capacity_kwh"])
    vars_dict["soc"] = model.addVars(
        n, lb=0.0, ub=cap_max, vtype=GRB.CONTINUOUS, name="soc"
    )

    # Production allocated to meet local demand (remainder goes to export/battery)
    # `prod_for_local_demand` removed — production is fixed and reported via input series

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

    if HEAT_PUMP_TECHNICAL.get("enforce_modulation_binary", False):
        # Heat pump on/off state (used to enforce exact modulation limits)
        vars_dict["heatpump_on"] = model.addVars(
            n, vtype=GRB.BINARY, name="heatpump_on"
        )

    # Heat pump nominal thermal power [kW_th]
    vars_dict["heatpump_nominal_kwth"] = model.addVar(
        lb=0.0, vtype=GRB.CONTINUOUS, name="heatpump_nominal_kwth"
    )

    # Woodchip boiler nominal thermal power [kW_th]
    vars_dict["woodchip_nominal_kwth"] = model.addVar(
        lb=0.0, ub=5200.0, vtype=GRB.CONTINUOUS, name="woodchip_nominal_kwth"
    )

    ptes_mode = PTES_MODE.lower()
    if ptes_mode == "optional":
        vars_dict["ptes_installed"] = model.addVar(
            vtype=GRB.BINARY, name="ptes_installed"
        )
    elif ptes_mode == "always_on":
        vars_dict["ptes_installed"] = model.addVar(
            lb=1.0, ub=1.0, vtype=GRB.CONTINUOUS, name="ptes_installed"
        )
    elif ptes_mode == "always_off":
        vars_dict["ptes_installed"] = model.addVar(
            lb=0.0, ub=0.0, vtype=GRB.CONTINUOUS, name="ptes_installed"
        )
    else:
        raise ValueError(f"Unknown PTES_MODE: {PTES_MODE}")

    # PTES (Pit Thermal Energy Storage) variables [kWh_th]
    vars_dict["ptes_charge_kWhth"] = model.addVars(
        n, lb=0.0, vtype=GRB.CONTINUOUS, name="ptes_charge_kWhth"
    )

    vars_dict["ptes_discharge_kWhth"] = model.addVars(
        n, lb=0.0, vtype=GRB.CONTINUOUS, name="ptes_discharge_kWhth"
    )

    # Optional PTES charge/discharge exclusivity binary.
    if GENERAL.get("use_ptes_exclusivity", False):
        vars_dict["ptes_charge_mode"] = model.addVars(
            n, vtype=GRB.BINARY, name="ptes_charge_mode"
        )

    # PTES state of charge [kWh_th]
    vars_dict["ptes_soc_kWhth"] = model.addVars(
        n, lb=0.0, vtype=GRB.CONTINUOUS, name="ptes_soc_kWhth"
    )

    # PTES storage volume sizing variable [m³]
    ptes_volume_max = PTES_TECHNICAL["volume_m3_max"]
    vars_dict["ptes_volume_m3"] = model.addVar(
        lb=0.0, ub=ptes_volume_max, vtype=GRB.CONTINUOUS, name="ptes_volume_m3"
    )

    model.addConstr(
        vars_dict["ptes_volume_m3"] <= vars_dict["ptes_installed"] * ptes_volume_max,
        name="ptes_volume_upper_if_installed",
    )
    model.addConstr(
        vars_dict["ptes_volume_m3"]
        >= vars_dict["ptes_installed"] * PTES_TECHNICAL["volume_m3_min"],
        name="ptes_volume_lower_if_installed",
    )

    return vars_dict
