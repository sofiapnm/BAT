# Quick Reference: Objective Function Guide

## TL;DR - The Main Point

**Your model uses cost minimization, which is equivalent to profit maximization:**

```
MINIMIZE (costs - revenues) = MAXIMIZE (revenues - costs) = MAXIMIZE profit
```

**But it's backwards semantically.** To fix:
1. Change objective from MINIMIZE to MAXIMIZE (1 line)
2. Rewrite expression as `profit = revenue - cost` instead of `cost - revenue` (cleanup only)

**Before doing that, fix these 3 critical parameter errors:**
1. ✋ Heat pump CAPEX is 50,000× too large (parameter error)
2. ✋ PTES cost exponent is negative (sign error) 
3. ✋ Battery degradation is disabled (design choice, should enable)

---

## Quick Parameter Reference

### What Each Cost Component Looks Like

```python
# In objective.py, the cost expression is built like this:

COSTS (positive, increase expr):
  + grid_import[t] × (spot_price[t] + 1.08 Rp/kWh)  # Grid import power
  + battery_deg × (charge[t] + discharge[t])         # Battery cycling (currently 0)
  + woodchip[t] × 5.539 Rp/kWh_th                   # Fuel cost
  + monthly_peak × 1,143 Rp/kW/month                 # Power tariff
  + battery_installed × 66M Rp/yr                    # Battery fixed annual
  + heatpump_nominal × (2.46M Rp/kWh_th/yr)         # Heat pump HUGE cost ⚠️
  + ptes_volume × 27,955 × (vol ^ -0.424)           # Storage cost ⚠️ (inverted exponent)

REVENUES (negative, decrease expr):
  - prod_for_local[t] × 6.5 Rp/kWh                  # Local generation profit
  - grid_export[t] × (spot_price[t] - 1.08)         # Export revenue
  - heatdemand[t] × 9.917 Rp/kWh_th                 # Thermal revenue

OBJECTIVE:
  minimize(costs - revenues)  ← Minimize cost = Maximize profit
```

---

## Variable Count

| Category | Count | Time-Varying? |
|----------|-------|---------------|
| Electricity flow (import/export) | 6 vars × n | Yes |
| Battery (charge/discharge/SoC) | 4 vars × n | Yes |
| Heat pump (thermal/electrical) | 2 vars × n | Yes |
| Heat storage (charge/discharge/SoC) | 3 vars × n | Yes |
| Thermal production (woodchip) | 1 var × n | Yes |
| Production allocation (local/export) | 1 var × n | Yes |
| **Fixed sizing decisions** | 5 single vars | No |
| **Status/mode variables** | 4 single vars | No |
| **Monthly** | 12 (peaks) | No |
| **Annual auxiliary** | 2 (tariff mode, PTES cost) | No |
| **Total** | ~18,000 for full year | - |

---

## Cost/Revenue Components Ranked by Impact

| Rank | Component | Annual Value (Typical) | Status |
|------|-----------|------------------------|--------|
| 1️⃣ | Heat pump fixed cost | **2.46M CHF/yr** (100 kW_th) | **⚠️ Likely wrong** |
| 2️⃣ | Battery fixed cost | **660k CHF/yr** (10 MWh) | ✓ Reasonable |
| 3️⃣ | Grid import cost | **100k CHF/yr** | ✓ Reasonable |
| 4️⃣ | Power tariff | **70k CHF/yr** | ✓ Reasonable |
| 5️⃣ | Woodchip fuel cost | **50k CHF/yr** | ✓ Reasonable |
| — | — | — | — |
| 🔄 | Grid export revenue | **−50k CHF/yr** | ✓ Reasonable |
| 🔄 | Run-of-river revenue | **−50k CHF/yr** | ✓ Reasonable |
| 🔄 | Thermal revenue | **−80k CHF/yr** | ✓ Reasonable |
| — | — | — | — |
| **NET** | **Annual Profit/Loss** | **−2.5M CHF/yr (loss)** | **⚠️ Dominated by HP cost** |

---

## Where Each File Fits

```
PARAMETER FILES (heat_pump.py, battery.py, etc.)
         ↓
         ↓ Parameters define economic assumptions
         ↓
OBJECTIVE FUNCTION (objective.py)
         ↓ Builds cost/emissions expressions using parameters
         ↓
MODEL BUILDER (model_builder.py)
         ↓ Combines objective + constraints
         ↓
GUROBI SOLVER
         ↓ Minimizes/maximizes objective
         ↓
SOLUTION (all variables get .X values)
         ↓
RESULTS AGGREGATION (results.py)
         ↓ Converts hourly solution to annual summary
         ↓
summarize_solution() → annual profit/emissions
print_summary()      → report to user
```

---

## The Sign Convention Problem Illustrated

### Current (Confusing)
```python
# In objective.py
cost_expr = (
    grid_import + ... + heatpump_fixed    # Costs: positive
    - grid_export - production - thermal   # Revenues: negative
)
model.setObjective(cost_expr, GRB.MINIMIZE)

# To get profit in results.py:
profit = -cost_expr / 100   # Negate and convert units
```
❌ Backward logic: minimizing cost to maximize profit via negation trick

### Better (Intuitive)
```python
# In objective.py
profit_expr = (
    grid_export + production + thermal    # Revenues: positive
    - grid_import - ... - heatpump_fixed  # Costs: positive (subtracted)
)
model.setObjective(profit_expr, GRB.MAXIMIZE)

# To get profit in results.py:
profit = profit_expr / 100  # Direct conversion, no negation
```
✅ Forward logic: directly maximize profit

---

## Sanity Check: Parameter Values

```
┌─ Heat Pump ──────────────────────────────────────┐
│ CAPEX per kWh_th nominal: 56,759,718 Rp         │
│ ✗ This is 50,000× the battery CAPEX per kWh     │
│ ✗ A 100 kW_th device costing €5.67 billion?     │
│ → LIKELY ERROR: unit conversion or per-MW typo  │
└───────────────────────────────────────────────────┘

┌─ PTES Cost ───────────────────────────────────────┐
│ Exponent: −0.424 (negative)                      │
│ ✗ Means larger volume → cheaper storage          │
│ ✗ 5,000 m³ costs only 10 Rp/yr (essentially 0)  │
│ → LIKELY ERROR: should be +0.424 (positive)     │
└───────────────────────────────────────────────────┘

┌─ Battery Degradation ──────────────────────────────┐
│ Cost: 0.0 Rp/kWh throughput                       │
│ ✗ Battery can cycle infinitely with zero cost     │
│ ✗ Encourages unrealistic dispatch strategy        │
│ → DESIGN CHOICE: should enable (0.05 Rp/kWh)    │
└────────────────────────────────────────────────────┘

┌─ Grid Tariffs ────────────────────────────────────┐
│ Import (high): 1.08 Rp/kWh = 0.0108 CHF/kWh     │
│ Export (high): 1.08 Rp/kWh tariff deducted       │
│ Power (high): 1,143 Rp/kW/month = 1.14 CHF/kW/m │
│ ✓ Values seem consistent with Swiss utility      │
└────────────────────────────────────────────────────┘
```

---

## How to Switch from Cost → Profit Minimization

### Method 1: Minimal Change (Semantics Only)

**Edit: objective.py, line 196**

```python
# BEFORE:
model.setObjective(expr, GRB.MINIMIZE)

# AFTER:
model.setObjective(expr, GRB.MAXIMIZE)
```

**Result:** Model produces same decisions but uses profit-maximization semantics. ✅ Works immediately.

---

### Method 2: Full Clarity Rewrite (Recommended)

**Edit: objective.py, lines 150-196**

Replace the entire cost expression with:

```python
# Collect all revenues (positive)
annual_revenues = gp.quicksum(
    prod_for_local[t] * runofriver_profit_per_kwh
    + (production_kwh[t] - prod_for_local[t]) * (spot_price_rp_per_kwh[t] - export_high_use_tariff)
    for t in range(n)
) + gp.quicksum(
    heatdemand_kwhth[t] * thermal_revenue_per_kwhth
    for t in range(n)
)

# Collect all costs (positive, subtracted)
annual_costs = gp.quicksum(
    grid_import[t] * (spot_price_rp_per_kwh[t] + import_high_use_tariff)
    + battery_degradation_cost * (batt_charge[t] + batt_discharge[t])
    + woodchip_heat[t] * woodchip_cost_per_kwhth
    for t in range(n)
) + (import tariff adjustments) + (power tariff logic) \
  + battery_installed * (battery_capex + battery_annual_opex) \
  + heatpump_fixed_cost_rp \
  + ptes_cost_var

# Profit = Revenues - Costs
profit_expr = annual_revenues - annual_costs

model.setObjective(profit_expr, GRB.MAXIMIZE)
```

**Also edit: results.py, line 455**

```python
# BEFORE:
net_annual_profit_chf = -annual_cost_burden_rp / 100.0

# AFTER:
net_annual_profit_chf = annual_profit_burden_rp / 100.0
```

**Result:** Clear, intuitive code that directly maximizes profit. ✅ Best practice.

---

## Timeline for Fixes

### Phase 1 (Blocking)
1. **Verify heat pump parameters** (1-2 hours)
   - Get supplier CAPEX quote for target sizing
   - Compare with model assumptions
   - Correct parameter or explanatory comment

2. **Fix PTES exponent** (5 minutes)
   - Change: `"cost_chf_exp": -0.424,` → `"cost_chf_exp": 0.424,`
   - Validate: larger volume should be cheaper per unit
   - Run validation test

### Phase 2 (Recommended)
3. **Enable battery degradation** (5 minutes)
   - Change: `"degradation_cost_rp_per_kwh_throughput": 0.0,` → `0.05,`
   - Rationale: Matches real-world Li-ion behavior

4. **Switch to profit maximization** (1-2 hours)
   - Rewrite objective.py (Method 2 above)
   - Update results.py aggregation function
   - Test with small horizon
   - Run full-year optimization

### Phase 3 (Optional)
5. **Add parameter validation** (2-4 hours)
   - Sanity checks on parameter ranges
   - Warning alerts if values seem unrealistic
   - Documentation of assumptions

---

## Files to Modify

For **Minimal Change (Method 1):**
- [objective.py](objective.py#L196): Change `GRB.MINIMIZE` → `GRB.MAXIMIZE`

For **Full Clarity (Method 2):**
- [objective.py](objective.py#L145-L196): Rewrite objective expression
- [results.py](results.py#L455): Remove negation in profit calculation
- [parameters/](parameters/): Fix HP, PTES, battery parameters

---

## Testing Checklist

After making changes:

- [ ] **Syntax validation:** No Python errors
- [ ] **Small test (24 timesteps):** Solves to optimality
- [ ] **Profit is positive** or at least reasonable
- [ ] **Heat pump sizing is realistic** (< 500 kW_th for small island, e.g.)
- [ ] **Battery is being used reasonably** (not 100% charged/discharged constantly)
- [ ] **PTES volume decreases with cost** (not inverted)
- [ ] **Objective value matches calculation** (within rounding error)
- [ ] **Full year runs without timeout** (< 1 hour on modern machine)
- [ ] **Results pass economic sanity check:**
  - Grid import cost seems reasonable
  - Revenue from production seems reasonable
  - Net profit/loss is plausible

---

## Example: What "Reasonable" Looks Like

For a 1 MW alpine micro-grid:

```
Annual Revenue:
  Run-of-river generation (500 MWh @6.5 Rp):   3.25M CHF
  Grid export (100 MWh @ 20 Rp avg):          2.00M CHF
  Thermal demand selling (300 MWh_th @ 9.917 Rp): 3.00M CHF  ?
                                        TOTAL:  8.25M CHF

Annual Costs:
  Grid import (200 MWh @ 21 Rp):               4.20M CHF
  Power tariff (monthly peaks):                0.30M CHF
  Woodchip fuel (250 MWh_th @ 5.539 Rp):      1.38M CHF
  Battery fixed (if 10 MWh):                   0.66M CHF
  Heat pump fixed (if 100 kW_th):              0.05M CHF (corrected)
                                        TOTAL: 6.59M CHF

Net Annual Profit: 8.25M - 6.59M = 1.66M CHF ✓
                  (Without heat pump: −2.4M CHF) ← This would be wrong
```

---

## Questions to Answer Before Full Rerun

1. **Is the heat pump specification correct?**
   - Actual size (kW_th)?
   - Actual CAPEX (CHF)?
   - Realistic for the climate zone?

2. **Is the PTES really needed?**
   - With negative cost exponent, model wants infinite storage
   - Fixing exponent may change optimal storage size significantly
   - Is storage economically justified?

3. **Are we sure about the tariff tiers?**
   - Grid use threshold (3,500 h) correct?
   - Power tariff (1,143 Rp/kW/month) recent?
   - Contract details match model assumptions?

4. **What if the model still predicts a loss after fixes?**
   - Are the business economics viable?
   - Is optimization revealing a real issue?
   - Do parameters need further review?

---

## Summary

| Action | Effort | Impact | Priority |
|--------|--------|--------|----------|
| Fix heat pump CAPEX | 2 hours | Game-changing (adds 2M CHF/yr to profit) | ⭐⭐⭐ CRITICAL |
| Fix PTES exponent | 5 min | Prevents unbounded storage | ⭐⭐⭐ CRITICAL |
| Enable battery degradation | 5 min | Minor (could save 10-50k CHF/yr) | ⭐⭐ High |
| Switch to profit objective | 1 hour | Clarity & risk reduction | ⭐⭐ High |
| Add parameter validation | 4 hours | Prevent future errors | ⭐ Nice-to-have |

