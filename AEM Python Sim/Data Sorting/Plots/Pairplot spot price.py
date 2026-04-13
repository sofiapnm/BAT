"""
Seaborn pairplot of Demand, Surplus and Spot price.
"""
import matplotlib.pyplot as plt
import os
import pandas as pd
import seaborn as sns
sns.set_theme(style="whitegrid")

# configuration
data_path = r"/workspaces/BAT/AEM Python Sim/Data Sorting/DATA/AEM TOTAL 2024.csv"
pairplot_output = r"/workspaces/BAT/AEM Python Sim/Data Sorting/Plots/Pairplot.png"

# load the data
df = pd.read_csv(data_path, sep=';', parse_dates=['DateTime'], dayfirst=True)

# ensure the columns needed for the pairplot are present
required_cols = ['Demand', 'Surplus', 'Spot price [Rp/kWh]']
missing = [c for c in required_cols if c not in df.columns]
if missing:
    raise KeyError(f"Missing columns: {missing}")

# create & save seaborn pairplot
pairplot_data = df[required_cols].copy()
pairplot_data = pairplot_data.rename(columns={
    'Demand': 'Deficit [kWh]',
    'Surplus': 'Surplus [kWh]',
})
spot_col = 'Spot price [Rp/kWh]'

# Ensure numeric comparisons work even if source columns are read as strings.
for col in pairplot_data.columns:
    pairplot_data[col] = pd.to_numeric(pairplot_data[col], errors='coerce')

# Compute separate spot-price averages for rows with demand and with surplus.
deficit_mask = pairplot_data['Deficit [kWh]'] > 0
surplus_mask = pairplot_data['Surplus [kWh]'] < 0
avg_spot_price_demand = pairplot_data.loc[deficit_mask, spot_col].mean()
avg_spot_price_surplus = pairplot_data.loc[surplus_mask, spot_col].mean()
avg_by_comparison = {
    'Deficit [kWh]': avg_spot_price_demand,
    'Surplus [kWh]': avg_spot_price_surplus,
}
color_by_comparison = {
    'Deficit [kWh]': 'red',
    'Surplus [kWh]': 'purple',
}

pairplot_fig = sns.pairplot(pairplot_data,
                            diag_kind='scatter',
                            plot_kws={'alpha': 0.5, 's': 10})

# Add a red average spot-price reference line to Spot-vs-Demand and Spot-vs-Surplus panels.
for i, y_var in enumerate(pairplot_fig.y_vars):
    for j, x_var in enumerate(pairplot_fig.x_vars):
        ax = pairplot_fig.axes[i, j]
        if ax is None:
            continue
        if y_var == spot_col and x_var in avg_by_comparison:
            avg_val = avg_by_comparison[x_var]
            if pd.notna(avg_val):
                ax.axhline(avg_val, color=color_by_comparison[x_var], linestyle='-', linewidth=1)
        if x_var == spot_col and y_var in avg_by_comparison:
            avg_val = avg_by_comparison[y_var]
            if pd.notna(avg_val):
                ax.axvline(avg_val, color=color_by_comparison[y_var], linestyle='-', linewidth=1)

pairplot_fig.fig.suptitle("Pairplot: Demand, Surplus, and Spot Price", y=1.001)

os.makedirs(os.path.dirname(pairplot_output), exist_ok=True)
pairplot_fig.savefig(pairplot_output, dpi=100)

if pd.notna(avg_spot_price_demand):
    print(f"Average spot price when Deficit [kWh] > 0: {avg_spot_price_demand:.4f} Rp/kWh")
else:
    print("Average spot price when Deficit [kWh] > 0: N/A (no rows matched)")

if pd.notna(avg_spot_price_surplus):
    print(f"Average spot price when Surplus < 0: {avg_spot_price_surplus:.4f} Rp/kWh")
else:
    print("Average spot price when Surplus < 0: N/A (no rows matched)")

print(f"✓ Pairplot saved to: {pairplot_output}")