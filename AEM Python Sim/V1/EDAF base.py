from pyomo.environ import *
import numpy as np
import pandas as pd

# -------------------------
# INPUT DATA (single df)
# -------------------------
# Expect df to contain at least:
# - 'TimestampInUtc'  (or whatever your timestamp column is called)
# - 'Sales'
# - 'Total Production Hydro]'           <-- using EXACT name you provided
# - 'Spot price [Rp/kWh]'

df = pd.read_csv('/workspaces/BAT/AEM Python Sim/Data Sorting/DATA/AEM TOTAL 2024_corrected.csv')
df['DateTime'] = pd.to_datetime(df['DateTime'])

# # Ensure timestamp index (optional but recommended)
# if 'TimestampInUtc' in df.columns:
#     df['TimestampInUtc'] = pd.to_datetime(df['TimestampInUtc'])
#     df = df.sort_values('TimestampInUtc').set_index('TimestampInUtc')
# elif df.index.name == 'TimestampInUtc':
#     df = df.copy()
#     df.index = pd.to_datetime(df.index)
#     df = df.sort_index()
# else:
#     # If you truly have no timestamp column, we just assume df is already in correct chronological order.
#     df = df.copy()

# Map your columns to the model signals
load = df['Sales'].values
hydro = df['Total Production Hydro'].values
spotprice = df['Spot price [Rp/kWh]'].values

# -------------------------
# TIME SETUP (WHOLE YEAR)
# -------------------------
deltat = 0.25  # hours (15 minutes)
num_periods = len(df)  # <-- IMPORTANT: use full year length (e.g., 365*96 = 35040)

# Basic sanity checks (optional but helpful)
assert len(load) == num_periods
assert len(hydro) == num_periods
assert len(spotprice) == num_periods

# -------------------------
# PARAMETERS
# -------------------------
feedin_hydro = 33  # Rp/kWh (keep your value, rename for clarity)

objective_selector = 1  # 1=min cost, 2=min grid peak, 3=max self-consumption (min import)

# Storage parameters
SOC_max = 95
SOC_min = 5
charge_eff = 0.95
discharge_eff = 0.95
P_ES_discharge_max = 30
SOC_init = 50
SOC_end = 50  # for a year horizon, keeping end SOC = start SOC is common but optional

cost_per_kwh_storage = (100000 / (12.5 * 365))  # Rp/kWh-ish, as in your original

P_grid_max = 100

# Grid cost signal (formerly dfcost['vario_plus'])
cost_grid = spotprice

# Hydro production profile (formerly P_solar_profile)
P_hydro_profile = hydro

# -------------------------
# PYOMO MODEL
# -------------------------
model = ConcreteModel()

# Sets
model.T = RangeSet(0, num_periods - 1)

# Design variables
model.E_ES_max = Var(bounds=(0, 500), initialize=100, within=NonNegativeReals)
model.P_ES_charge_capacity = Var(bounds=(0, P_grid_max), initialize=30, within=NonNegativeReals)

# Auxiliary for linearization
model.P_ES_charge_effective = Var(model.T, bounds=(0, P_grid_max), within=NonNegativeReals)

# Parameters
model.feedin_hydro = feedin_hydro
model.cost_grid = Param(
    model.T,
    within=Reals,
    initialize={i: float(cost_grid[i]) for i in range(num_periods)}
)

# Decision variables
model.P_hydro = Var(model.T, within=NonNegativeReals)
model.E_ES = Var(model.T, within=NonNegativeReals)
model.P_ES_charge = Var(model.T, within=NonNegativeReals)
model.P_ES_discharge = Var(model.T, within=NonNegativeReals)

model.P_grid = Var(model.T, within=Reals)
model.P_grid_peak = Var(within=NonNegativeReals)
model.P_grid_pos = Var(model.T, within=NonNegativeReals)
model.P_grid_neg = Var(model.T, within=NonNegativeReals)

model.grid_import = Var(model.T, within=Binary)
model.batterycharge_binary = Var(model.T, within=Binary)

# -------------------------
# CONSTRAINTS
# -------------------------

# Power balance (replace solar with hydro)
def grid_supply_rule(model, t):
    return model.P_grid[t] == load[t] - model.P_hydro[t] - model.P_ES_discharge[t] + model.P_ES_charge[t]
model.grid_supply = Constraint(model.T, rule=grid_supply_rule)

# Hydro generation constraint (no curtailment; change == to <= if you want curtailment)
def hydro_generation_rule(model, t):
    return model.P_hydro[t] == P_hydro_profile[t]
model.hydro_generation = Constraint(model.T, rule=hydro_generation_rule)

# SOC bounds
def energy_storage_upper_limit_rule(model, t):
    return model.E_ES[t] <= (SOC_max / 100) * model.E_ES_max
model.energy_storage_upper_limit = Constraint(model.T, rule=energy_storage_upper_limit_rule)

def energy_storage_lower_limit_rule(model, t):
    return model.E_ES[t] >= (SOC_min / 100) * model.E_ES_max
model.energy_storage_lower_limit = Constraint(model.T, rule=energy_storage_lower_limit_rule)

# Charging power upper limit with effective capacity
def charging_power_upper_limit_rule(model, t):
    if t == 0:
        return model.P_ES_charge[t] == 0
    return model.P_ES_charge[t] <= model.P_ES_charge_effective[t]
model.charging_power_upper_limit = Constraint(model.T, rule=charging_power_upper_limit_rule)

# Linearization: P_ES_charge_effective[t] = batterycharge_binary[t] * P_ES_charge_capacity
def linear_charge_effective_c1(model, t):
    if t > 0:
        return model.P_ES_charge_effective[t] <= P_grid_max * model.batterycharge_binary[t]
    return Constraint.Skip
model.linear_charge_effective_c1 = Constraint(model.T, rule=linear_charge_effective_c1)

def linear_charge_effective_c2(model, t):
    if t > 0:
        return model.P_ES_charge_effective[t] <= model.P_ES_charge_capacity
    return Constraint.Skip
model.linear_charge_effective_c2 = Constraint(model.T, rule=linear_charge_effective_c2)

def linear_charge_effective_c3(model, t):
    if t > 0:
        return model.P_ES_charge_effective[t] >= model.P_ES_charge_capacity - P_grid_max * (1 - model.batterycharge_binary[t])
    return Constraint.Skip
model.linear_charge_effective_c3 = Constraint(model.T, rule=linear_charge_effective_c3)

# Discharge power limit with binary
def discharging_power_upper_limit_rule(model, t):
    if t == 0:
        return model.P_ES_discharge[t] == 0
    return model.P_ES_discharge[t] <= (1 - model.batterycharge_binary[t]) * P_ES_discharge_max
model.discharging_power_upper_limit = Constraint(model.T, rule=discharging_power_upper_limit_rule)

# Initial/Final SOC over the FULL HORIZON (year)
def initial_SOC_rule(model):
    return model.E_ES[0] == (SOC_init / 100) * model.E_ES_max
model.initial_SOC = Constraint(rule=initial_SOC_rule)

def final_SOC_rule(model):
    return model.E_ES[num_periods - 1] == (SOC_end / 100) * model.E_ES_max
model.final_SOC = Constraint(rule=final_SOC_rule)

# SOC evolution
def SOC_evolution_rule(model, t):
    if t > 0:
        return model.E_ES[t] == model.E_ES[t - 1] + (
            charge_eff * model.P_ES_charge[t] - (1 / discharge_eff) * model.P_ES_discharge[t]
        ) * deltat
    return Constraint.Skip
model.SOC_evolution = Constraint(model.T, rule=SOC_evolution_rule)

# Grid peak bound
def grid_peak_constraints(model):
    return model.P_grid_peak <= P_grid_max
model.grid_peak_constraints = Constraint(rule=grid_peak_constraints)

# Split grid power into import/export (pos/neg)
def split_P_grid_rule(model, t):
    return model.P_grid[t] == model.P_grid_pos[t] - model.P_grid_neg[t]
model.split_P_grid = Constraint(model.T, rule=split_P_grid_rule)

def mutual_exclusivity_rule1(model, t):
    return model.P_grid_pos[t] <= model.grid_import[t] * P_grid_max
model.mutual_exclusivity_pos = Constraint(model.T, rule=mutual_exclusivity_rule1)

def mutual_exclusivity_rule2(model, t):
    return model.P_grid_neg[t] <= (1 - model.grid_import[t]) * P_grid_max
model.mutual_exclusivity_neg = Constraint(model.T, rule=mutual_exclusivity_rule2)

# Peak definition (two-sided)
def grid_peak_power_upper_limit_rule(model, t):
    return model.P_grid[t] <= model.P_grid_peak
model.grid_peak_power_upper_limit = Constraint(model.T, rule=grid_peak_power_upper_limit_rule)

def grid_peak_power_lower_limit_rule(model, t):
    return model.P_grid[t] >= -model.P_grid_peak
model.grid_peak_power_lower_limit = Constraint(model.T, rule=grid_peak_power_lower_limit_rule)

# -------------------------
# OBJECTIVES
# -------------------------
def objective_minimize_cost(model):
    return (
        sum(
            model.P_grid_pos[t] * model.cost_grid[t] - model.P_grid_neg[t] * model.feedin_hydro
            for t in model.T
        )
        + model.E_ES_max * cost_per_kwh_storage
    )

def objective_minimize_grid_peak(model):
    return model.P_grid_peak

def objective_max_selfconsumption(model):
    # minimizing total grid import
    return sum(model.P_grid_pos[t] for t in model.T)

if objective_selector == 1:
    model.obj = Objective(rule=objective_minimize_cost, sense=minimize)
elif objective_selector == 2:
    model.obj = Objective(rule=objective_minimize_grid_peak, sense=minimize)
elif objective_selector == 3:
    model.obj = Objective(rule=objective_max_selfconsumption, sense=minimize)
else:
    raise ValueError("Invalid objective selector value. Choose 1, 2, or 3.")

# -------------------------
# SOLVE
# -------------------------
solver = SolverFactory('highs')
solver.solve(model, tee=True)

print(f"Optimal P_ES_charge_capacity: {value(model.P_ES_charge_capacity):.6g}")
print(f"Optimal E_ES_max: {value(model.E_ES_max):.6g}")