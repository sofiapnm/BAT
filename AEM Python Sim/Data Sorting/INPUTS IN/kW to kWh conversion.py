from pathlib import Path

import pandas as pd


SOURCE_PATH = Path("/workspaces/BAT/AEM Python Sim/Data Sorting/DATA/maxprod2024.csv")
TARGET_PATH = Path("/workspaces/BAT/AEM Python Sim/Data Sorting/DATA/maxprod2024_kWh.csv")

COLUMNS_TO_DIVIDE = [
	"Sales",
	"PV Grid Feed-In",
	"Total Production Hydro",
	"Production Total",
	"Demand",
	"Surplus",
	"District heating sales",
]


def main():
	df = pd.read_csv(SOURCE_PATH)

	missing_columns = [column for column in COLUMNS_TO_DIVIDE if column not in df.columns]
	if missing_columns:
		raise ValueError(f"Missing columns in source CSV: {missing_columns}")

	df[COLUMNS_TO_DIVIDE] = df[COLUMNS_TO_DIVIDE] / 4.0
	df.to_csv(TARGET_PATH, index=False)

	print(f"Wrote {TARGET_PATH}")


if __name__ == "__main__":
	main()
