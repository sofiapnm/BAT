from dataclasses import dataclass


@dataclass(frozen=True)
class BatteryConfig:
    # 15-minute intervals
    delta_t_h: float = 0.25

    # Battery technical limits
    capacity_kwh: float = 4000.0
    soc_min_frac: float = 0.05
    soc_max_frac: float = 0.95
    soc_init_frac: float = 0.50
    soc_end_frac: float = 0.50
    charge_power_max_kw: float = 2000.0
    discharge_power_max_kw: float = 2000.0
    charge_eff: float = 0.95
    discharge_eff: float = 0.95
    throughput_cost_rp_per_kwh: float = 0.02

    #Battery physical constraints
    @property
    def soc_min_kwh(self) -> float:
        return self.soc_min_frac * self.capacity_kwh

    @property
    def soc_max_kwh(self) -> float:
        return self.soc_max_frac * self.capacity_kwh

    @property
    def soc_init_kwh(self) -> float:
        return self.soc_init_frac * self.capacity_kwh

    @property
    def soc_end_kwh(self) -> float:
        return self.soc_end_frac * self.capacity_kwh

    @property
    def max_charge_kwh_per_step(self) -> float:
        return self.charge_power_max_kw * self.delta_t_h

    @property
    def max_discharge_kwh_per_step(self) -> float:
        return self.discharge_power_max_kw * self.delta_t_h
