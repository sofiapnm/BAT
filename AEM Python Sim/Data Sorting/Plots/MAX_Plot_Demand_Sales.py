"""
Plot Demand, Sales, and Spot Price over DateTime
Interactive Plotly visualization
"""

import os
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# Configuration
data_path = r"/workspaces/BAT/AEM Python Sim/Data Sorting/DATA/maxprod2024.csv"
output_html = r"/workspaces/BAT/AEM Python Sim/Data Sorting/Plots/MAXPROD_SpotPrice_Plot.html"
corrected_path = r"/workspaces/BAT/AEM Python Sim/Data Sorting/DATA/AEM TOTAL 2024_corrected.csv"

# Load data with comma delimiter (sep=',') and correct date format (dayfirst=True for DD.MM.YYYY)
df = pd.read_csv(data_path, sep=',', parse_dates=['DateTime'], dayfirst=True)
# Load corrected AEM file to extract its Surplus series for comparison
try:
    aem_df = pd.read_csv(corrected_path, sep=',', parse_dates=['DateTime'], dayfirst=True)
except Exception:
    aem_df = pd.DataFrame()
print(f"Loaded {len(df)} rows")
print(f"Columns: {df.columns.tolist()}\n")

# Verify required columns exist
required_cols = ['DateTime', 'Demand', 'Surplus', 'District heating sales', 'Spot price [Rp/kWh]']
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

# Prepare AEM Surplus (from corrected CSV)
if not aem_df.empty and 'Surplus' in aem_df.columns:
    aem_surplus = pd.to_numeric(aem_df['Surplus'], errors='coerce').fillna(0)
else:
    aem_surplus = pd.Series(0, index=df.index)

maxprod_surplus = pd.to_numeric(df['Surplus'], errors='coerce').fillna(0)
potential_surplus = (-maxprod_surplus).where(~maxprod_surplus.reset_index(drop=True).eq(aem_surplus.reset_index(drop=True)), other=float('nan'))



# Surplus trace from the MAXprod data
fig.add_trace(
    go.Scatter(
        x=df['DateTime'],
        y=potential_surplus,
        name='Surplus (Potential)',
        mode='lines',
        line=dict(color='#9467bd', width=1),
        hovertemplate='<b>Surplus (MAXprod)</b><br>%{x}<br>%{y:.2f} kW<extra></extra>'
    ),
    secondary_y=False,
)

# Surplus trace from the corrected AEM file
fig.add_trace(
    go.Scatter(
        x=df['DateTime'],
        y=-aem_surplus,
        name='Surplus (AEM)',
        mode='lines',
        line=dict(color='#ff7f0e', width=1),
        hovertemplate='<b>Surplus (AEM)</b><br>%{x}<br>%{y:.2f} kW<extra></extra>'
    ),
    secondary_y=False,
)

fig.add_trace(
    go.Scatter(
        x=df['DateTime'],
        y=df['District heating sales'],
        name='District heating sales',
        mode='lines',
        line=dict(color='#d62728', width=1),
        hovertemplate='<b>District Heating Sales</b><br>%{x}<br>%{y:.2f}<extra></extra>'
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
    title_text="Demand, Surplus, District Heating Sales, and Spot Price over Time (2024)",
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
print(f"District Heating Sales: min={df['District heating sales'].min():.2f}, max={df['District heating sales'].max():.2f}, mean={df['District heating sales'].mean():.2f}")
print(f"Spot Price: min={df['Spot price [Rp/kWh]'].min():.2f}, max={df['Spot price [Rp/kWh]'].max():.2f}, mean={df['Spot price [Rp/kWh]'].mean():.2f}")
