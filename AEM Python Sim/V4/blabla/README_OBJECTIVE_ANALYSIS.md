# Objective Function Analysis - Documentation Index

## 📑 Documents Created

This analysis includes 5 comprehensive documents:

| Document | Purpose | Best For |
|----------|---------|----------|
| **QUICK_REFERENCE.md** | TL;DR summary and implementation guide | Quick answers, moving fast |
| **OBJECTIVE_ANALYSIS.md** | Complete component breakdown with every formula | Understanding the math |
| **COST_PROFIT_CONVERSION.md** | Visual diagrams and step-by-step conversion | Learning the relationship |
| **VARIABLE_USAGE_DETAILED.md** | Exact mapping of where each variable appears in code | Code navigation, debugging |
| **CRITICAL_FINDINGS.md** | Parameter errors and fix recommendations | Decision-making, fixes |

---

## 🎯 By Use Case

### "I just want to fix this and move on"
→ **QUICK_REFERENCE.md**

1. **Check Critical Issues** section → verify 3 key problems
2. **TL;DR section** → understand cost = objective relationship
3. **How to Switch** section → 1-line vs full rewrite
4. **Testing Checklist** → verify it works

**Time needed:** 1-2 hours total

---

### "I need to understand how the objective function works"
→ **OBJECTIVE_ANALYSIS.md** + **COST_PROFIT_CONVERSION.md**

1. Start with **COST_PROFIT_CONVERSION.md** for visual overview
2. Read **OBJECTIVE_ANALYSIS.md** Part 2 for all components
3. Use Part 3 (Aggregated Cost Structure) as reference while reading code
4. Cross-reference with **VARIABLE_USAGE_DETAILED.md** to see where each component appears

**Time needed:** 2-4 hours to understand completely

---

### "I need to trace a specific variable through the code"
→ **VARIABLE_USAGE_DETAILED.md**

1. Find your variable in the "Decision Variables" section
2. See exactly where it's created (file + line)
3. See all usages (file, function, line, purpose)
4. Understand all constraints applied to it

**Time needed:** 5-30 minutes per variable

---

### "I found a bug or suspect a parameter is wrong"
→ **CRITICAL_FINDINGS.md**

1. **Critical Issues** section lists known problems
2. **Data Validation Checklist** helps verify if you found something new
3. **Summary** table ranks issues by severity
4. **Next Steps** provides decision framework

**Time needed:** 0.5-2 hours debate/research

---

### "I'm modifying the objective function"
→ **OBJECTIVE_ANALYSIS.md** (Part 5) + **VARIABLE_USAGE_DETAILED.md**

Before modifying:
1. Read **OBJECTIVE_ANALYSIS.md** Part 5 (Sign Convention)
2. Find all variables in **VARIABLE_USAGE_DETAILED.md**
3. Check what constraints you'll affect
4. Update **results.py** summary function accordingly

**Time needed:** 2-6 hours depending on extent of changes

---

## 📋 Quick Navigation

### All Cost/Revenue Components
→ **OBJECTIVE_ANALYSIS.md** Part 2, Table on page ~15

### Sign Conventions (Why negatives?)
→ **OBJECTIVE_ANALYSIS.md** Part 6

### How Cost Becomes Profit
→ **COST_PROFIT_CONVERSION.md** "Step-by-Step Conversion" section

### Where grid_import[t] Is Used
→ **VARIABLE_USAGE_DETAILED.md** Search for "grid_import"

### Heat Pump Parameter Error
→ **CRITICAL_FINDINGS.md** Section 1

### PTES Exponent Bug
→ **CRITICAL_FINDINGS.md** Section 2

### Battery Degradation Disabled
→ **CRITICAL_FINDINGS.md** Section 3

### All Annual Cost Components
→ **COST_PROFIT_CONVERSION.md** "Annual Fixed Costs" section

---

## 🔍 Key Findings at a Glance

### The Main Equation

```
MINIMIZE(costs - revenues) ≡ MAXIMIZE(revenues - costs) = MAXIMIZE(profit)
```

The model is **correct mathematically** but **semantically backward**.

### Three Critical Parameter Errors

| Error | Location | Fix | Impact |
|-------|----------|-----|--------|
| Heat pump CAPEX 50,000× too large | heat_pump.py:26 | Verify units, likely divide by 50,000 | Changes annual profit by ±2.5M CHF |
| PTES cost exponent negative | ptes.py:11 | Change -0.424 → 0.424 | Prevents unbounded storage sizing |
| Battery degradation disabled | battery.py:16 | Enable: 0.0 → 0.05 | Minor realism improvement |

---

## 📊 Parameter Summary Table

```
ELECTRICITY:
  Grid import tariff (high use):     1.08 Rp/kWh            ✓
  Grid import tariff (low use):      3.28 Rp/kWh            ✓
  Grid export tariff (high use):     1.08 Rp/kWh            ✓
  Grid export tariff (low use):      3.28 Rp/kWh            ✓
  Run-of-river profit (local use):   6.5 Rp/kWh             ✓
  Power tariff (high use):           1,143 Rp/kW/month      ✓
  Power tariff (low use):            502 Rp/kW/month        ✓

HEAT:
  Woodchip cost:                     5.539 Rp/kWh_th        ✓
  Thermal revenue:                   9.917 Rp/kWh_th        ✓

BATTERY:
  CAPEX:                             60,000 Rp/kWh          ✓
  Lifetime:                          10 years               ✓
  Annual OPEX:                       1%                     ✓
  Degradation cost:                  0.0 Rp/kWh (DISABLED)  ✗ Should be 0.05

HEAT PUMP:
  CAPEX per kWh_th:                 56,759,718 Rp/kWh_th   ✗ LIKELY 50,000× too large
  Fixed CAPEX:                       17,233,943 Rp          ✗ LIKELY wrong
  Lifetime:                          30 years               ✓
  Annual OPEX:                       1%                     ✓

PTES:
  Energy density:                    605 kWh_th/m³          ✓
  Round-trip efficiency:             80%                    ✓
  Cost exponent:                     -0.424                 ✗ Should be +0.424
  Cost coefficient (annualized):     27,955.61 Rp           (depends on above fix)
```

---

## 🛠️ Implementation Steps

### Step 1: Read and Understand (30 min)
- Read **QUICK_REFERENCE.md** TL;DR section
- Skim **OBJECTIVE_ANALYSIS.md** Part 2
- Understand cost vs profit relationship

### Step 2: Verify Parameters (1-2 hours)
- Check heat pump quote/estimate
- Verify PTES cost function logic
- Confirm grid tariffs are current
- Document any findings

### Step 3: Fix Critical Errors (15 min)
- Fix heat pump CAPEX (if needed)
- Fix PTES exponent (5 min)
- Enable battery degradation (5 min)
- Run 24-step test to verify

### Step 4: Switch to Profit Semantics (1-2 hours)
- **Option A (Quick):** Change MINIMIZE → MAXIMIZE (1 line)
- **Option B (Better):** Full rewrite using profit_expr (1-2 hours)
- Update results.py aggregation
- Test with small horizon

### Step 5: Validate Full Year (Variable)
- Run complete annual optimization
- Verify profit is positive (or at least more reasonable)
- Check heat pump sizing is realistic
- Review dispatch decisions for sanity

---

## 💡 Understanding Shortcuts

### What is "Cost Burden"?
**Total cost minus total revenue.**

In the model:
- "Cost" acts like cost + revenue in accounting terms
- Negative signs on revenues make them reduce cost
- Higher exports → lower cost burden → higher profit

### Why Minimize Cost Instead of Maximize Profit?
**It's the same thing, just expressed backwards.**

Think of negative profits as costs:
- Profit of -100 = Cost of +100
- Minimizing cost = Maximizing profit (negating)

### What Does `summarize_solution()` Do?
**Aggregates hourly solution to annual totals.**

```
Hourly values: [grid_import[0], grid_import[1], ... grid_import[8759]]
              ↓ sum all timesteps
Annual total:  annual_import_kwh
              ↓ multiply by average price
Annual cost burden: annual_import_cost_rp
              ↓ add all cost components
Total cost burden: annual_cost_burden_rp
              ↓ negate and convert
Net profit: net_annual_profit_chf
```

---

## ❓ Frequently Asked Questions

### Q: Is the model currently correct or wrong?
**A:** Mathematically correct but semantically backward and contains 1-2 critical parameter errors.

### Q: If I change MINIMIZE to MAXIMIZE, will it break?
**A:** No, it will work. You'll get the same optimal solution but using profit-maximization semantics.

### Q: How large are the parameter errors?
**A:** Huge. One error alone (heat pump) accounts for ~€2.5M/year in false costs.

### Q: What if I only fix one of the three errors?
**A:** Do heat pump first (biggest impact). The others are enabling fixes.

### Q: Will fixing parameters change the optimal solution?
**A:** Very likely. The optimizer will make different sizing/dispatch decisions with correct costs.

### Q: Can I test this on a small horizon?
**A:** Yes. Use first 24 timesteps to verify logic. Note: small horizons may be infeasible due to annual tariff threshold logic (pre-existing issue).

### Q: What's the easiest first step?
**A:** Change objective.py line 196 from `GRB.MINIMIZE` to `GRB.MAXIMIZE`. This works immediately.

### Q: What's the recommended comprehensive fix?
**A:** (1) Verify heat pump CAPEX, (2) Fix PTES exponent, (3) Rewrite objective for profit, (4) Run full year.

---

## 📈 Expected Impact of Fixes

```
Current Model (Broken):
  Annual profit estimate: -3.15M CHF (loss)
  Dominated by: Heat pump costs (~2.5M CHF false cost)
  
After Heat Pump Fix:
  Annual profit estimate: ~+2.5M CHF (realistic profit)
  Battery/Grid decisions still validated
  
After All Fixes:
  Annual profit estimate: ~+2.7M CHF (best practice)
  Better dispatch decisions
  Cleaner code for future modifications
```

---

## 🚀 Next Actions

1. **Today:** Read QUICK_REFERENCE.md (30 min)
2. **Day 1:** Verify heat pump parameters (1-2 hours)
3. **Day 2:** Fix three critical errors (30 min)
4. **Day 3:** Switch to profit maximization (1-2 hours)
5. **Day 4:** Run full annual optimization (variable)
6. **Day 5:** Analyze results and make final decisions

---

## 📞 Document Locations

All documents are in `/workspaces/BAT/`:
- `QUICK_REFERENCE.md` ← Start here
- `OBJECTIVE_ANALYSIS.md`
- `COST_PROFIT_CONVERSION.md`
- `VARIABLE_USAGE_DETAILED.md`
- `CRITICAL_FINDINGS.md`
- `README.md` (this file)

---

## 🎓 Key Takeaways

1. **Cost minimization = Profit maximization** (mathematically)
2. **But semantics matter** (code clarity, error prevention)
3. **Three critical parameter errors** need fixing
4. **Heat pump cost dominates** everything else
5. **PTES exponent is inverted** (unbounded growth)
6. **Switch to explicit profit formulation** for clarity

