from pyomo.environ import SolverFactory


class GurobiSizeLimitError(RuntimeError):
    pass


class ModelSolver:
    def __init__(self, solver_cfg):
        self.solver_cfg = solver_cfg

    def solve(self, model):
        primary = SolverFactory(self.solver_cfg.primary_solver)

        if not primary.available():
            print(
                f"{self.solver_cfg.primary_solver} not available, falling back to {self.solver_cfg.fallback_solver}."
            )
            return self._solve_fallback(model)

        try:
            for key, val in self.solver_cfg.gurobi_options.items():
                primary.options[key] = val
            results = primary.solve(model, tee=False)
            return results, self.solver_cfg.primary_solver
        except Exception as exc:
            if "size-limited license" in str(exc).lower():
                raise GurobiSizeLimitError("GUROBI_SIZE_LIMIT") from exc

            print(
                f"{self.solver_cfg.primary_solver} solve failed ({exc}), trying {self.solver_cfg.fallback_solver}."
            )
            return self._solve_fallback(model, source_exc=exc)

    def _solve_fallback(self, model, source_exc=None):
        solver = SolverFactory(self.solver_cfg.fallback_solver)
        if not solver.available():
            if source_exc is None:
                raise RuntimeError(
                    f"Neither {self.solver_cfg.primary_solver} nor {self.solver_cfg.fallback_solver} is available."
                )
            raise RuntimeError(
                f"{self.solver_cfg.primary_solver} failed and {self.solver_cfg.fallback_solver} is unavailable."
            ) from source_exc
        results = solver.solve(model, tee=False)
        return results, self.solver_cfg.fallback_solver
