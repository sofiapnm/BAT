#using the sales profile (load), create an optimization model to determine the optimal energy dispatch strategy for meeting demand
#optimization: consider the minimum cost profile, which includes the cost of importing energy from the grid and the revenue from exporting excess energy to the grid, as well as the cost of using the battery (if applicable)
#two sources of energy: hydropower production and grid import
#2. sell excess energy to the grid when spot prices are high and buy from the grid?
#power can be imported or exported depending on the sign of the load profile (positive = demand, negative = surplus)
#when positive, demand can be met by either buying from spot market or discharging the battery
#when negative, surplus can be exported to the grid or used to charge the battery
 
 
from pyomo.environ import *
import pandas as pd

# Create model
model = ConcreteModel()

# Load and prepare data
df = pd.read_csv('/workspaces/BAT/AEM Python Sim/Data Sorting/DATA/AEM TOTAL 2024_corrected.csv')
df['DateTime'] = pd.to_datetime(df['DateTime'])

# Extract relevant columns
time_periods = len(df)
load=df['Sales'].values  # kWh
demand = df['Demand'].values  # kWh
production = df['Production Total'].values  # kWh
spot_price = df['Spot price [Rp/kWh]'].values # Rp/kWh
surplus = df['Surplus'].values  # kWh

# Battery parameters #TO BE DEFINED
battery_capacity = 1000  # kWh (to be defined)
battery_efficiency = 0.95
battery_max_charge_rate = 500  # kW
battery_max_discharge_rate = 500  # kW
battery_cost_per_cycle = 0.01  # CHF/kWh

# Time periods
T = range(time_periods)

# Decision variables
model.grid_import = Var(T, within=NonNegativeReals)  # kWh imported from grid
model.grid_export = Var(T, within=NonNegativeReals)  # kWh exported to grid
model.battery_charge = Var(T, within=NonNegativeReals)  # kWh charged
model.battery_discharge = Var(T, within=NonNegativeReals)  # kWh discharged
model.battery_soc = Var(T, bounds=(0, battery_capacity))  # State of charge

# Objective: Minimize total cost
def objective_rule(model):
    return sum(
        model.grid_import[t] * (spot_price[t] + 1.08)
        - model.grid_export[t] * spot_price[t]
        + (model.battery_charge[t] + model.battery_discharge[t])
          * battery_cost_per_cycle
        for t in T
    )

model.objective = Objective(rule=objective_rule, sense=minimize)

# Constraints
# Energy balance at each time step
def energy_balance_rule(model, t):
    return (production[t] + model.grid_import[t] + model.battery_discharge[t] * battery_efficiency == 
            load[t] + model.grid_export[t] + model.battery_charge[t])

model.energy_balance = Constraint(T, rule=energy_balance_rule)

# Battery state of charge dynamics
def battery_soc_rule(model, t):
    if t == 0:
        return model.battery_soc[t] == battery_capacity / 2 + model.battery_charge[t] - model.battery_discharge[t]
    else:
        return model.battery_soc[t] == model.battery_soc[t-1] + model.battery_charge[t] - model.battery_discharge[t]

model.battery_soc_dynamics = Constraint(T, rule=battery_soc_rule)

# Battery charge/discharge rate limits
def charge_rate_limit(model, t):
    return model.battery_charge[t] <= battery_max_charge_rate
model.charge_limit = Constraint(T, rule=charge_rate_limit)

def discharge_rate_limit(model, t):
    return model.battery_discharge[t] <= battery_max_discharge_rate
model.discharge_limit = Constraint(T, rule=discharge_rate_limit)

# Solve
solver = SolverFactory('cbc')
if not solver.available():
    raise RuntimeError("cbc not found – install coinor‑cbc or use another solver")
results = solver.solve(model, tee=True)   # prints CBC/GLPK output to the console
print("return code:", results.solver.return_code)

# Load solution into model
if results.solver.termination_condition == TerminationCondition.optimal:
    model.solutions.load_from(results)
else:
    print("Solver did not find an optimal solution!")
    print("Termination Condition:", results.solver.termination_condition)
    exit()

# Print results
print("Optimization Status:", results.solver.status)
print("Termination Condition:", results.solver.termination_condition)
print("\n" + "="*50)
print("OPTIMIZATION RESULTS")
print("="*50)
print(f"\nMinimum Total Cost: {model.objective():.2f} CHF")

print("\n--- Summary by Time Period ---")
print(f"{'Time':<6} {'Import':<10} {'Export':<10} {'Charge':<10} {'Discharge':<12} {'SOC':<10}")
print("-" * 60)

for t in T:
    print(f"{t:<6} {model.grid_import[t]():<10.2f} {model.grid_export[t]():<10.2f} "
          f"{model.battery_charge[t]():<10.2f} {model.battery_discharge[t]():<12.2f} {model.battery_soc[t]():<10.2f}")

print("\n--- Cost Breakdown ---")
import_cost = sum(model.grid_import[t]() * (spot_price[t] + 1.08) for t in T)
export_revenue = sum(model.grid_export[t]() * spot_price[t] for t in T)
battery_op_cost = sum((model.battery_charge[t]() + model.battery_discharge[t]()) * battery_cost_per_cycle for t in T)

print(f"Grid Import Cost: {import_cost:.2f} CHF")
print(f"Grid Export Revenue: {export_revenue:.2f} CHF")
print(f"Battery Operating Cost: {battery_op_cost:.2f} CHF")
print(f"Net Cost: {import_cost - export_revenue + battery_op_cost:.2f} CHF")
