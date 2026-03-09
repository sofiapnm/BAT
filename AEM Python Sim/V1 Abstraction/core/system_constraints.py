from pyomo.environ import Constraint


def add_energy_balance_constraint(model, battery_cfg):
    def energy_balance_rule(m, t):
        return (
            m.production[t]
            + m.grid_import[t]
            + m.batt_discharge[t] * battery_cfg.discharge_eff
            == m.demand[t] + m.grid_export[t] + m.batt_charge[t]
        )

    model.energy_balance = Constraint(model.T, rule=energy_balance_rule)


def add_soc_constraints(model, battery_cfg, init_soc_kwh, final_soc_kwh):
    def soc_transition_rule(m, t):
        if t == 0:
            return m.soc[t] == (
                init_soc_kwh + battery_cfg.charge_eff * m.batt_charge[t] - m.batt_discharge[t]
            )
        return m.soc[t] == (
            m.soc[t - 1] + battery_cfg.charge_eff * m.batt_charge[t] - m.batt_discharge[t]
        )

    model.soc_transition = Constraint(model.T, rule=soc_transition_rule)
    model.charge_rate_limit = Constraint(
        model.T,
        rule=lambda m, t: m.batt_charge[t] <= battery_cfg.max_charge_kwh_per_step,
    )
    model.discharge_rate_limit = Constraint(
        model.T,
        rule=lambda m, t: m.batt_discharge[t] <= battery_cfg.max_discharge_kwh_per_step,
    )

    if final_soc_kwh is not None:
        n = len(model.T)
        model.final_soc = Constraint(expr=model.soc[n - 1] == final_soc_kwh)
