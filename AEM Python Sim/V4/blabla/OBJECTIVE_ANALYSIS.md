# Complete Objective Function Analysis: Cost Minimization vs Profit Maximization

## Executive Summary

The current model uses **cost minimization** in `objective.py`. The objective expression is structured as:
```
MINIMIZE: Cost_expr
```

To switch to **profit maximization**, you simply negate the cost expression in the `setObjective()` call, and maximize instead of minimize. However, there are **sign conventions** embedded in how costs and revenues are combined that need explanation.

---

## Part 1: Current Cost Objective Structure

### The Cost Minimization Formula (from objective.py, lines 145-196)

```python
expr = gp.quicksum(
    grid_import[t] * (spot_price_rp_per_kwh[t] + import_high_use_tariff)
    - grid_export[t] * (spot_price_rp_per_kwh[t] - export_high_use_tariff)
    + battery_degradation_cost * (batt_charge[t] + batt_discharge[t])
    for t in range(n)
) + (tariff adjustment terms) + (power tariff terms) 
  + battery_installed * (battery_capex + battery_annual_opex)     # Fixed costs
  + heatpump_fixed_cost_rp                                         # Fixed costs
  + ptes_cost_var                                                  # Fixed costs
  - production_revenue                                             # SUBTRACTED (revenue)
  + woodchip_net_cost                                              # Added (cost)
  - thermal_revenue                                                # SUBTRACTED (revenue)

model.setObjective(expr, GRB.MINIMIZE)
```

### What This Means

- **Positive coefficients** → costs (added to minimize)
- **Negative coefficients** → revenues (subtracted to minimize, making profit larger)
- **GRB.MINIMIZE** → makes the objective as small as possible = minimizes net cost = maximizes net profit

This is a **confusing and indirect way** to represent profit. The optimization engine is actually minimizing cost (which gives profit), but the semantics are inverted.

---

## Part 2: Component Breakdown - Every Variable and Parameter

### TIMESTEP-DEPENDENT COSTS (summed over n timesteps)

#### 1. **GRID IMPORT COST**
| Component | Formula | Sign | Units | Value Location |
|-----------|---------|------|-------|-----------------|
| Grid import at high-use tariff | `grid_import[t] × (spot_price[t] + import_high_use_tariff)` | **+** (cost) | Rp | grid_import.py |
| Grid import cost parameter | `import_high_use_tariff` | - | Rp/kWh | **1.08 Rp/kWh** |
| Grid import cost parameter (low) | `import_low_use_tariff` | - | Rp/kWh | **3.28 Rp/kWh** |

**Why two tariffs?** Depends on annual grid usage hours. If > 3500h → high tariff. If ≤ 3500h → low tariff.

#### 2. **GRID EXPORT REVENUE** (subtracted, so it reduces cost)
| Component | Formula | Sign | Units | Value |
|-----------|---------|------|-------|-------|
| Grid export revenue (high tariff) | `grid_export[t] × (spot_price[t] - export_high_use_tariff)` | **−** (revenue) | Rp | grid_export.py |
| Export high-use tariff | `export_high_use_tariff` | - | Rp/kWh | **1.08 Rp/kWh** |
| Export low-use tariff | `export_low_use_tariff` | - | Rp/kWh | **3.28 Rp/kWh** |

**Note:** The sign in the objective is already negative (`- grid_export[t] * ...`), so export reduces the total cost.

#### 3. **BATTERY DEGRADATION COST**
| Component | Formula | Sign | Units | Value |
|-----------|---------|------|-------|-------|
| Battery throughput degradation | `battery_degradation_cost × (batt_charge[t] + batt_discharge[t])` | **+** (cost) | Rp | battery.py |
| Degradation cost per kWh throughput | `degradation_cost_rp_per_kwh_throughput` | - | Rp/kWh | **0.0 Rp/kWh** (disabled) |

#### 4. **RUN-OF-RIVER GENERATION REVENUE** (subtracted, so it reduces cost)
| Component | Formula | Sign | Units | Value |
|-----------|---------|------|-------|-------|
| Production for local demand revenue | `prod_for_local[t] × runofriver_profit_per_kwh` | **−** (revenue) | Rp | runofriver.py |
| Run-of-river profit per kWh local use | `runofriver_profit_per_kwh` | - | Rp/kWh | **6.50 Rp/kWh** |
| Export revenue of excess production | `(production[t] - prod_for_local[t]) × (spot_price[t] - export_high_use_tariff)` | **−** (revenue) | Rp | grid_export + runofriver |

#### 5. **WOODCHIP BOILER FUEL COST**
| Component | Formula | Sign | Units | Value |
|-----------|---------|------|-------|-------|
| Woodchip fuel cost | `woodchip_heat[t] × woodchip_cost_per_kwhth` | **+** (cost) | Rp | woodchip_boiler.py |
| Woodchip cost per kWh_th useful | `woodchip_cost_per_kwhth` | - | Rp/kWh_th | **5.539 Rp/kWh_th** |

#### 6. **THERMAL REVENUE** (subtracted, so it reduces cost)
| Component | Formula | Sign | Units | Value |
|-----------|---------|------|-------|-------|
| Thermal output revenue | `heatdemand[t] × thermal_revenue_per_kwhth` | **−** (revenue) | Rp | woodchip_boiler.py |
| Thermal revenue per kWh_th sold | `thermal_revenue_per_kwhth` | - | Rp/kWh_th | **9.917 Rp/kWh_th** |

---

### ANNUAL FIXED COSTS (added once per year, in the model = once per optimization)

#### 7. **BATTERY FIXED COSTS**
| Component | Formula | Sign | Units | Value |
|-----------|---------|------|-------|-------|
| Annual CAPEX (amortized) | `battery_capacity_kwh × annual_capex_rp_per_kwh_amortized` | - | Rp | battery.py |
| Annual OPEX | `battery_capacity_kwh × annual_opex_rp_per_kwh_year` | - | Rp | battery.py |
| Combined annual cost | `battery_installed × (battery_capex + battery_annual_opex)` | **+** (fixed cost) | Rp | - |
| Battery capacity | `capacity_kwh` | - | kWh | **10,000 kWh** |
| CAPEX per kWh | `capex_rp_kwh` | - | Rp/kWh | **60,000 Rp/kWh** |
| Lifetime for amortization | `battery_lifetime_years` | - | years | **10 years** |
| Annual amortized CAPEX | `60,000 / 10 = 6,000 Rp/kWh/yr` | - | Rp/kWh/yr | **6,000** |
| Annual OPEX % of CAPEX | `0.01 × (cost_rp_kwh)` | - | % | **1% = 600 Rp/kWh/yr** |
| **Total annual battery cost** | `(6000 + 600) × 10000 × battery_installed` | - | Rp | **66,000,000 Rp** (if installed) |

#### 8. **HEAT PUMP FIXED COSTS**
| Component | Formula | Sign | Units | Value |
|-----------|---------|------|-------|-------|
| CAPEX per kW_th nominal (variable) | `cost_rp_per_kwth_nominal × heatpump_nominal / lifetime_years` | - | Rp | heat_pump.py |
| OPEX per kW_th nominal per year | `annual_opex_rp_per_kwth_year × heatpump_nominal` | - | Rp | heat_pump.py |
| Combined variable cost | `(cost_rp_per_kwth_nominal / 30 + annual_opex_rp_per_kwth_year) × heatpump_nominal` | **+** (fixed cost) | Rp | - |
| Fixed CAPEX (one-time, amortized) | `cost_rp_fixed / 30` | - | Rp | heat_pump.py |
| **Total annual heat pump cost** | `heatpump_fixed_cost_rp` | **+** (fixed cost) | Rp | - |
| CAPEX per kWh_th nominal | `cost_rp_per_kwth_nominal` | - | Rp/kWh_th | **56,759,718 Rp/kWh_th** ⚠️ |
| Fixed CAPEX | `cost_rp_fixed` | - | Rp | **17,233,943 Rp** |
| Lifetime | `heatpump_lifetime_years` | - | years | **30 years** |
| Annual OPEX % of per-unit CAPEX | `0.01 × cost_rp_per_kwth_nominal` | - | % | **1% = 567,597 Rp/kWh_th/yr** ⚠️ |

#### 9. **PTES FIXED COSTS**
| Component | Formula | Sign | Units | Value |
|-----------|---------|------|-------|-------|
| PTES annualized cost function | `cost_rp_per_year_factor × (ptes_volume_m3 ^ cost_exp)` | **+** (fixed cost) | Rp | ptes.py |
| Cost coefficient (annualized) | `cost_rp_per_year_factor = 838668.4 / 30` | - | Rp/m³^exp | **27,955.61** |
| Cost exponent | `cost_chf_exp` | - | dimensionless | **−0.424** (decreasing marginal cost) |
| **Total PTES cost** | `ptes_cost_var = 27955.61 × (volume_m3 ^ -0.424)` | **+** (fixed cost) | Rp | - |

#### 10. **GRID POWER TARIFF (MONTHLY)**
| Component | Formula | Sign | Units | Value |
|-----------|---------|------|-------|-------|
| Annual power tariff | `power_tariff_rp_per_kw_per_month × sum(monthly_peak_kw)` | **+** (cost) | Rp | import.py |
| Power tariff (high grid use) | `power_tariff_high_grid_use_rp_per_kw_per_month` | - | Rp/kW/month | **1143 Rp/kW/month** |
| Power tariff (low grid use) | `power_tariff_low_grid_use_rp_per_kw_per_month` | - | Rp/kW/month | **502 Rp/kW/month** |

---

## Part 3: Aggregated Annual Cost Structure

The `summarize_solution()` function in [results.py](results.py#L380) consolidates all costs:

```python
annual_cost_burden_rp = (
    annual_import_cost_rp              # Cost of electricity imported
    - annual_export_revenue_rp         # Revenue from electricity exported (subtracted = profit)
    + annual_battery_degradation_rp    # Cost of battery wear
    - annual_runofriver_profit_rp      # Profit from local production (subtracted = profit)
    + annual_woodchip_cost_rp          # Cost of woodchip fuel
    - annual_thermal_revenue_rp        # Revenue from thermal sales (subtracted = profit)
    + annual_power_cost_rp             # Monthly power tariff
    + annual_battery_fixed_cost_rp     # Battery CAPEX + OPEX
    + annual_heatpump_fixed_cost_rp    # Heat pump CAPEX + OPEX
    + annual_ptes_fixed_cost_rp        # PTES CAPEX (annualized)
)

net_annual_profit_chf = -annual_cost_burden_rp / 100.0  # Negate cost to get profit (and convert Rp to CHF)
```

### Sign Convention in `summarize_solution()`:
- **Costs are ADDED** to `annual_cost_burden_rp` (positive)
- **Revenues are SUBTRACTED** (negative signs) to reduce the cost burden
- **Final conversion:** `profit = -cost_burden / 100` (negate and convert units)

---

## Part 4: Exact Cost/Revenue Components Table

| # | Component | Variable(s) Used | Formula | Sign in Cost Obj | Annual Aggregation (summarize_solution) |
|---|-----------|-----------------|---------|------------------|----------------------------------------|
| **1** | Grid import cost (timestep) | `grid_import[t]`, `spot_price[t]` | `sum(grid_import[t] × (spot + tariff_import))` | **+** | `annual_import_cost_rp = sum(grid_import × price_with_tariff)` |
| **2** | Grid export revenue (timestep) | `grid_export[t]`, `spot_price[t]` | `sum(grid_export[t] × (spot - tariff_export))` | **−** | `annual_export_revenue_rp = sum(grid_export × price_minus_tariff)` |
| **3** | Run-of-river local use profit | `prod_for_local_demand[t]` | `sum(prod_local[t] × 6.5)` | **−** | `annual_runofriver_profit_rp = sum(prod_local × 6.5)` |
| **4** | Export excess production | Implicit in grid export | `sum((production[t] - prod_local[t]) × (spot - export_tariff))` | **−** (included in #2) | Included in `annual_export_revenue_rp` |
| **5** | Woodchip fuel cost | `woodchip_heat[t]` | `sum(woodchip[t] × 5.539)` | **+** | `annual_woodchip_cost_rp = sum(woodchip × cost_per_unit)` |
| **6** | Thermal revenue | `heatdemand[t]` | `sum(heatdemand[t] × 9.917)` | **−** | `annual_thermal_revenue_rp = sum(heatdemand × revenue_per_unit)` |
| **7** | Battery degradation | `batt_charge[t]`, `batt_discharge[t]` | `sum((charge+discharge)[t] × 0.0)` | **+** | `annual_battery_degradation_rp = sum(throughput × 0.0)` ⚠️ **DISABLED** |
| **8** | Battery fixed (CAPEX+OPEX) | `battery_installed`, `battery_capacity_kwh` | `battery_installed × 66M` (if always_on) | **+** | `annual_battery_fixed_cost_rp = 66,000,000 × battery_installed` |
| **9** | Power tariff (monthly) | `monthly_peak_kw[month]` | `sum(monthly_peak × power_tariff_monthly)` | **+** | `annual_power_cost_rp = sum(monthly_peaks × tariff)` |
| **10** | Heat pump fixed (CAPEX+OPEX) | `heatpump_nominal_kWhth` | `(HP_capex_per_kwth/30 + HP_opex) × nominal + HP_fixed_capex/30` | **+** | `annual_heatpump_fixed_cost_rp = (...) × heatpump_nominal + fixed_amortized` |
| **11** | PTES fixed cost (annualized) | `ptes_volume_m3` | `27955.61 × (volume ^ -0.424)` | **+** | `annual_ptes_fixed_cost_rp = cost_func(ptes_volume)` |

---

## Part 5: Conversion from Cost Minimization to Profit Maximization

### Current Implementation (Cost Minimization)

```python
# In objective.py, add_objective() function
expr = gp.quicksum(...)  # All terms as above
model.setObjective(expr, GRB.MINIMIZE)  # ← Minimize cost
```

### To Switch to Profit Maximization

**Option 1: Direct Negation (No Code Change)**
```python
expr = gp.quicksum(...)  # Same formula
model.setObjective(expr, GRB.MAXIMIZE)  # ← Change MINIMIZE to MAXIMIZE
```
This works because **the same objective expression represents profit** when maximized (due to negative signs on revenues).

**Option 2: Explicit Profit Formula (Clearer Semantics)**
```python
# Define profit = revenue - cost
profit_expr = (
    # REVENUES (positive)
    + annual_production_revenue          # Run-of-river + export
    + annual_thermal_revenue
    + annual_export_revenue
    
    # COSTS (negative)
    - annual_import_cost
    - annual_battery_degradation
    - annual_woodchip_cost
    - annual_battery_fixed_cost
    - annual_heatpump_fixed_cost
    - annual_ptes_fixed_cost
    - annual_power_cost
)

model.setObjective(profit_expr, GRB.MAXIMIZE)
```

### Why Both Approaches Give The Same Answer

The current cost objective is cleverly constructed:
```
cost_expr = costs(+) - revenues(-)
          = (import + battery + woodchip + fixed) - (export + production + thermal)
          
When MINIMIZED, this is equivalent to:
maximize(revenue - cost) = maximize(profit)
```

Because:
```
minimize(cost_expr) ↔ minimize(costs - revenues) ↔ maximize(revenues - costs) = maximize(profit)
```

---

## Part 6: Sign Issues in Current Model

### Potential Problems with Current Sign Convention

The current approach is **semantically backwards** which can lead to confusion:

1. **Negative revenues look like costs in the code** (they have `-` signs), which is counter-intuitive
2. **When adding new components, developers might forget the negative sign** for revenues, accidentally adding a cost instead of a revenue
3. **The `summarize_solution()` function needs to negate the annual cost burden** to get profit, which is another inversion

### Example of a Missing Sign Bug

In the current code:
```python
- grid_export[t] * (spot_price_rp_per_kwh[t] - export_high_use_tariff)
```
If a developer mistakenly removed the leading `-` sign, grid export would become a **cost** instead of a **revenue**, and the optimizer would **minimize exports** instead of **maximize them**.

This is exactly what happened in the conversation history when PTES costs were missing from the summary—the objective was correct but the summary function was missing the accounting.

---

## Part 7: Complete Sign Audit

| Component | In Objective.py | In summarize_solution() | Correct? |
|-----------|-----------------|------------------------|----------|
| Grid import cost | `+` | `annual_import_cost_rp` (added) | ✅ |
| Grid export revenue | `−` | `− annual_export_revenue_rp` | ✅ |
| Run-of-river profit | `−` | `− annual_runofriver_profit_rp` | ✅ |
| Woodchip cost | `+` | `+ annual_woodchip_cost_rp` | ✅ |
| Thermal revenue | `−` | `− annual_thermal_revenue_rp` | ✅ |
| Battery degradation | `+` | `+ annual_battery_degradation_rp` | ✅ |
| Battery fixed | `+` | `+ annual_battery_fixed_cost_rp` | ✅ |
| Power tariff | `+` | `+ annual_power_cost_rp` | ✅ |
| Heat pump fixed | `+` | `+ annual_heatpump_fixed_cost_rp` | ✅ |
| PTES fixed | `+` | `+ annual_ptes_fixed_cost_rp` | ✅ |

---

## Part 8: Step-by-Step Conversion Guide

### To Switch from Cost Minimization → Profit Maximization

**Step 1:** In [objective.py](objective.py#L145-L196), change line 196 from:
```python
model.setObjective(expr, GRB.MINIMIZE)
```
to:
```python
model.setObjective(expr, GRB.MAXIMIZE)
```

**Step 2 (Optional, for Clarity):** Rewrite the entire objective expression with explicit profit semantics:
```python
# Instead of cost = costs - revenues,
# Make it explicit: profit = revenue - costs

profit_expr = (
    # Annual revenues
    gp.quicksum(
        prod_for_local[t] * runofriver_profit_per_kwh
        + (production_kwh[t] - prod_for_local[t]) * (spot_price_rp_per_kwh[t] - export_high_use_tariff)
        + heatdemand_kwhth[t] * thermal_revenue_per_kwhth
        for t in range(n)
    )
    # Annual costs (subtracted)
    - gp.quicksum(
        grid_import[t] * (spot_price_rp_per_kwh[t] + import_high_use_tariff)
        + battery_degradation_cost * (batt_charge[t] + batt_discharge[t])
        + woodchip_heat[t] * woodchip_cost_per_kwhth
        for t in range(n)
    )
    # Fixed costs (subtracted)
    - (battery_installed * (battery_capex + battery_annual_opex))
    - heatpump_fixed_cost_rp
    - ptes_cost_var
    - (power_tariff + ... adjustments)
)

model.setObjective(profit_expr, GRB.MAXIMIZE)
```

**Step 3:** In [results.py](results.py#L455), change the final profit calculation from:
```python
net_annual_profit_chf = -annual_cost_burden_rp / 100.0
```
to simply:
```python
net_annual_profit_chf = annual_cost_burden_rp / 100.0  # Remove the negation
```

---

## Part 9: Examples of Cost/Revenue Components

### EXAMPLE 1: Grid Import (Cost)
```
If grid_import[t] = 100 kWh at t=3
If spot_price[t] = 20 Rp/kWh
If import_tariff = 1.08 Rp/kWh

Cost contribution at t=3:
= 100 × (20 + 1.08)
= 100 × 21.08
= 2,108 Rp added to cost expression

When minimizing: optimizer discourages high import
When maximizing: optimizer still discourages import (it's reversed in sign = negative profit)
```

### EXAMPLE 2: Grid Export (Revenue)
```
If grid_export[t] = 50 kWh at t=3
If spot_price[t] = 20 Rp/kWh
If export_tariff = 1.08 Rp/kWh

Revenue contribution at t=3:
= - 50 × (20 - 1.08)
= - 50 × 18.92
= -946 Rp subtracted from cost expression
  (same as +946 Rp added as profit)

When minimizing cost: optimizer encourages export (lowers total cost)
When maximizing profit: optimizer still encourages export (directly increases profit)
```

### EXAMPLE 3: Battery Fixed Cost (Annual)
```
Battery capacity = 10,000 kWh
Amortized CAPEX/year = 60,000 Rp/kWh/yr
Annual OPEX = 600 Rp/kWh/yr
Battery installed = 1 (binary, yes/no)

Fixed cost contribution:
= 1 × (60,000 + 600) × 10,000
= 606,000,000 Rp added to cost expression

When minimizing: optimizer evaluates whether battery benefits outweigh €6.06M/yr cost
When maximizing: optimizer evaluates net benefit after subtracting this cost
```

### EXAMPLE 4: Heat Pump (Mixed Fixed + Variable)
```
Nominal capacity (decision variable): 100 kWh_th

Per-unit costs:
- CAPEX amortized = 56,759,718 Rp/kWh_th / 30 = 1,891,990 Rp/kWh_th/yr
- OPEX = 1% × 56,759,718 = 567,597 Rp/kWh_th/yr
- Combined = 2,459,588 Rp/kWh_th/yr

Fixed costs:
- Fixed CAPEX amortized = 17,233,943 / 30 = 574,465 Rp/yr

Total annual heat pump cost if nominal=100:
= (2,459,588 × 100) + 574,465
= 246,533,265 Rp/yr

⚠️ These parameters are VERY LARGE. The heat pump dominates the cost!
```

---

## Part 10: Recommended Changes for Clarity

### Current Status: Confusing Sign Convention
**Pros:**
- Minimization naturally handles profit maximization
- No code change needed to switch paradigms

**Cons:**
- Counter-intuitive (negative signs for revenues)
- Difficult to verify correctness
- Error-prone for new components

### Recommended: Explicit Profit Objective
**Changes needed:**
1. **Rewrite objective expression** to be `profit = revenue - cost` (no negative signs needed)
2. **Use GRB.MAXIMIZE** instead of GRB.MINIMIZE
3. **Update results.py** to not negate the profit
4. **Add comments** explaining which terms are revenues and which are costs

**Benefits:**
- Semantically correct (maximize profit = good)
- Easier to audit (all revenues positive, all costs negative)
- Lower risk of sign errors in future modifications
- Easier for others to understand the code

---

## Summary Table: All Components at a Glance

| Category | Component | Objective Contribution | Annual Cost (summarize_solution) | Time-Varying? | Value |
|----------|-----------|------------------------|----------------------------------|---------------|-------|
| **ELECTRICITY** | Grid import | `+ spot + 1.08 Rp/kWh` | sum(import × price) | Yes (spot varies) | 20-30 Rp/kWh typical |
| | Grid export | `- (spot - 1.08 Rp/kWh)` | sum(export × price) | Yes (spot varies) | 15-25 Rp/kWh typical |
| | Run-of-river local use | `- 6.5 Rp/kWh` | sum(prod_local × 6.5) | No (fixed) | 6.5 Rp/kWh |
| | Export excess production | `- (spot - export_tariff)` | Included in grid export | Yes (spot varies) | Variable |
| **HEAT** | Woodchip fuel | `+ 5.539 Rp/kWh_th` | sum(woodchip × 5.539) | No (fixed) | 5.539 Rp/kWh_th |
| | Thermal revenue | `- 9.917 Rp/kWh_th` | sum(demand × 9.917) | No (fixed) | 9.917 Rp/kWh_th profit |
| **STORAGE** | Battery degradation | `+ 0.0 Rp/kWh throughput` | sum(charged + discharged) × 0 | No (disabled) | 0 Rp |
| | Battery fixed annual | `+ 66M Rp if installed` | battery_installed × 66M | No (fixed) | 66,000,000 Rp/yr |
| | Power tariff | `+ 502-1143 Rp/kW/month` | sum(monthly_peaks × tariff) | No (fixed tier) | 6,024-13,716 Rp/yr per kW |
| **DEVICES** | Heat pump fixed | `+ (variable with capacity)` | hp_nominal_dependent | No (fixed) | Huge (~246M Rp/100 kW_th) |
| | PTES fixed | `+ 27955.61 × (V ^ -0.424)` | depends on volume chosen | No (fixed) | Decreasing with scale |

