

#1. Create load profile: sales- production *positive = demand, negative = surplus
"""
Module for grid load profile analysis and cost/revenue calculation.

This module creates and analyzes load profiles based on sales and production data,
then calculates associated costs and revenues based on spot prices.

Process:
    1. Create load profile: sales production where positive values represent demand
       and negative values represent surplus (dfload = sales*G1 - hydropower_production*C1)
    2. Add 'Load Profile' column to dataframe with calculated load values
    3. Calculate demand costs: for positive dfload values, multiply by spot price + constant C2
    4. Calculate surplus revenue: for negative dfload values, multiply by spot price - constant C3

Constants:
    G1: Sales marginal profit scaling factor
    C1: Hydropower production marginal cost factor
    C2: Demand cost adjustment constant
    C3: Surplus revenue adjustment constant

Returns:
    pandas.DataFrame: Enhanced dataframe with Load Profile column and associated
                     cost/revenue calculations
"""
#   dfgrid = [sales column]*G1 - [total production hydropower column]*C1
#then make it so that: for every row (time step), if dfload is positive, then it is demand, if negative, then it is surplus
#2. Create a new column in the dataframe called 'Load Profile' and populate it with the values from dfload
#3. For dfload =demand (negative) multiply by the spot price column plus a constant C2 (to get the cost of demand)
#4. For dfload = surplus (positive) multiply by the spot price column minus a constant C3 (to get the revenue from export / surplus)

import pandas as pd

# Constants [Rp/kWh]
C0 = 1.0  # Sales marginal profit scaling factor
C1 = -6.0  # Hydropower production marginal cost factor
C2 = -1.08  # Demand cost tariff -(spot price+tariff broker) adjustment constant
    #Two tariffs available: flat rate 1.08 Rp/kWh OR power tariff 11.43CHF/kWp pro monat)
C3 = 1  # Surplus revenue tariff (+spot price - (grid cost+spot price broker tariff)) adjustment constant

# Load the CSV file
df = pd.read_csv('/workspaces/BAT/AEM Python Sim/Data Sorting/DATA/AEM TOTAL 2024_corrected.csv')

# 1. Calculate load profile & its cost: sales*G1 - production*C1
df['Load Profile'] = df['Sales'] - df['Total Production Hydro']
df['Cost Profile'] = df['Sales'] * C0 + df['Total Production Hydro'] * C1

# 3 & 4. Calculate demand costs and surplus revenue
df['Cost/Revenue'] = df['Cost Profile'] - df.apply(
    lambda row: row['Load Profile'] * (row['Spot price [Rp/kWh]'] + C2)
    if row['Load Profile'] > 0
    else row['Load Profile'] * (row['Spot price [Rp/kWh]'] + C3),
    axis=1)


# Display results
print(df[['DateTime', 'Sales', 'Total Production Hydro', 'Load Profile', 'Spot price [Rp/kWh]', 'Cost/Revenue']].head(10))


import plotly.graph_objects as go
from plotly.subplots import make_subplots

# Create subplots with secondary y-axis (for different scales)
fig = make_subplots(
    rows=1, cols=1,
    specs=[[{"secondary_y": True}]]
)

# Add traces
fig.add_trace(
    go.Scatter(
        x=df['DateTime'],
        y=df['Load Profile'],
        name='Load profile [kWh]',
        mode='lines',
        line=dict(color='#1f77b4', width=1),
        hovertemplate='<b>Load</b><br>%{x}<br>%{y:.2f} kW<extra></extra>'
    ),
    secondary_y=False,
)

fig.add_trace(
    go.Scatter(
        x=df['DateTime'],
        y=df['Cost/Revenue'],
        name='Cost/Revenue [Rp]',
        mode='lines',
        line=dict(color='#ff7f0e', width=1),
        hovertemplate='<b>Cost/Revenue</b><br>%{x}<br>%{y:.2f} Rp<extra></extra>'
    ),
    secondary_y=True,
)

fig.write_html('/workspaces/BAT/AEM Python Sim/V0/Plots/load_profile_cost_revenue.html')
