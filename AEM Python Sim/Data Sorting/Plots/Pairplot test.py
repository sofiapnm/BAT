"""
Seaborn pairplot of Demand, Surplus and Spot price.
"""

import os
import pandas as pd
import seaborn as sns

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
pairplot_fig = sns.pairplot(pairplot_data,
                            diag_kind='hist',
                            plot_kws={'alpha': 0.5, 's': 10})
pairplot_fig.fig.suptitle("Pairplot: Demand, Surplus, and Spot Price", y=1.001)

os.makedirs(os.path.dirname(pairplot_output), exist_ok=True)
pairplot_fig.savefig(pairplot_output, dpi=100)
print(f"✓ Pairplot saved to: {pairplot_output}")