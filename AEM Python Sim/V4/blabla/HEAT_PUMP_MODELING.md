# Heat Pump Model in V4

This note documents how the heat pump is represented in the V4 optimization model, how its bounds and modulation work, and what the solved results imply about sizing and feasibility.

## 1) Decision variables

The model uses three heat-pump variables:

- $E_{HP,t}$: electric input of the heat pump [kWh$_{el}$ per timestep]
- $Q_{HP,t}$: useful thermal output [kWh$_{th}$ per timestep]
- $Q_{HP}^{nom}$: nominal thermal capacity [kWh$_{th}$ per timestep]

A binary on/off variable $y_t$ also exists, but it is only activated when `enforce_modulation_binary = True`.

## 2) Operating equations

The core heat-pump relation is a monthly COP conversion:

$$
Q_{HP,t} = COP_{m(t)} \cdot E_{HP,t}
$$

where $COP_{m(t)}$ is the COP assigned to the month of timestep $t$.

In the current parameter set, the monthly COP profile is:

- Jan: 2.95
- Feb: 2.90
- Mar: 3.05
- Apr: 3.20
- May: 3.35
- Jun: 3.55
- Jul: 3.85
- Aug: 3.85
- Sep: 3.70
- Oct: 3.55
- Nov: 3.35
- Dec: 3.10

The thermal balance uses the heat pump together with the woodchip boiler and PTES:

$$
Q_{wood,t} + Q_{HP,t} + Q_{PTES,dis,t} = Q_{demand,t} + Q_{PTES,ch,t}
$$

So the heat pump is one supply source in a broader heat system, not a standalone heater.

## 3) Bounds and technical limits

### Thermal output cap

The parameter `hp_elec_max` is a legacy name. In the current implementation, it represents the maximum heat output per timestep:

$$
0 \le Q_{HP,t} \le Q_{HP,max}
$$

with

$$
Q_{HP,max} = 150\ \text{kWh}_{th}/\text{timestep}
$$

Since the timestep is 15 minutes ($\Delta t = 0.25$ h), this corresponds to:

$$
150 / 0.25 = 600\ \text{kW}_{th}
$$

### Equivalent electric-input bound

Because the heat pump still follows the COP law, the thermal cap implies an equivalent electric-input bound:

$$
E_{HP,t} \le \frac{Q_{HP,max}}{COP_{m(t)}}
$$

This is the bound actually enforced in the model.

### Nominal capacity ceiling

The output is also constrained by the optimized nominal capacity:

$$
Q_{HP,t} \le Q_{HP}^{nom}
$$

Therefore, the realized output at each timestep is bounded by:

$$
Q_{HP,t} \le \min\left(Q_{HP,max},\ Q_{HP}^{nom}\right)
$$

### Ramp limit

The model also enforces a continuous ramp limit on electric input:

$$
\left|E_{HP,t} - E_{HP,t-1}\right| \le R_{HP}
$$

with

$$
R_{HP} = 0.125\ \text{kWh}_{el}/\text{timestep}
$$

This is a very tight ramp, so the heat pump changes gradually from one 15-minute step to the next.

### Optional binary modulation

If exact on/off modulation is enabled, the model also applies:

$$
E_{HP,t} \le \frac{Q_{HP,max}}{COP_{m(t)}} \cdot y_t
$$

$$
E_{HP,t} \ge f_{min} \cdot \frac{Q_{HP,max}}{COP_{m(t)}} \cdot y_t
$$

where

$$
f_{min} = 0.2
$$

This means that when the unit is on, it must run at least at 20% of the COP-adjusted electric-input ceiling.

In the current repository, `enforce_modulation_binary = False`, so the heat pump is modeled as a continuously modulating unit with no minimum-load constraint.

## 4) What the current implementation means operationally

Because the binary modulation is disabled, the heat pump behaves like a flexible continuous source:

- it can be fully off,
- or it can operate anywhere between zero and its technical maximum heat output,
- but it still respects the monthly COP, the derived electric-input bound, the ramp limit, and the nominal thermal cap.

This is a good approximation for long-horizon planning runs, because it avoids an expensive MILP formulation while still capturing the main operational physics.

## 5) How the heat pump is sized in the optimization

The nominal capacity $Q_{HP}^{nom}$ is a decision variable with no independent purchase curve beyond the annual fixed cost term. The optimizer therefore sets it just large enough to accommodate the maximum realized heat output, but no larger.

That means the chosen size is driven by:

- the COP profile,
- the thermal output cap,
- the ramp limit,
- the heat balance with PTES and the woodchip boiler,
- and the annualized fixed cost of capacity.

## 6) Results-based interpretation from the solved kWh table

From the solved `kWh Results.csv`:

- nominal heat-pump capacity: **150.0 kWh$_{th}$ per timestep**
- maximum realized heat output: **150.0 kWh$_{th}$ per timestep**
- total heat-pump output over the solved horizon: **5.19 GWh$_{th}$**
- total heat demand over the solved horizon: **15.76 GWh$_{th}$**
- heat-pump share of heat demand: **32.9%**
- peak heat demand: **1310.5 kWh$_{th}$ per timestep**

Two important implications follow:

1. **It does not cover peak demand on its own.**
   The heat pump nominal output is only about 11% of the peak heat demand:

   $$
   150.0 / 1310.5 \approx 0.11
   $$

   So it is not oversized relative to the peak thermal requirement.

2. **It is heavily utilized.**
   The heat pump runs very close to its ceiling for most timesteps, which means the optimizer uses it as a constrained base-load heat source rather than an underused reserve asset.

## 7) Cost interpretation

From the cost-optimal solution:

- heat-pump annual fixed cost: **10,180.431 rappen** = **CHF 101.80**
- PTES annual fixed cost: **755.276 rappen** = **CHF 7.55**
- total cost objective burden: **-48,690,706.42 rappen** = **CHF 486,907.06** net annual profit

The heat-pump fixed cost is still small relative to the total annual objective value, but it is no longer paired with an oversized thermal cap. The optimizer therefore uses the heat pump aggressively, but only up to the 150 kWh$_{th}$/timestep ceiling.

That does **not** mean the heat pump is physically unrealistic in the model. It means the model economics make the capacity almost free compared with the operational savings it creates.

## 8) Feasibility and sizing conclusion

### Technical conclusion
The heat pump is technically feasible in the current model. It satisfies the COP law, the thermal cap, the ramp limit, and the thermal balance.

### Sizing conclusion
It is **not oversized relative to peak demand**, because it cannot meet the system peak by itself. In fact, it is now clearly **undersized for peak coverage** and instead functions as a controlled base-load source.

### Economic conclusion
Under the current cost assumptions, the heat pump remains economically attractive and still operates nearly continuously, but the new thermal cap makes its role much more modest. If the goal is to reflect realistic deployment economics, the heat-pump capex/fixed-cost assumptions should still be revisited, but the sizing signal is now far less extreme.

### Overall conclusion
The current solution is best interpreted as a **small-to-midsize, heavily utilized base-load heat pump supported by PTES and woodchip boiler peak coverage**, not as an oversized machine. It is feasible in the model, and the thermal-cap interpretation makes the sizing result much more credible.

## 9) Practical note

The emissions-optimal solution in the current results eliminates the heat pump entirely and relies on other thermal sources instead. That shows the heat pump is not structurally required for feasibility; it is chosen mainly because the cost objective makes it attractive.
