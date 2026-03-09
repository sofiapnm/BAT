from dataclasses import dataclass, field

from gurobipy import GRB


@dataclass(frozen=True)
class GridConfig:
    emissions_kgco2_per_kwh: float = 0.35
    export_emissions_credit_kgco2_per_kwh: float = 0.0


@dataclass(frozen=True)
class SolverConfig:
    primary_solver: str = "gurobi"
    fallback_solver: str = "highs"
    gurobi_options: dict = field(
        default_factory=lambda: {
            "Method": int(GRB.METHOD_BARRIER),
            "Crossover": 0,
            "OutputFlag": 0,
        }
    )
