# Variable Usage Mapping: Complete Trace

## Overview
This document shows EXACTLY where each variable appears in the optimization and how it flows through the code.

---

## Decision Variables (Created in variables.py)

### Grid-Related Variables

#### `grid_import[t]` for t=0..n-1
**Location Created:** [variables.py:30-32](variables.py#L30-L32)
```python
vars_dict["grid_import"] = model.addVars(
    n, lb=0.0, vtype=GRB.CONTINUOUS, name="grid_import"
)
```

**Used In:**
| File | Function | Line | Purpose | Formula |
|------|----------|------|---------|---------|
| objective.py | add_objective() | 152 | Grid import cost (hourly) | `grid_import[t] × (spot_price + tariff)` |
| objective.py | add_objective() | 162a | Annual grid use calc | `sum(grid_import[t])` |
| constraints/energy_balance.py | add_energy_balance_constraint() | ? | Electricity balance | `production + import ≥ demand + battery_charge + hp_elec` |
| results.py | extract_solution() | 35 | Solution table | Extract all `grid_import[t].X` values |
| results.py | summarize_solution() | 440 | Annual total | `sum(grid_import)` for tariff tier decision |
| results.py | build_results_table() | ~240 | Hourly results | Grid import kWh column |

**Constraints Applied To:**
- Non-negativity: `lb=0.0` (can't import negative power)
- Indicator constraint: If `grid_mode[t]=1` (import mode), then `grid_export[t]=0` [constraints/energy_balance.py]

---

#### `grid_export[t]` for t=0..n-1
**Location Created:** [variables.py:33-35](variables.py#L33-L35)
```python
vars_dict["grid_export"] = model.addVars(
    n, lb=0.0, vtype=GRB.CONTINUOUS, name="grid_export"
)
```

**Used In:**
| File | Function | Line | Purpose | Formula |
|------|----------|------|---------|---------|
| objective.py | add_objective() | 153 | Grid export revenue (hourly) | `-grid_export[t] × (spot_price - tariff)` |
| objective.py | add_objective() | 162b | Annual grid use calc | `sum(grid_export[t])` |
| constraints/energy_balance.py | add_energy_balance_constraint() | ? | Electricity balance | `production - export ≥ demand + battery_charge + hp_elec` |
| results.py | extract_solution() | 36 | Solution table | Extract all `grid_export[t].X` values |
| results.py | summarize_solution() | 441 | Annual total | `sum(grid_export)` for tariff tier decision |
| results.py | build_results_table() | ~240 | Hourly results | Grid export kWh column |

**Constraints Applied To:**
- Non-negativity: `lb=0.0` (can't export negative power)
- Indicator constraint: If `grid_mode[t]=0` (export mode), then `grid_import[t]=0` [constraints/energy_balance.py]

---

#### `grid_mode[t]` for t=0..n-1
**Location Created:** [variables.py:36-38](variables.py#L36-L38)
```python
vars_dict["grid_mode"] = model.addVars(
    n, vtype=GRB.BINARY, name="grid_mode"
)
```

**Used In:**
| File | Function | Line | Purpose | Formula |
|------|----------|------|---------|---------|
| constraints/energy_balance.py | add_energy_balance_constraint() | ? | Enforce mutual exclusivity | `grid_mode[t]=1 → grid_export[t]=0` |
| constraints/energy_balance.py | add_energy_balance_constraint() | ? | Enforce mutual exclusivity | `grid_mode[t]=0 → grid_import[t]=0` |

**Purpose:** Binary indicator for which of {import, export} is active. Enables the indicator constraints that prevent simultaneous import/export.

---

### Battery Variables

#### `batt_charge[t]` for t=0..n-1
**Location Created:** [variables.py:42-44](variables.py#L42-L44)
```python
vars_dict["batt_charge"] = model.addVars(
    n, lb=0.0, vtype=GRB.CONTINUOUS, name="batt_charge"
)
```

**Used In:**
| File | Function | Line | Purpose | Formula |
|------|----------|------|---------|---------|
| objective.py | add_objective() | 154 | Battery degradation cost (hourly) | `battery_degradation_cost × batt_charge[t]` |
| constraints/battery.py | add_battery_constraint() | ? | State of charge dynamics | `soc[t] = soc[t-1] + charge×eff - discharge` |
| constraints/battery.py | add_battery_constraint() | ? | Charge power limit | `batt_charge[t] ≤ 25 kW` |
| constraints/battery.py | add_battery_constraint() | ? | Charge/discharge exclusivity | `batt_charge_mode[t]=1 → batt_discharge[t]=0` |
| results.py | extract_solution() | 37 | Solution table | Extract all `batt_charge[t].X` values |
| results.py | summarize_solution() | 445 | Annual total | `sum(batt_charge)` for degradation calculation |
| results.py | build_results_table() | ~240 | Hourly results | Battery charge kWh column |

**Constraints Applied To:**
- Non-negativity: `lb=0.0` (can't charge backward)
- Power limit: `batt_charge[t] ≤ 25 kW` [constraints/battery.py]
- Charge efficiency: Energy stored = `charge[t] × 0.95` [constraints/battery.py]

---

#### `batt_discharge[t]` for t=0..n-1
**Location Created:** [variables.py:45-47](variables.py#L45-L47)
```python
vars_dict["batt_discharge"] = model.addVars(
    n, lb=0.0, vtype=GRB.CONTINUOUS, name="batt_discharge"
)
```

**Used In:**
| File | Function | Line | Purpose | Formula |
|------|----------|------|---------|---------|
| objective.py | add_objective() | 154 | Battery degradation cost (hourly) | `battery_degradation_cost × batt_discharge[t]` |
| constraints/battery.py | add_battery_constraint() | ? | State of charge dynamics | `soc[t] = soc[t-1] + charge×0.95 - discharge` |
| constraints/battery.py | add_battery_constraint() | ? | Discharge power limit | `batt_discharge[t] ≤ 25 kW` |
| constraints/battery.py | add_battery_constraint() | ? | Charge/discharge exclusivity | `batt_charge_mode[t]=0 → batt_discharge[t]=0` |
| results.py | extract_solution() | 38 | Solution table | Extract all `batt_discharge[t].X` values |
| results.py | summarize_solution() | 445 | Annual total | `sum(batt_discharge)` for degradation calculation |
| results.py | build_results_table() | ~240 | Hourly results | Battery discharge kWh column |

**Constraints Applied To:**
- Non-negativity: `lb=0.0` (can't discharge backward)
- Power limit: `batt_discharge[t] ≤ 25 kW` [constraints/battery.py]
- Discharge efficiency: Energy released = `discharge[t]` (with SoC loss of 5%) [constraints/battery.py]

---

#### `batt_charge_mode[t]` for t=0..n-1
**Location Created:** [variables.py:48-50](variables.py#L48-L50)
```python
vars_dict["batt_charge_mode"] = model.addVars(
    n, vtype=GRB.BINARY, name="batt_charge_mode"
)
```

**Used In:**
| File | Function | Line | Purpose | Formula |
|------|----------|------|---------|---------|
| constraints/battery.py | add_battery_constraint() | ? | Enforce mutual exclusivity | `batt_charge_mode[t]=1 → batt_discharge[t]=0` |
| constraints/battery.py | add_battery_constraint() | ? | Enforce mutual exclusivity | `batt_charge_mode[t]=0 → batt_charge[t]=0` |

**Purpose:** Binary indicator for charge mode. When=1, battery charges (discharge must be 0). When=0, battery discharges (charge must be 0).

---

#### `soc[t]` for t=0..n-1 (State of Charge)
**Location Created:** [variables.py:53-56](variables.py#L53-L56)
```python
vars_dict["soc"] = model.addVars(
    n, lb=0.0, ub=soc_ub, vtype=GRB.CONTINUOUS, name="soc"
)
```

**Used In:**
| File | Function | Line | Purpose | Formula |
|------|----------|------|---------|---------|
| constraints/battery.py | add_battery_constraint() | ? | State equation (t>0) | `soc[t] = soc[t-1] + charge×0.95 - discharge` |
| constraints/battery.py | add_battery_constraint() | ? | Min/max bounds | `soc_min ≤ soc[t] ≤ soc_max` |
| constraints/battery.py | add_battery_constraint() | ? | Initial condition | `soc[0] = initial_soc` |
| constraints/battery.py | add_battery_constraint() | ? | Final condition (optional) | `soc[n-1] = final_soc` |
| results.py | extract_solution() | 39 | Solution table | Extract all `soc[t].X` values |
| results.py | build_results_table() | ~240 | Hourly results | Battery SoC kWh column |

**Bounds Applied:**
- Lower bound: `lb=0.0` (can't go negative)
- Upper bound: `ub = 0.95 × 10000 = 9500 kWh` (95% of 10 MWh capacity)
- Min operating level: `soc[t] ≥ 0.05 × 10000 = 500 kWh` (via constraint)

---

#### `battery_installed` (Single BINARY variable)
**Location Created:** [variables.py:10-22](variables.py#L10-L22)
```python
# Either:
vars_dict["battery_installed"] = model.addVar(vtype=GRB.BINARY)
# Or forced to 1.0 if mode="always_on"
```

**Used In:**
| File | Function | Line | Purpose | Formula |
|------|----------|------|---------|---------|
| objective.py | add_objective() | 185 | Battery fixed cost | `battery_installed × (capex + opex)` |
| constraints/battery.py | add_battery_constraint() | ? | Activate/deactivate battery | `battery_installed=0 → batt_charge[t]=0 etc` |
| results.py | extract_solution() | 26 | Solution table | Extract `battery_installed.X` |
| results.py | summarize_solution() | 439 | Annual total | Use for cost calculation |

**Purpose:** Whether to physically install a battery system. If=0, all battery flows must be zero. If=1, battery is available.

---

### Heat Pump Variables

#### `heatpump_heat_kWhth[t]` for t=0..n-1
**Location Created:** [variables.py:70-72](variables.py#L70-L72)
```python
vars_dict["heatpump_heat_kWhth"] = model.addVars(
    n, lb=0.0, vtype=GRB.CONTINUOUS, name="heatpump_heat_kWhth"
)
```

**Used In:**
| File | Function | Line | Purpose | Formula |
|------|----------|------|---------|---------|
| constraints/heat_balance.py | add_heat_balance_constraint() | ? | Heat balance (hourly) | `heatpump_heat + woodchip_heat + ptes_discharge ≥ heatdemand` |
| constraints/heat_pump.py | add_heatpump_constraint() | ? | Ramp limit | `|heatpump_heat[t] - heatpump_heat[t-1]| ≤ ramp_limit` |
| constraints/heat_pump.py | add_heatpump_constraint() | ? | Power limit | `heatpump_heat[t] ≤ hp_heat_max = 1750 kWh_th` |
| objective.py | add_objective() | (in emissions mode) | Emissions from heat generation | `heatpump_heat[t] × emissions_per_kwhth` |
| results.py | extract_solution() | 45-46 | Solution table | Extract all `heatpump_heat_kWhth[t].X` values |
| results.py | summarize_solution() | 448 | Annual total | `sum(heatpump_heat)` for cost calculation |
| results.py | build_results_table() | ~270 | Hourly results | Heat pump heat output column |

**Constraints Applied To:**
- Non-negativity: `lb=0.0`
- Power capacity: `heatpump_heat[t] ≤ 1750 kWh_th per timestep` (= 7000 kW_th)
- Ramp constraint: `|heatpump_heat[t] - heatpump_heat[t-1]| ≤ 0.125 kWh_th` (gentle ramp)

---

#### `heatpump_elec_kWh[t]` for t=0..n-1
**Location Created:** [variables.py:73-75](variables.py#L73-L75)
```python
vars_dict["heatpump_elec_kWh"] = model.addVars(
    n, lb=0.0, vtype=GRB.CONTINUOUS, name="heatpump_elec_kWh"
)
```

**Used In:**
| File | Function | Line | Purpose | Formula |
|------|----------|------|---------|---------|
| constraints/heat_pump.py | add_heatpump_constraint() | ? | COP relationship (hourly) | `heatpump_heat[t] = COP[month(t)] × heatpump_elec[t]` |
| constraints/energy_balance.py | add_energy_balance_constraint() | ? | Electricity balance | `production + import ≥ demand + battery_charge + heatpump_elec` |
| results.py | extract_solution() | 48 | Solution table | Extract all `heatpump_elec_kWh[t].X` values |
| results.py | build_results_table() | ~275 | Hourly results | Heat pump electric input column |

**Constraints Applied To:**
- Non-negativity: `lb=0.0`
- Linked to thermal output via: `heatpump_heat[t] = COP[month] × heatpump_elec[t]`
- COP varies monthly: [2.95, 2.9, 3.05, ..., 3.1] from heat_pump.py

---

#### `heatpump_nominal_kWhth` (Single CONTINUOUS variable)
**Location Created:** [variables.py:81-83](variables.py#L81-L83)
```python
vars_dict["heatpump_nominal_kWhth"] = model.addVar(
    lb=0.0, vtype=GRB.CONTINUOUS, name="heatpump_nominal_kWhth"
)
```

**Used In:**
| File | Function | Line | Purpose | Formula |
|------|----------|------|---------|---------|
| constraints/heat_pump.py | add_heatpump_constraint() | ? | Sizing constraint | `heatpump_heat[t] ≤ heatpump_nominal (upper bound per timestep)` |
| objective.py | add_objective() | 180-182 | Heat pump fixed cost | `heatpump_fixed_cost = (capex_per_kwth / 30 + opex) × nominal + fixed_capex/30` |
| results.py | extract_solution() | 50 | Solution table | Extract `heatpump_nominal_kWhth.X` |
| results.py | summarize_solution() | 448 | Annual summary | Use for annual cost calculation |
| results.py | build_results_table() | ~280 | Hourly results | Nominal capacity (same for all timesteps) |

**Purpose:** Sizing decision. The device capacity is chosen by the optimizer, then each hour's operation must be ≤ nominal.

---

#### `heatpump_on[t]` for t=0..n-1 (OPTIONAL)
**Location Created:** [variables.py:77-79](variables.py#L77-L79) (only if `enforce_modulation_binary=True`)
```python
if HEAT_PUMP_TECHNICAL.get("enforce_modulation_binary", False):
    vars_dict["heatpump_on"] = model.addVars(
        n, vtype=GRB.BINARY, name="heatpump_on"
    )
```

**Used In:**
| File | Function | Line | Purpose | Formula |
|------|----------|------|---------|---------|
| constraints/heat_pump.py | add_heatpump_constraint() | ? | Modulation logic | `heatpump_on[t]=1 → heatpump_elec[t] ≥ 0.2×nominal` |
| constraints/heat_pump.py | add_heatpump_constraint() | ? | Modulation logic | `heatpump_on[t]=0 → heatpump_elec[t]=0` |

**Note:** Currently disabled (enforce_modulation_binary=False), so this variable is not created.

---

### PTES Variables

#### `ptes_charge_kWhth[t]` for t=0..n-1
**Location Created:** [variables.py:88-90](variables.py#L88-L90)
```python
vars_dict["ptes_charge_kWhth"] = model.addVars(
    n, lb=0.0, vtype=GRB.CONTINUOUS, name="ptes_charge_kWhth"
)
```

**Used In:**
| File | Function | Line | Purpose | Formula |
|------|----------|------|---------|---------|
| constraints/ptes.py | add_ptes_constraint() | ? | State equation | `ptes_soc[t] = ptes_soc[t-1] + charge×eff - discharge` |
| constraints/ptes.py | add_ptes_constraint() | ? | Charge limit | `ptes_charge[t] ≤ ptes_charge_max` |
| constraints/heat_balance.py | add_heat_balance_constraint() | ? | Heat balance | `heatpump_heat + woodchip_heat + ptes_discharge ≥ heatdemand + ptes_charge` |
| results.py | extract_solution() | 56 | Solution table | Extract all `ptes_charge_kWhth[t].X` values |
| results.py | build_results_table() | ~290 | Hourly results | PTES charge column |

---

#### `ptes_discharge_kWhth[t]` for t=0..n-1
**Location Created:** [variables.py:92-94](variables.py#L92-L94)
```python
vars_dict["ptes_discharge_kWhth"] = model.addVars(
    n, lb=0.0, vtype=GRB.CONTINUOUS, name="ptes_discharge_kWhth"
)
```

**Used In:**
| File | Function | Line | Purpose | Formula |
|------|----------|------|---------|---------|
| constraints/ptes.py | add_ptes_constraint() | ? | State equation | `ptes_soc[t] = ptes_soc[t-1] + charge×0.80 - discharge` |
| constraints/ptes.py | add_ptes_constraint() | ? | Discharge limit | `ptes_discharge[t] ≤ ptes_discharge_max` |
| constraints/heat_balance.py | add_heat_balance_constraint() | ? | Heat balance | `heatpump_heat + woodchip_heat + ptes_discharge ≥ heatdemand` |
| results.py | extract_solution() | 57 | Solution table | Extract all `ptes_discharge_kWhth[t].X` values |
| results.py | build_results_table() | ~291 | Hourly results | PTES discharge column |

---

#### `ptes_soc_kWhth[t]` for t=0..n-1
**Location Created:** [variables.py:97-99](variables.py#L97-L99)
```python
vars_dict["ptes_soc_kWhth"] = model.addVars(
    n, lb=0.0, vtype=GRB.CONTINUOUS, name="ptes_soc_kWhth"
)
```

**Used In:**
| File | Function | Line | Purpose | Formula |
|------|----------|------|---------|---------|
| constraints/ptes.py | add_ptes_constraint() | ? | State equation | `ptes_soc[t] = ptes_soc[t-1] + charge×0.80 - discharge` |
| constraints/ptes.py | add_ptes_constraint() | ? | Volume constraint | `ptes_soc[t] ≤ ptes_volume × energy_density (605 kWh_th/m³)` |
| results.py | extract_solution() | 58 | Solution table | Extract all `ptes_soc_kWhth[t].X` values |
| results.py | build_results_table() | ~292 | Hourly results | PTES state of charge column |

---

#### `ptes_volume_m3` (Single CONTINUOUS variable)
**Location Created:** [variables.py:101-103](variables.py#L101-L103)
```python
vars_dict["ptes_volume_m3"] = model.addVar(
    lb=0.0, vtype=GRB.CONTINUOUS, name="ptes_volume_m3"
)
```

**Used In:**
| File | Function | Line | Purpose | Formula |
|------|----------|------|---------|---------|
| objective.py | add_ptes_cost_constraint() | 22-49 | PTES cost function (piecewise linear) | `ptes_cost_var = cost_rp_per_year_factor × (volume ^ -0.424)` |
| objective.py | add_objective() | 187 | Annual PTES fixed cost | `ptes_cost_var` (computed via SOS2 interpolation) |
| constraints/ptes.py | add_ptes_constraint() | ? | Max state constraint | `ptes_soc[t] ≤ ptes_volume × 605` |
| objective.py | build_annual_emissions_expr() | 73 | PTES embodied emissions | `ptes_volume × ptes_emissions_per_m3` |
| results.py | extract_solution() | 20 | Solution table | Extract `ptes_volume_m3.X` |
| results.py | summarize_solution() | 450 | Annual summary | Use for annual cost & emissions |
| results.py | build_results_table() | ~293 | Hourly results | Storage volume (same for all timesteps) |

---

### Production And Load Allocation Variables

#### `prod_for_local_demand[t]` for t=0..n-1
**Location Created:** [variables.py:62-64](variables.py#L62-L64)
```python
vars_dict["prod_for_local_demand"] = model.addVars(
    n, lb=0.0, vtype=GRB.CONTINUOUS, name="prod_for_local_demand"
)
```

**Used In:**
| File | Function | Line | Purpose | Formula |
|------|----------|------|---------|---------|
| objective.py | add_objective() | 169-173 | Production revenue split | `production_revenue = sum(prod_for_local × 6.5) + sum((production - prod_for_local) × (spot - tariff))` |
| constraints/energy_balance.py | add_energy_balance_constraint() | ? | Allocation constraint | `prod_for_local[t] ≤ production[t]` |
| results.py | extract_solution() | 40 | Solution table | Extract all `prod_for_local_demand[t].X` values |
| results.py | summarize_solution() | 443 | Annual total | `sum(prod_for_local)` for profit calculation |
| results.py | build_results_table() | ~245 | Hourly results | Production for local demand column |

**Purpose:** Split hourly production between local use (6.5 Rp/kWh) and export (spot price - tariff). The difference goes to export.

---

### Thermal Production Variables

#### `woodchip_boiler_heat_kWhth[t]` for t=0..n-1
**Location Created:** [variables.py:66-68](variables.py#L66-L68)
```python
vars_dict["woodchip_boiler_heat_kWhth"] = model.addVars(
    n, lb=0.0, vtype=GRB.CONTINUOUS, name="woodchip_boiler_heat_kWhth"
)
```

**Used In:**
| File | Function | Line | Purpose | Formula |
|------|----------|------|---------|---------|
| objective.py | add_objective() | 175 | Woodchip fuel cost (hourly) | `sum(woodchip_heat × 5.539)` |
| constraints/heat_balance.py | add_heat_balance_constraint() | ? | Heat balance | `woodchip_heat + heatpump_heat + ptes_discharge ≥ heatdemand + ptes_charge` |
| objective.py | build_annual_emissions_expr() | 68 | Woodchip emissions | `sum(woodchip_heat × 0.3272)` |
| results.py | extract_solution() | 41 | Solution table | Extract all `woodchip_boiler_heat_kWhth[t].X` values |
| results.py | summarize_solution() | 446 | Annual total | `sum(woodchip_heat)` for cost calculation |
| results.py | build_results_table() | ~250 | Hourly results | Woodchip heat output column |

**Constraints Applied To:**
- Non-negativity: `lb=0.0`
- No explicit power limit (unlimited thermal production from woodchip)

---

## Derived/Auxiliary Variables

### Grid Mode Variable (Binary)

#### `export_low_grid_use` (Single BINARY variable)
**Location Created:** [objective.py:163-167](objective.py#L163-L167)
```python
export_low_grid_use = model.addVar(
    vtype=GRB.BINARY, name="export_low_grid_use_tariff_active"
)
```

**Used In:**
| File | Function | Line | Purpose | Formula |
|------|----------|------|---------|---------|
| objective.py | add_objective() | 168-174 | Tariff adjustment | If grid use ≤ 3500h: import/export tariff changes from 1.08 to 3.28 Rp/kWh |

**Purpose:** Determines which tariff tier is active based on annual grid usage.

---

### PTES Cost Piecewise Linear Variable

#### `ptes_annual_cost_rp` (Single CONTINUOUS variable)
**Location Created:** [objective.py:155](objective.py#L155)
```python
ptes_cost_var = model.addVar(lb=0.0, vtype=GRB.CONTINUOUS, name="ptes_annual_cost_rp")
```

**Used In:**
| File | Function | Line | Purpose |
|------|----------|------|---------|
| objective.py | add_ptes_cost_constraint() | 36 | Define via SOS2 interpolation |
| objective.py | add_objective() | 187 | Add to total annual cost |

**Computation Method:** SOS2 (Special Ordered Set type 2) with 9 breakpoints

---

## Monthly Peak Variables

#### `monthly_peak_kw[month_label]` for each month
**Location Created:** In [model_builder.py](model_builder.py) or [constraints/](constraints/) (not shown in variables.py)

**Used In:**
| File | Function | Purpose | Formula |
|------|----------|---------|---------|
| objective.py | add_objective() | Power tariff cost | `sum(monthly_peak × power_tariff)` |
| results.py | summarize_solution() | Annual power cost | Sum of monthly peaks × tariff rate |

---

## Input Data (NOT Decision Variables)

These are parameters passed into the optimization, not variables modified by Gurobi:

| Variable Name | Type | Created From | Used In |
|---------------|------|--------------|---------|
| `production_kwh[t]` | Array[n] | CSV data (run-of-river generation) | Energy balance, revenue calculations |
| `heatdemand_kwhth[t]` | Array[n] | CSV data | Heat balance, revenue calculations |
| `spot_price_rp_per_kwh[t]` | Array[n] | CSV data | Grid import/export cost |
| `datetime_series` | Series | CSV dates | Results timestamping |

---

## Summary Table: All Decision Variables

| Variable | Type | Count | Created Line | Objective? | Constraints? | Time-Varying? |
|----------|------|-------|--------------|-----------|--------------|---------------|
| `grid_import[t]` | Continuous | n | 30-32 | **Yes** | **Yes** | Yes |
| `grid_export[t]` | Continuous | n | 33-35 | **Yes** | **Yes** | Yes |
| `grid_mode[t]` | Binary | n | 36-38 | No | **Yes** (indicator) | Yes |
| `batt_charge[t]` | Continuous | n | 42-44 | **Yes** | **Yes** | Yes |
| `batt_discharge[t]` | Continuous | n | 45-47 | **Yes** | **Yes** | Yes |
| `batt_charge_mode[t]` | Binary | n | 48-50 | No | **Yes** (indicator) | Yes |
| `soc[t]` | Continuous | n | 53-56 | No | **Yes** | Yes |
| `battery_installed` | Binary | 1 | 10-22 | **Yes** | **Yes** | No |
| `heatpump_heat_kWhth[t]` | Continuous | n | 70-72 | **Yes** (emis) | **Yes** | Yes |
| `heatpump_elec_kWh[t]` | Continuous | n | 73-75 | No | **Yes** | Yes |
| `heatpump_nominal_kWhth` | Continuous | 1 | 81-83 | **Yes** | **Yes** | No |
| `heatpump_on[t]` | Binary | n | 77-79 | No | **Yes** | Yes* |
| `ptes_charge_kWhth[t]` | Continuous | n | 88-90 | No | **Yes** | Yes |
| `ptes_discharge_kWhth[t]` | Continuous | n | 92-94 | No | **Yes** | Yes |
| `ptes_soc_kWhth[t]` | Continuous | n | 97-99 | No | **Yes** | Yes |
| `ptes_volume_m3` | Continuous | 1 | 101-103 | **Yes** | **Yes** | No |
| `prod_for_local_demand[t]` | Continuous | n | 62-64 | **Yes** | **Yes** | Yes |
| `woodchip_boiler_heat_kWhth[t]` | Continuous | n | 66-68 | **Yes** | **Yes** | Yes |
| `monthly_peak_kw[month]` | Continuous | 12 | (external) | **Yes** | No | No |
| `export_low_grid_use` | Binary | 1 | 163 | **Yes** | **Yes** | No |
| `ptes_cost_var` | Continuous | 1 | 155 | **Yes** | **Yes** | No |
| `ptes_weights[i]` | Continuous | 9 | 38 (ptes) | No | **Yes** (SOS2) | No |

\* `heatpump_on[t]` only created if `enforce_modulation_binary=True`

---

## Cost Objective: Variable Contributions

Sorted by magnitude of annual impact:

| Rank | Component | Variable(s) | Formula | Typical Annual Value | Impact |
|------|-----------|------------|---------|----------------------|--------|
| **1** | Heat pump fixed | `heatpump_nominal` | `(capex+opex) × nominal + fixed` | ~2.46 M CHF/yr (for 100 kW_th) | **Dominates** |
| **2** | Battery fixed | `battery_installed` | `66 M Rp × installed` | 660,000 CHF/yr | **Major** |
| **3** | Grid import | `grid_import[t]` | `sum(import × spot+tariff)` | 50,000-100,000 CHF/yr | Moderate |
| **4** | Power tariff | `monthly_peak_kw` | `sum(peaks × tariff)` | 60,000-137,000 CHF/yr | Moderate |
| **5** | PTES fixed | `ptes_volume_m3` | `27955.61 × (V^-0.424)` | 100-1,000 CHF/yr | **Negligible** ⚠️ |
| **6** | Woodchip cost | `woodchip_boiler_heat[t]` | `sum(heat × 5.539)` | 10,000-50,000 CHF/yr | Minor |
| **7** | Battery degradation | `batt_charge[t]+batt_discharge[t]` | `sum((ch+dis) × 0.0)` | 0 CHF/yr | **Disabled** |
| **8** | Grid export revenue | `grid_export[t]` | `-sum(export × (spot-tariff))` | −20,000 to −50,000 CHF/yr | Revenue reduction |
| **9** | Run-of-river revenue | `prod_for_local_demand[t]` | `-sum(prod × 6.5)` | −30,000 to −50,000 CHF/yr | Revenue reduction |
| **10** | Thermal revenue | `heatdemand` (input) | `-sum(demand × 9.917)` | −50,000 to −100,000 CHF/yr | Revenue reduction |

**Conclusion:** The optimizer's decisions are dominated by (1) heat pump sizing and (2) battery installation choice. Other variables have much smaller marginal impact.

