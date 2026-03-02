# AEM Energy generation TOTAL [MI, MII & PV ]
# - MI: integrate 2023 summer generation profile into 2024 NaNs
# - id NaN cells

#NOTE: Demand and Surplus profiles are calculated from the sales and production, not measured

#1ST STEP: OPEN TERMINAL AND INPUT : pip install pandas openpyxl
#create virtual environment if necessary


import pandas as pd

def load_excel_file(file_path):
    try:
        # Explicitly load first sheet
        df = pd.read_excel(file_path, sheet_name=0)
        print(df.head())

        return df

    except Exception as e:
        print(f"Error loading file: {e}")
        return None


def combine_datetime_columns(df, date_col='Date', time_col='Time', datetime_col='DateTime'):
    """
    Combine separate date and time columns into a single datetime column.
    
    Parameters:
    -----------
    df : pd.DataFrame
        DataFrame containing date and time columns
    date_col : str
        Name of the date column (default: 'Date')
    time_col : str
        Name of the time column (default: 'Time')
    datetime_col : str
        Name for the new datetime column (default: 'DateTime')
    
    Returns:
    --------
    pd.DataFrame
        DataFrame with the new datetime column added
    """
    try:
        # Convert date column to datetime if it's not already
        df[date_col] = pd.to_datetime(df[date_col])
        
        # Convert time column to time objects
        df[time_col] = pd.to_datetime(df[time_col], format='%H:%M:%S').dt.time
        
        # Combine date and time columns
        df[datetime_col] = pd.to_datetime(
            df[date_col].astype(str) + ' ' + df[time_col].astype(str)
        )
        
        print(f"✓ Successfully created '{datetime_col}' column")
        print(f"  DateTime range: {df[datetime_col].min()} to {df[datetime_col].max()}")
        
        return df
    
    except Exception as e:
        print(f"Error combining date and time columns: {e}")
        return df


if __name__ == "__main__":
    file_path = r"/workspaces/BAT/AEM Python Sim/Data Sorting/DATA/00 Energy Production+Sale_2023-2024.xlsx"
    usecols = "A:J"
    df = pd.read_excel(file_path, sheet_name=0, usecols=usecols)
    df = load_excel_file(file_path)

    if df is not None:
        # Combine date and time columns into a datetime column
        df = combine_datetime_columns(df, date_col='Date', time_col='Time', datetime_col='DateTime')
        
        # Create new dataframe: drop Date/Time columns and unwanted columns, move DateTime to beginning
        df_energygen = df.drop(columns=['Date', 'Time']).copy()
        
        # Drop columns 10-15 (M1, M2, Summiert total, Füllstand M1, Füllstand M2, Nicht nutzbare)
        cols_to_drop = ['M1 [kWh]', 'M2 [kWh]', 'Summiert total[kWh]', 'Füllstand M1', 'Füllstand M2', 'Nicht nutzbare Energieüberschuss']
        df_energygen = df_energygen.drop(columns=cols_to_drop, errors='ignore')
        
        # Reorder columns: DateTime first, then all others
        cols = ['DateTime'] + [col for col in df_energygen.columns if col != 'DateTime']
        df_energygen = df_energygen[cols]
        
        print("\n✓ df_energygen created successfully")
        print(f"Shape: {df_energygen.shape}")
        print(f"\nColumns: {df_energygen.columns.tolist()}")
        print("\nFirst 5 rows:")
        print(df_energygen.head())
        
    # Export to CSV
    csv_path = r"/workspaces/BAT/AEM Python Sim/Data Sorting/DATA/00 CLEAN Energy Production+Sale_2023-2024.csv"
    df_energygen.to_csv(csv_path, index=False)
    print(f"\n✓ CSV exported to: {csv_path}")

