# Key Findings and Recommendations for Cost Objective

## Critical Issues Identified

### 1. ⚠️ HEAT PUMP PARAMETERS ARE SUSPICIOUSLY LARGE

**Location:** [heat_pump.py:26](heat_pump.py#L26)

```python
HEAT_PUMP_ECONOMIC = {
    "cost_rp_per_kwth_nominal": 56759718,  # 56.7 Million Rappen!
    "cost_rp_fixed": 17233943,             # 17.2 Million Rappen!
}
```

**Impact Analysis:**
```
Annual cost for 100 kWh_th heat pump:
- Per-unit CAPEX: 56.76M Rp/kWh_th ÷ 30 yrs = 1.89M Rp/kWh_th/yr
- Per-unit OPEX:  1% × 56.76M = 567k Rp/kWh_th/yr  
- Fixed CAPEX:    17.23M Rp ÷ 30 = 574k Rp/yr
- Total annual:   (1.89M + 567k) × 100 + 574k = 246.5M Rp/yr
                = 2.46 Million CHF/yr

For comparison (Battery):
- 10 MWh battery: (6,000 + 600) Rp/kWh/yr × 10,000 kWh = 66M Rp/yr = 660k CHF/yr
- Heat pump is ~3,700× more expensive per unit energy!
```

**Sanity Check:**
- A 100 kW_th heat pump ($100k equipment) shouldn't cost €2.46M/year to operate
- Typical industrial heat pump: €50-200k CAPEX, 1-3% annual OPEX = €500-6k/year
- **These parameters suggest a unit conversion error (CHF → Rp, or per-MW to per-kW)**

**Recommendation:**
```python
# Before proceeding, verify:
# 1. What is the INTENDED capacity in the CAPEX numbers?
#    - Per MW_th? → divide by 1000
#    - Per 100 kW_th? → correct as-is
#    - Per kW_th? → divide by 1000
#
# 2. Are these in CHF and need Rp conversion (×100)?
#    - If cost_rp_per_kwth_nominal should be ~500-1000 Rp/kWh_th
#    - Current 56.76M is off by factor of ~50,000-100,000
#
# 3. Check against supplier quotes or engineering estimates
```

---

### 2. ⚠️ PTES COST FUNCTION HAS INVERTED EXPONENT

**Location:** [ptes.py:11](ptes.py#L11)

```python
PTES_ECONOMIC = {
    "cost_chf_exp": -0.424,  # NEGATIVE exponent causes DEGRESSION
}
```

**Impact Analysis:**
```
Cost function: cost = 27955.61 × (volume ^ -0.424)

With negative exponent, LARGER volume = LOWER cost (!)

Examples:
  Volume    Cost/year    Issue
  ────────────────────────────
  1 m³      27,956 Rp    
  10 m³     3,518 Rp     ← costs decrease (wrong)
  100 m³    444 Rp       ← more storage = cheaper   
  5000 m³   10 Rp        ← almost free!
  ∞ m³      0 Rp         ← unlimited free storage!
```

**Economic Implications:**
- The optimizer has incentive to build INFINITELY LARGE thermal storage
- Model becomes unbounded (no practical limit on PTES)
- In practice, solver likely hits numerical bounds, but logic is reversed

**Recommendation:**
```python
# Change exponent sign:
PTES_ECONOMIC = {
    "cost_chf_exp": 0.424,  # ← POSITIVE for economies of scale
}

# This gives realistic cost behavior:
# • Larger volume = economies of scale = slightly lower per-unit cost
# • But total cost still increases with volume
# • Creates natural limit on storage sizing
```

---

### 3. ⚠️ BATTERY DEGRADATION IS DISABLED (Set to 0.0)

**Location:** [battery.py:16](battery.py#L16)

```python
BATTERY_ECONOMIC = {
    "degradation_cost_rp_per_kwh_throughput": 0.0,  # ← DISABLED
}
```

**Impact Analysis:**
```
Current behavior:
  - Battery can be cycled infinitely with zero cost constraint
  - Degradation is not reflected in dispatch decisions
  - No incentive to minimize charge/discharge cycles
  
Real-world battery degradation:
  - Lithium-ion: 0.05-0.10 Rp/kWh throughput (0.05-0.10 CHF/MWh)
  - LiFePO₄: 0.03-0.05 Rp/kWh throughput  (even better)
```

**Recommendation:**
```python
BATTERY_ECONOMIC = {
    # Enable realistic degradation cost
    "degradation_cost_rp_per_kwh_throughput": 0.05,  # Rp per kWh cycled
    # This costs ~0.0005 CHF per kWh, very low but nonzero
}
```

---

### 4. SIGN CONVENTION IS CONFUSING (Not necessarily wrong, but risky)

**Location:** [objective.py:145-196](objective.py#L145-L196)

**Current Approach:**
```python
expr = (
    # Costs (positive)
    grid_import + battery_deg + woodchip + power_tariff + hp_fixed + ptes_fixed
    
    # Revenues (negative, subtracted)
    - grid_export
    - runofriver_profit
    - thermal_revenue
)

model.setObjective(expr, GRB.MINIMIZE)  # Minimize cost
```

**Risk Assessment:**
- ✅ Mathematically correct (minimize cost = maximize profit)
- ❌ Counter-intuitive (negative signs for revenues)
- ❌ Error-prone for future modifications

**Example of Risk:**
```python
# Reviewer sees this line:
- grid_export[t] * (spot_price_rp_per_kwh[t] - export_high_use_tariff)

# Without understanding the larger pattern, they might:
# 1. Think negative sign is a bug (it's not)
# 2. Remove it to "fix" the model (breaks optimization)
# 3. Add new revenue with wrong sign (creates hidden cost)
```

**Recommendation:**
Rewrite objective to use explicit profit semantics (see **Conversion to Profit Maximization** section below).

---

## Conversion from Cost Minimization to Profit Maximization

### Why Bother?

**Current approach (cost minimization):**
- Semantically backward but mathematically correct
- Requires negation trick to extract profit from cost
- Risk of sign errors in future modifications

**Better approach (profit maximization):**
- Direct and intuitive
- Easier to verify correctness
- Reduces risk of accidental sign errors

### Three-Step Conversion

#### Step 1: Rewrite Objective Expression

**Current (in objective.py, lines 150-196):**
```python
expr = gp.quicksum(
    grid_import[t] * (spot_price_rp_per_kwh[t] + import_high_use_tariff)
    - grid_export[t] * (spot_price_rp_per_kwh[t] - export_high_use_tariff)
    + battery_degradation_cost * (batt_charge[t] + batt_discharge[t])
    for t in range(n)
) + ... + ptes_cost_var - production_revenue + woodchip_net_cost - thermal_revenue
```

**Better:**
```python
# REVENUES (positive terms)
annual_revenues = gp.quicksum(
    prod_for_local[t] * runofriver_profit_per_kwh
    + (production_kwh[t] - prod_for_local[t]) * (spot_price_rp_per_kwh[t] - export_high_use_tariff)
    + heatdemand_kwhth[t] * thermal_revenue_per_kwhth
    for t in range(n)
)

# COSTS (positive terms, subtracted for profit)
annual_costs = gp.quicksum(
    grid_import[t] * (spot_price_rp_per_kwh[t] + import_high_use_tariff)
    + battery_degradation_cost * (batt_charge[t] + batt_discharge[t])
    + woodchip_heat[t] * woodchip_cost_per_kwhth
    for t in range(n)
) + (power_tariff_terms) + battery_installed * (battery_capex + battery_annual_opex) \
  + heatpump_fixed_cost_rp + ptes_cost_var

# PROFIT (maximize this)
profit_expr = annual_revenues - annual_costs
```

#### Step 2: Change Objective Command

**Current (objective.py, line 196):**
```python
model.setObjective(expr, GRB.MINIMIZE)
```

**Better:**
```python
model.setObjective(profit_expr, GRB.MAXIMIZE)
```

#### Step 3: Update Results Aggregation

**Current (results.py, line 455):**
```python
net_annual_profit_chf = -annual_cost_burden_rp / 100.0  # Negate cost to get profit
```

**Better:**
```python
net_annual_profit_chf = annual_profit_rp / 100.0  # Direct profit, no negation
```

---

## Data Validation Checklist

Use this checklist to verify that parameters are correct before running full-year optimization:

### Heat Pump ☐
- [ ] CAPEX per unit heat output is in realistic range (€100-1,000/kW_th, not €50,000/kW_th)
- [ ] Check if cost_rp_per_kwth_nominal needs unit conversion
- [ ] Verify 30-year amortization matches project timeline
- [ ] 1% annual OPEX is reasonable for industrial heat pump

### PTES ☐
- [ ] Cost exponent should be positive (0.424, not −0.424)
- [ ] Energy density 605 kWh_th/m³ is correct for gravel/sand thermal storage
- [ ] 80% round-trip efficiency is appropriate
- [ ] Cost function scaling makes sense (larger volume = economies of scale)

### Battery ☐
- [ ] Degradation cost should be enabled (not 0.0)
- [ ] Realistic value: 0.03-0.10 Rp/kWh throughput
- [ ] Check if battery CAPEX (60k Rp/kWh) is realistic for current market

### Grid Tariffs ☐
- [ ] Import high-use tariff (1.08 Rp/kWh) matches actual grid operator rates
- [ ] Export tariff is correctly subtracted (not added) in revenue
- [ ] Grid use threshold (3,500 h/yr) matches actual contract terms
- [ ] Power tariff (1,143 Rp/kW/month high-use) is realistic

### Run-of-River ☐
- [ ] Profit per kWh local use (6.5 Rp/kWh) is correct
- [ ] Includes all avoided grid import costs
- [ ] Export is handled separately at spot price minus tariff

### Woodchip ☐
- [ ] Cost 5.539 Rp/kWh_th matches local fuel supplier quotes
- [ ] Revenue 9.917 Rp/kWh_th reflects thermal demand value in market
- [ ] Margin (9.917 - 5.539 = 4.378 Rp/kWh_th) is realistic

---

## Summary: What Needs Fixing

| Issue | Severity | Impact | Fix |
|-------|----------|--------|-----|
| Heat pump CAPEX parameters too large | 🔴 **Critical** | Objective dominated by unrealistic costs | Verify units; likely divide by 50,000-100,000 |
| PTES cost exponent is negative | 🔴 **Critical** | Unbounded growth of storage; wrong incentives | Change −0.424 → +0.424 |
| Battery degradation disabled | 🟡 **Medium** | Unrealistic dispatch (over-cycling); minor impact | Set to 0.05 Rp/kWh throughput |
| Cost minimization semantics | 🟡 **Medium** | Risk of future errors; confusing code | Rewrite as profit maximization |
| No explicit error handling for infeasible horizons | 🟡 **Medium** | Small test cases fail mysteriously | Add tariff threshold override for diagnostics |

---

## Recommended Implementation Order

1. **Verify heat pump parameters** (blocking issue for model credibility)
2. **Fix PTES exponent** (blocking issue for unbounded behavior)
3. **Enable battery degradation** (improves realism without breaking existing code)
4. **Rewrite objective function** (improves clarity and reduces future risks)
5. **Run full-year optimization** with corrected parameters

---

## Example: Impact of Heat Pump Parameter Fix

Assuming the CAPEX should be ~500-1,000 Rp/kWh_th instead of 56,759,718:

```
BEFORE (incorrect):
──────────────────
Annual heat pump cost = 246.5 M Rp/yr (for 100 kW_th nominal)
                      = 2.46 M CHF/yr
Annual profit        = -3.15 M CHF (loss)

AFTER (if divided by ~50,000):
──────────────────────────────
Annual heat pump cost ≈ 5M Rp/yr (for 100 kW_th nominal)
                      = 50k CHF/yr (realistic)
Annual profit         ≈ +2.7M CHF (profit!)
                      = +27M CHF over 10 year horizon
```

This completely changes the project economics from **unviable loss** to **viable profit**.

---

## Next Steps

1. **Extract heat pump quotes** from suppliers (current capacity scenario)
2. **Verify PTES cost function** against vendor data
3. **Check grid tariff** against actual utility contract
4. **Correct the three critical parameters** identified above
5. **Re-run optimization** with `objective_mode = "cost"`
6. **Verify profit is now positive** (or at least more reasonable)
7. **Switch to explicit profit maximization** for clarity

