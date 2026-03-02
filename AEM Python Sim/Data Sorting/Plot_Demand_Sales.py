"""
Plot Demand, Sales, and Spot Price over DateTime
Interactive Plotly visualization
"""

import os
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# Configuration
data_path = r"/workspaces/BAT/AEM Python Sim/Data Sorting/DATA/AEM TOTAL 2024.csv"
output_html = r"/workspaces/BAT/AEM Python Sim/Data Sorting/Plots/SpotPrice_Plot.html"

# Load data with semicolon delimiter (sep=';') and correct date format (dayfirst=True for DD.MM.YYYY)
df = pd.read_csv(data_path, sep=';', parse_dates=['DateTime'], dayfirst=True)
print(f"Loaded {len(df)} rows")
print(f"Columns: {df.columns.tolist()}\n")

# Verify required columns exist
required_cols = ['DateTime', 'Demand', 'Surplus','Spot price [Rp/kWh]']
missing = [c for c in required_cols if c not in df.columns]
if missing:
    raise KeyError(f"Missing columns: {missing}. Available: {df.columns.tolist()}")

# Create subplots with secondary y-axis (for different scales)
fig = make_subplots(
    rows=1, cols=1,
    specs=[[{"secondary_y": True}]],
)

# Add traces
fig.add_trace(
    go.Scatter(
        x=df['DateTime'],
        y=df['Demand'],
        name='Demand [kW]',
        mode='lines',
        line=dict(color='#1f77b4', width=1),
        hovertemplate='<b>Demand</b><br>%{x}<br>%{y:.2f} kW<extra></extra>'
    ),
    secondary_y=False,
)

fig.add_trace(
    go.Scatter(
        x=df['DateTime'],
        y=df['Surplus'],
        name='Surplus [kW]',
        mode='lines',
        line=dict(color='#ff7f0e', width=1),
        hovertemplate='<b>Surplus</b><br>%{x}<br>%{y:.2f} kW<extra></extra>'
    ),
    secondary_y=False,
)

fig.add_trace(
    go.Scatter(
        x=df['DateTime'],
        y=df['Spot price [Rp/kWh]'],
        name='Spot Price [Rp/kWh]',
        mode='lines',
        line=dict(color='#12946a', width=1),
        hovertemplate='<b>Spot Price</b><br>%{x}<br>%{y:.2f} Rp/kWh<extra></extra>'
    ),
    secondary_y=True,
)

# Update layout
fig.update_layout(
    title_text="Demand, Surplus, and Spot Price over Time (2024)",
    hovermode='x unified',
    height=600,
    template='plotly_white',
    xaxis_title='DateTime',
    legend=dict(x=0.01, y=0.99),
)

fig.update_yaxes(title_text="Demand / Surplus [kW]", secondary_y=False)
fig.update_yaxes(title_text="Spot Price [Rp/kWh]", secondary_y=True)

# Save
os.makedirs(os.path.dirname(output_html), exist_ok=True)
fig.write_html(output_html)
print(f"✓ Plot saved to: {output_html}")

# Show summary stats
print("\n--- Summary Statistics ---")
print(f"Demand:     min={df['Demand'].min():.2f}, max={df['Demand'].max():.2f}, mean={df['Demand'].mean():.2f}")
print(f"Surplus:    min={df['Surplus'].min():.2f}, max={df['Surplus'].max():.2f}, mean={df['Surplus'].mean():.2f}")
print(f"Spot Price: min={df['Spot price [Rp/kWh]'].min():.2f}, max={df['Spot price [Rp/kWh]'].max():.2f}, mean={df['Spot price [Rp/kWh]'].mean():.2f}")
