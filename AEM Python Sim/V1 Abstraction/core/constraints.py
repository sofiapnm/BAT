from pyomo.environ import Constraint


class ConstraintBlock:
    def __init__(self, battery_cfg, init_soc_kwh, final_soc_kwh):
        self.battery_cfg = battery_cfg
        self.init_soc_kwh = init_soc_kwh
        self.final_soc_kwh = final_soc_kwh

    def attach(self, model):
        def energy_balance_rule(m, t):
            return (
                m.production[t]
                + m.grid_import[t]
                + m.batt_discharge[t] * self.battery_cfg.discharge_eff
                == m.demand[t] + m.grid_export[t] + m.batt_charge[t]
            )

        def soc_transition_rule(m, t):
            if t == 0:
                return m.soc[t] == (
                    self.init_soc_kwh + self.battery_cfg.charge_eff * m.batt_charge[t] - m.batt_discharge[t]
                )
            return m.soc[t] == (
                m.soc[t - 1] + self.battery_cfg.charge_eff * m.batt_charge[t] - m.batt_discharge[t]
            )

        model.energy_balance = Constraint(model.T, rule=energy_balance_rule)
        model.soc_transition = Constraint(model.T, rule=soc_transition_rule)
        model.charge_rate_limit = Constraint(
            model.T,
            rule=lambda m, t: m.batt_charge[t] <= self.battery_cfg.max_charge_kwh_per_step,
        )
        model.discharge_rate_limit = Constraint(
            model.T,
            rule=lambda m, t: m.batt_discharge[t] <= self.battery_cfg.max_discharge_kwh_per_step,
        )

        if self.final_soc_kwh is not None:
            n = len(model.T)
            model.final_soc = Constraint(expr=model.soc[n - 1] == self.final_soc_kwh)
