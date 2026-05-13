# Cost Minimization ↔ Profit Maximization: Visual Flow

## The Confusing Part: Current Implementation

```
┌─────────────────────────────────────────────────────────────────────────┐
│                     CURRENT OBJECTIVE FUNCTION                          │
│                      (Semantically Backwards)                           │
└─────────────────────────────────────────────────────────────────────────┘

                        MINIMIZE expr

                    expr = costs - revenues
                    
                    = (import + battery + woodchip + fixed)
                      - (export + production + thermal)

            When you MINIMIZE (costs - revenues),
         you're actually MAXIMIZING (revenues - costs)
                    = MAXIMIZING PROFIT


SIGN CONVENTION IN CODE:
┌────────────────────────────────────────────────────────────────┐
│  Costs    → ADDED    (+)  to expr                              │
│  Revenues → SUBTRACTED (-) to expr                             │
│                                                                │
│  Why?  Because minimizing (costs - revenues)                  │
│        = minimizing costs relative to revenues                │
│        = maximizing profit                                    │
└────────────────────────────────────────────────────────────────┘
```

---

## The Clear Way: Profit Maximization

```
┌─────────────────────────────────────────────────────────────────────────┐
│            PROFIT-FIRST OBJECTIVE FUNCTION                              │
│                  (Directly Maximizes Profit)                            │
└─────────────────────────────────────────────────────────────────────────┘

                        MAXIMIZE profit_expr

                profit_expr = revenues - costs
                    
                = (export + production + thermal)
                  - (import + battery + woodchip + fixed)

            When you MAXIMIZE (revenues - costs),
              you're directly MAXIMIZING PROFIT


SIGN CONVENTION IN CODE:
┌────────────────────────────────────────────────────────────────┐
│  Revenues → ADDED    (+)  to profit_expr                       │
│  Costs    → SUBTRACTED (-) from profit_expr                    │
│                                                                │
│  This is intuitive and correct.                               │
└────────────────────────────────────────────────────────────────┘
```

---

## Conversion Formula

```
Current Implementation (Confusing):
═══════════════════════════════════

expr_cost = (import + battery + woodchip_fuel + power_tariff + HP_fixed + PTES_fixed)
            - (export + runofriver + thermal)

model.setObjective(expr_cost, GRB.MINIMIZE)  ← minimize cost

Result:
profit = -expr_cost / 100  (Rp to CHF)


Better Implementation (Clear):
══════════════════════════════

expr_profit = (export + runofriver + thermal)
              - (import + battery + woodchip_fuel + power_tariff + HP_fixed + PTES_fixed)

model.setObjective(expr_profit, GRB.MAXIMIZE)  ← maximize profit

Result:
profit = expr_profit / 100  (Rp to CHF)


KEY INSIGHT:
════════════
expr_cost = K - expr_profit   (where K is a constant-ish term)

Therefore:
minimize(expr_cost) = minimize(K - expr_profit) 
                    = maximize(expr_profit)

Both approaches give the SAME OPTIMIZATION,
but the second is clearer semantically.
```

---

## Detailed Component Breakdown: Where Each Variable Appears

### TIMESTEP COSTS/REVENUES (Summed over n=365×24×4=35,040 timesteps for 1 year)

```
┌──────────────────────────────────┐
│  GRID ELECTRICITY (Time-Varying) │
└──────────────────────────────────┘

IMPORT (COST):
  Rp_cost = grid_import[t] × (spot_price[t] + import_tariff[t])
  
  Example: Import 100 kWh at 20 Rp/kWh base + 1.08 Rp/kWh tariff
  = 100 × 21.08 = 2,108 Rp cost

EXPORT (REVENUE, shown as negative cost):
  -Rp_revenue = -grid_export[t] × (spot_price[t] - export_tariff[t])
  
  Example: Export 50 kWh at 20 Rp/kWh base - 1.08 Rp/kWh tariff
  = -50 × 18.92 = -946 Rp (= +946 Rp profit)

─────────────────────────────────────────────────────────────────

┌──────────────────────────────────┐
│  RENEWABLE PRODUCTION (Revenue)  │
└──────────────────────────────────┘

LOCAL USE (REVENUE, shown as negative cost):
  -Rp_revenue = -prod_for_local[t] × 6.5 Rp/kWh
  
  Example: 80 kWh used locally
  = -80 × 6.5 = -520 Rp (= +520 Rp profit)

EXPORT (INCLUDED IN GRID EXPORT ABOVE):
  Already counted in grid_export revenue

─────────────────────────────────────────────────────────────────

┌──────────────────────────────────┐
│  THERMAL ENERGY (Mixed)          │
└──────────────────────────────────┘

WOODCHIP FUEL (COST):
  Rp_cost = woodchip_heat[t] × 5.539 Rp/kWh_th
  
  Example: 200 kWh_th from woodchip
  = 200 × 5.539 = 1,107.8 Rp cost

THERMAL REVENUE (REVENUE, shown as negative cost):
  -Rp_revenue = -heatdemand[t] × 9.917 Rp/kWh_th
  
  Example: Sell 200 kWh_th of heat demand
  = -200 × 9.917 = -1,983.4 Rp (= +1,983.4 Rp profit)

NET THERMAL: +1,983.4 - 1,107.8 = +875.6 Rp profit per 200 kWh_th
            (thermal revenue > woodchip cost = profitable)

─────────────────────────────────────────────────────────────────

┌──────────────────────────────────┐
│  BATTERY (Storage Overhead)      │
└──────────────────────────────────┘

DEGRADATION (COST):
  Rp_cost = battery_degradation_cost × (batt_charge[t] + batt_discharge[t])
  
  Current: battery_degradation_cost = 0.0 Rp/kWh throughput
           → Effectively DISABLED
  
  If enabled: 100 kWh charged + 95 kWh discharged (5% loss)
  = cost × 195 = 0 Rp (disabled)

FIXED ANNUAL (COST):
  Handled separately in annual lump-sum (see below)

```

### ANNUAL FIXED COSTS (Added Once Per Optimization Run)

```
┌───────────────────────────────────┐
│  BATTERY ANNUAL FIXED (12,000 CHF) │
└───────────────────────────────────┘

If installed (battery_installed = 1):
  Cost = (CAPEX + OPEX) × capacity × battery_installed
       = (60,000/10 + 600) × 10,000 × 1
       = 6,600 × 10,000
       = 66,000,000 Rp/yr
       = 660,000 CHF/yr

If not installed (battery_installed = 0):
  Cost = 0


┌─────────────────────────────────────────────┐
│  HEAT PUMP ANNUAL FIXED (Huge! ~7.4M CHF)   │
└─────────────────────────────────────────────┘

Depends on heatpump_nominal (decision variable, kWh_th):

Per-unit costs:
  CAPEX amortized = 56,759,718 Rp/kWh_th / 30 yr = 1,891,990 Rp/kWh_th/yr
  Annual OPEX     = 1% × 56,759,718 = 567,597 Rp/kWh_th/yr
  Per-unit total  = 2,459,587 Rp/kWh_th/yr

Fixed costs:
  Fixed CAPEX amortized = 17,233,943 / 30 = 574,465 Rp/yr

Total annual heat pump cost:
  Cost = (2,459,587 × heatpump_nominal) + 574,465

Example if nominal = 100 kWh_th:
  = (2,459,587 × 100) + 574,465
  = 246,533,165 Rp/yr
  = 2,465,332 CHF/yr


⚠️ ALERT: These heat pump costs are ENORMOUS because:
   - CAPEX per unit = 56.76 M Rp (56 million rappen!)
   - For 100 kWh_th nominal, that's 5.676 billion Rp one-time
   - Amortized over 30 years: 2.46 M CHF/yr per 100 kWh_th

   This may be a data entry error. Verify units!


┌──────────────────────────────────┐
│  PTES ANNUAL FIXED (~0.75M CHF)  │
└──────────────────────────────────┘

Nonlinear function of volume chosen (ptes_volume_m3):

Cost = 27,955.61 × (ptes_volume_m3 ^ -0.424)

Examples:
  1 m³:    27,955.61 × 1^(-0.424)     = 27,955.61 Rp/yr (278 CHF)
  10 m³:   27,955.61 × 10^(-0.424)    = 3,518.37 Rp/yr (35 CHF) ← This shouldn't decrease!
  100 m³:  27,955.61 × 100^(-0.424)   = 443.55 Rp/yr (4 CHF)  ← Bug in exponent?
  1000 m³: 27,955.61 × 1000^(-0.424)  = 55.89 Rp/yr (0.56 CHF)
  5000 m³: 27,955.61 × 5000^(-0.424)  = 10.39 Rp/yr (0.10 CHF)

⚠️ ALERT: The negative exponent (-0.424) makes LARGER storage CHEAPER!
   This is economically nonsensical. Check if the exponent should be positive.


┌──────────────────────────────────┐
│  MONTHLY POWER TARIFF (~0.1M CHF)│
└──────────────────────────────────┘

Fixed per month based on max demand that month:

Cost = sum(monthly_peak_kw[m] × power_tariff_Rp_per_kw_per_month) × 12 months

Tariff depends on annual grid use tier:
  High grid use (>3500 h):  1,143 Rp/kW/month
  Low grid use (≤3500 h):    502 Rp/kW/month

Example (high use tier):
  Peak demand = 100 kW
  = 100 × 1,143 × 12 = 1,371,600 Rp/yr = 13,716 CHF/yr


┌────────────────────────────────────┐
│  SUMMARY OF ANNUAL FIXED COSTS     │
└────────────────────────────────────┘

Battery fixed:         66,000,000 Rp/yr (typical)
Heat pump fixed:      246,533,165 Rp/yr (for 100 kWh_th—HUGE!)
PTES fixed:            10,390 Rp/yr (for 5000 m³—very small)
Power tariff:          1,371,600 Rp/yr (typical)
────────────────────────────────────────────────
TOTAL FIXED:          ~313,916,155 Rp/yr

= ~3,139,162 CHF/yr (nearly 3.1 M CHF just in fixed costs!)

Note: The heat pump dominates, suggesting a possible parameter error.

```

---

## Step-by-Step Conversion: Cost → Profit for 1 Year

```
GIVEN:
  annual_import_cost_rp         = 5,000,000 Rp
  annual_export_revenue_rp      = 2,000,000 Rp
  annual_battery_degradation_rp = 0 Rp
  annual_runofriver_profit_rp   = 3,000,000 Rp
  annual_woodchip_cost_rp       = 1,500,000 Rp
  annual_thermal_revenue_rp     = 2,000,000 Rp
  annual_power_cost_rp          = 1,000,000 Rp
  annual_battery_fixed_cost_rp  = 66,000,000 Rp
  annual_heatpump_fixed_cost_rp = 246,533,165 Rp
  annual_ptes_fixed_cost_rp     = 10,390 Rp
  ──────────────────────────────────────────
  total costs:                    = 322,043,555 Rp
  total revenues:                 = 7,000,000 Rp


CURRENT COST-MINIMIZATION APPROACH:
═══════════════════════════════════

annual_cost_burden_rp = (
    annual_import_cost_rp           (+5,000,000)
    - annual_export_revenue_rp      (−2,000,000)
    + annual_battery_degradation_rp (+        0)
    - annual_runofriver_profit_rp   (−3,000,000)
    + annual_woodchip_cost_rp       (+1,500,000)
    - annual_thermal_revenue_rp     (−2,000,000)
    + annual_power_cost_rp          (+1,000,000)
    + annual_battery_fixed_cost_rp  (+66,000,000)
    + annual_heatpump_fixed_cost_rp (+246,533,165)
    + annual_ptes_fixed_cost_rp     (+   10,390)
)

= 5,000,000 - 2,000,000 + 0 - 3,000,000 + 1,500,000 - 2,000,000 + 1,000,000 + 66,000,000 + 246,533,165 + 10,390
= 313,043,555 Rp (cost)

net_annual_profit_chf = -313,043,555 / 100
                      = -3,130,435.55 CHF (LOSS)


CLEAR PROFIT-MAXIMIZATION APPROACH:
═══════════════════════════════════

annual_revenue_rp = (
    annual_export_revenue_rp             (+2,000,000)
    + annual_runofriver_profit_rp        (+3,000,000)
    + annual_thermal_revenue_rp          (+2,000,000)
)
= 7,000,000 Rp

annual_cost_rp = (
    annual_import_cost_rp                (+5,000,000)
    + annual_battery_degradation_rp      (+        0)
    + annual_woodchip_cost_rp            (+1,500,000)
    + annual_power_cost_rp               (+1,000,000)
    + annual_battery_fixed_cost_rp       (+66,000,000)
    + annual_heatpump_fixed_cost_rp      (+246,533,165)
    + annual_ptes_fixed_cost_rp          (+   10,390)
)
= 314,043,555 Rp

net_annual_profit_rp = annual_revenue_rp - annual_cost_rp
                     = 7,000,000 - 314,043,555
                     = -307,043,555 Rp (LOSS)

net_annual_profit_chf = -307,043,555 / 100
                      = -3,070,435.55 CHF (LOSS)


Ah! The profit calculation differs because cost_burden includes additional negations.
The current formula has an accounting error in how it combines revenues and costs.

Let me recalculate:

CORRECT COST-BURDEN APPROACH:
════════════════════════════

The code says:
  annual_cost_burden = (import) - (export) + (degradation) - (production) + (woodchip) - (thermal) + (power) + (battery) + (heatpump) + (ptes)

Regrouping by cost vs revenue:
  = (import + degradation + woodchip + power + battery + heatpump + ptes)   [costs]
    - (export + production + thermal)   [revenues]

  = (costs) - (revenues)
  = 322,043,555 - 7,000,000
  = 315,043,555 Rp

net_profit = -315,043,555 / 100 = -3,150,435.55 CHF

So a LOSS of ~3.15 M CHF/yr.


INTERPRETATION:
════════════════

With current parameters:
- Your system spends ~3.2M CHF/yr on fixed costs alone
- It only generates ~70k CHF/yr in revenues from exports + production + thermal sales
- Net loss = ~3.15M CHF/yr

The heat pump cost dominates (2.46M CHF/yr for just 100 kWh_th nominal).
This suggests the heat pump parameter is WRONG (unit error?) or vastly oversized.

```

---

## What to Check

### 1. Heat Pump Parameters (Most Suspicious)
```python
# In heat_pump.py:
HEAT_PUMP_ECONOMIC = {
    "cost_rp_per_kwth_nominal": 56759718,  ← 56.7 M Rp per kWh_th!
    "cost_rp_fixed": 17233943,             ← 17.2 M Rp fixed
    ...
}

This seems VERY HIGH. 

Sanity check:
- A 100 kWh_th heat pump = 56.7M × 100 = 5.67 BILLION Rp (€56.7M)
- Per year amortized: €1.89M/yr just for CAPEX
- Plus €567k/yr OPEX
- Total: €2.46M/yr for a single device!

Is this in units of:
- Rp (rappen)? → OK, 56M rappen ≈ €560k
- CHF (francs)? → Wrong! Should be divided by 100
- Some other unit?

Compare with battery:
  60,000 Rp/kWh for 10 MWh = €600/kWh
  Heat pump is 56,759,718 Rp/kWh = €567,597/kWh
  
  That's 900× more expensive per unit!
```

### 2. PTES Parameters (Exponent Seems Wrong)
```python
# In ptes.py:
PTES_ECONOMIC = {
    "cost_rp_per_year_factor": 838668.4 / 30,
    "cost_chf_exp": -0.424,  ← NEGATIVE exponent!
}

With negative exponent:
- Larger volume → CHEAPER per unit (unusual)
- This creates an incentive to build HUGE storage (infinite size = free!)

Should probably be positive exponent like -0.424 → 0.424
(typical economies of scale: cost ∝ V^0.4)
```

### 3. Battery Degradation (Disabled)
```python
battery_degradation_cost = 0.0 Rp/kWh throughput

Currently disabled. Should be:
- 0.1-0.5 Rp/kWh throughput for realistic battery wear
```

---

## Conclusion

**Current Implementation:**
- Cost minimization (semantically backward)
- Multiple accounting sign errors or unclear design
- Dominated by potentially incorrect heat pump costs
- PTES cost function has nonsensical negative exponent

**Recommended Actions:**
1. Verify heat pump parameters (cost per kW_th seems very high)
2. Fix PTES exponent (should be positive for economies of scale)
3. Enable battery degradation cost
4. Rewrite objective with explicit profit semantics (revenue - cost)
5. Switch from MINIMIZE to MAXIMIZE (one-line change)

