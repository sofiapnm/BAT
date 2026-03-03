import pandas as pd
from pathlib import Path


# --- Config ---
data_path = r"/workspaces/BAT/AEM Python Sim/Data Sorting/DATA/00 CLEAN Energy Production+Sale_2023-2024.csv"
output_path = r"/workspaces/BAT/AEM Python Sim/Data Sorting/DATA/MI_Production_Data_2023_2024_aligned.csv"
base_year = 2023  # year to which timestamps will be normalized for alignment


def find_column(df, candidates):
	for c in candidates:
		if c in df.columns:
			return c
	return None


def normalize_to_base_year(ts, base_year=2023):
	try:
		return ts.replace(year=base_year)
	except Exception:
		# handle Feb 29 (leap day) by mapping to Feb 28 in the base year
		if ts.month == 2 and ts.day == 29:
			return ts.replace(year=base_year, day=28)
		return pd.NaT


def main():
	df = pd.read_csv(data_path)

	print("Available columns:")
	print(df.columns.tolist())

	# locate columns (case-sensitive fallback list)
	datetime_col = find_column(df, ["DateTime", "datetime", "date_time", "date"])
	production_col = find_column(df, ["Production MI", "production MI", "production mi", "production_mi", "M1 [kWh]", "m1 [kwh]"])

	if datetime_col is None or production_col is None:
		raise KeyError(f"Required columns not found. Found: {df.columns.tolist()}")

	# parse DateTime
	df[datetime_col] = pd.to_datetime(df[datetime_col])

	# normalize timestamps to base year for alignment
	df["norm_dt"] = df[datetime_col].apply(lambda t: normalize_to_base_year(t, base_year))

	# split by original year
	df["orig_year"] = df[datetime_col].dt.year

	s2023 = (
		df.loc[df["orig_year"] == 2023, ["norm_dt", production_col]]
		.dropna()
		.groupby("norm_dt")[production_col]
		.mean()
	)

	s2024 = (
		df.loc[df["orig_year"] == 2024, ["norm_dt", production_col]]
		.dropna()
		.groupby("norm_dt")[production_col]
		.mean()
	)

	# union index and build aligned DataFrame
	index = pd.DatetimeIndex(sorted(set(s2023.index).union(set(s2024.index))))
	result = pd.DataFrame(index=index)
	result.index.name = "DateTime"
	result[f"{base_year} Production MI"] = s2023.reindex(index)
	result[f"{base_year+1} Production MI"] = s2024.reindex(index)

	# reset index to make DateTime a column (if preferred)
	result = result.reset_index()

	print("\nAligned result sample:")
	print(result.head(10))

	# save
	result.to_csv(output_path, index=False)
	print(f"\nSaved aligned CSV to: {output_path}")


if __name__ == "__main__":
	main()