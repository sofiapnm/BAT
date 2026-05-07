import pandas as pd

# Read the original CSV
df = pd.read_csv('/workspaces/BAT/AEM Python Sim/Data Sorting/DATA/AEM TOTAL 2024_corrected.csv')

# Delete columns "Production MI Amended" and "Production MII"
df = df.drop(columns=['Production MI Amended', 'Production MII'], errors='ignore')

# Define months April to July (months 4-7)
maxprod_months = [4, 5, 6, 7]

# Extract month from date column (assuming there's a date column)
# Adjust the date column name if needed
if 'Date' in df.columns:
    df['Month'] = pd.to_datetime(df['Date']).dt.month
elif 'date' in df.columns:
    df['Month'] = pd.to_datetime(df['date']).dt.month
else:
    # Try to find a date column automatically
    date_cols = [col for col in df.columns if 'date' in col.lower()]
    if date_cols:
        df['Month'] = pd.to_datetime(df[date_cols[0]]).dt.month
    else:
        print("Warning: No date column found")

# Replace "Total Production Hydro" with 4000 for April to July
if 'Total Production Hydro' in df.columns:
    mask = df['Month'].isin(maxprod_months)
    df.loc[mask, 'Total Production Hydro'] = 4000

# Recalculate "Production Total" as PV Grid Feed-In + Total Production Hydro
if 'PV Grid Feed-In' in df.columns and 'Total Production Hydro' in df.columns:
    df['Production Total'] = df['PV Grid Feed-In'] + df['Total Production Hydro']

# Compute Demand and Surplus from Production Total and Sales
# Demand: when Load (Sales) > Total Production
# Surplus: when Total Production > Load (Sales)
df['Demand'] = (df['Sales'] - df['Production Total']).clip(lower=0)
df['Surplus'] = (df['Production Total'] - df['Sales']).clip(lower=0)

# Drop the helper Month column
df = df.drop(columns=['Month'], errors='ignore')

# Move 'Total Production Hydro' to be the 4th column (after the 3rd column)
if 'Total Production Hydro' in df.columns:
    cols = list(df.columns)
    # remove the column and re-insert at position index 3 (0-based)
    cols.remove('Total Production Hydro')
    insert_pos = 3 if len(cols) >= 3 else len(cols)
    cols.insert(insert_pos, 'Total Production Hydro')
    df = df[cols]

# Save to new CSV
output_path = '/workspaces/BAT/AEM Python Sim/Data Sorting/DATA/maxprod2024.csv'
df.to_csv(output_path, index=False)

print(f"New CSV created successfully at: {output_path}")
