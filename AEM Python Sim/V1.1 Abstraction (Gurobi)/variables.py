from gurobipy import GRB

from parameters.battery import BATTERY_TECHNICAL


def add_variables(model, n):
    vars_dict = {}

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
        n, lb=soc_lb, ub=soc_ub, vtype=GRB.CONTINUOUS, name="soc"
    )

    return vars_dict