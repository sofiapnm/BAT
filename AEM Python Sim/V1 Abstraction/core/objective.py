from pyomo.environ import Objective, minimize


class ObjectiveBlock:
    def __init__(self, objective_mode, battery_cfg, grid_cfg):
        self.objective_mode = objective_mode
        self.battery_cfg = battery_cfg
        self.grid_cfg = grid_cfg

    def attach(self, model):
        if self.objective_mode == "cost":
            model.objective = Objective(
                expr=sum(
                    model.grid_import[t] * model.spot[t]
                    - model.grid_export[t] * model.spot[t]
                    + self.battery_cfg.throughput_cost_rp_per_kwh
                    * (model.batt_charge[t] + model.batt_discharge[t])
                    for t in model.T
                ),
                sense=minimize,
            )
            return

        if self.objective_mode == "emissions":
            model.objective = Objective(
                expr=sum(
                    model.grid_import[t] * self.grid_cfg.emissions_kgco2_per_kwh
                    - model.grid_export[t] * self.grid_cfg.export_emissions_credit_kgco2_per_kwh
                    for t in model.T
                ),
                sense=minimize,
            )
            return

        raise ValueError(f"Unknown objective_mode: {self.objective_mode}")
