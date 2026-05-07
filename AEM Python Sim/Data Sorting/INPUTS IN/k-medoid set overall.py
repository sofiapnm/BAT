from pathlib import Path

import numpy as np
import pandas as pd


CSV_PATH = Path("/workspaces/BAT/AEM Python Sim/Data Sorting/DATA/AEM TOTAL 2024_corrected.csv")
FEATURE_COLUMNS = ["Demand", "Surplus", "District heating sales"]
K = 5


def load_data(path: Path) -> pd.DataFrame:
	df = pd.read_csv(path, parse_dates=["DateTime"])
	df["Date"] = df["DateTime"].dt.date
	return df


def create_daily_feature_vectors(df: pd.DataFrame) -> pd.DataFrame:
	return df.groupby("Date")[FEATURE_COLUMNS].mean()


def pairwise_distances(data: np.ndarray, medoids: np.ndarray) -> np.ndarray:
	return np.linalg.norm(data[:, None, :] - medoids[None, :, :], axis=2)


def total_cost(data: np.ndarray, medoid_indices: list[int]) -> float:
	medoids = data[medoid_indices]
	distances = pairwise_distances(data, medoids)
	return float(np.min(distances, axis=1).sum())


def pam_k_medoids(data: np.ndarray, k: int, max_iter: int = 100, random_state: int = 42) -> list[int]:
	rng = np.random.default_rng(random_state)
	medoid_indices = list(rng.choice(len(data), size=k, replace=False))

	for _ in range(max_iter):
		current_cost = total_cost(data, medoid_indices)
		improved = False

		for m_pos, _ in enumerate(medoid_indices):
			for candidate in range(len(data)):
				if candidate in medoid_indices:
					continue
				trial = medoid_indices.copy()
				trial[m_pos] = candidate
				trial_cost = total_cost(data, trial)
				if trial_cost < current_cost:
					medoid_indices = trial
					current_cost = trial_cost
					improved = True

		if not improved:
			break

	return medoid_indices


def main() -> None:
	df = load_data(CSV_PATH)
	daily_vectors = create_daily_feature_vectors(df)

	print("Daily feature vectors (mean of Demand, Surplus, District heating sales):")
	print(daily_vectors.to_string())

	data = daily_vectors.to_numpy(dtype=float)
	medoid_indices = pam_k_medoids(data, K)
	medoid_days = daily_vectors.iloc[medoid_indices]

	# determine cluster assignment for each day and cluster sizes
	medoids = data[medoid_indices]
	distances = pairwise_distances(data, medoids)
	assignments = np.argmin(distances, axis=1)  # which medoid each day is assigned to (0..k-1)
	counts = np.bincount(assignments, minlength=len(medoid_indices))

	medoid_days = medoid_days.copy()
	medoid_days["ClusterSize"] = counts

	print(f"\nRepresentative k-medoid set for k={K} (with cluster sizes):")
	print(medoid_days.to_string())


if __name__ == "__main__":
	main()
