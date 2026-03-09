from pyomo.environ import NonNegativeReals, Param, RangeSet, Reals, Var


class VariableBlock:
    def __init__(self, battery_cfg):
        self.battery_cfg = battery_cfg

    def attach(self, model, production_kwh, demand_kwh, spot_price_rp_per_kwh):
        n = len(demand_kwh)
        model.T = RangeSet(0, n - 1)

        model.production = Param(model.T, initialize={t: float(production_kwh[t]) for t in range(n)}, within=Reals)
        model.demand = Param(model.T, initialize={t: float(demand_kwh[t]) for t in range(n)}, within=Reals)
        model.spot = Param(model.T, initialize={t: float(spot_price_rp_per_kwh[t]) for t in range(n)}, within=Reals)

        model.grid_import = Var(model.T, within=NonNegativeReals)
        model.grid_export = Var(model.T, within=NonNegativeReals)
        model.batt_charge = Var(model.T, within=NonNegativeReals)
        model.batt_discharge = Var(model.T, within=NonNegativeReals)
        model.soc = Var(
            model.T,
            bounds=(self.battery_cfg.soc_min_kwh, self.battery_cfg.soc_max_kwh),
            within=NonNegativeReals,
        )
