import pandas as pd
from datetime import date

csv_path = '/workspaces/BAT/AEM Python Sim/Data Sorting/DATA/MI_Production_Data_2023_2024_aligned.csv'
out_path = '/workspaces/BAT/AEM Python Sim/Data Sorting/DATA/MI_Production_2024_zero_days.csv'

df = pd.read_csv(csv_path, parse_dates=['DateTime'])
col = '2024 Production MI'

if col not in df.columns:
    raise KeyError(f"Column {col} not found in {csv_path}. Columns: {df.columns.tolist()}")
 
# Create date column
df['date_only'] = df['DateTime'].dt.date

zero_days = []
for d, g in df.groupby('date_only'):
    non_na = g[col].dropna()
    if len(non_na) > 0 and (non_na == 0.0).all():
        zero_days.append((d, len(g), len(non_na)))
 
# Save and print
rez = pd.DataFrame(zero_days, columns=['date','rows_total','non_na_count'])
rez.to_csv(out_path, index=False)

print(f"Found {len(rez)} days where all non-null 2024 readings are 0.0")
print(rez.to_string(index=False))
print('\nSaved list to', out_path)