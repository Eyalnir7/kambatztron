"""ShiftAssigner ABC and CpsatShiftAssigner implementation."""
from abc import ABC, abstractmethod
from typing import List
from ortools.sat.python import cp_model

from domain.job import Shift
from .solver import SchedulingProblem
from .schedule import Schedule


class ShiftAssigner(ABC):
    @abstractmethod
    def assign(self, context) -> Schedule:
        raise NotImplementedError()


class CpsatShiftAssigner(ShiftAssigner):
    """An exact assigner using OR-Tools CP-SAT solver."""

    def __init__(self, t_rest_hours: float = 8.0, rho: float = 10.0):
        self.t_rest_hours = t_rest_hours
        self.rho = rho

    def assign(self, context) -> Schedule:
        # context: ScheduleContext (has .cadets, .shifts, .constraint_index)
        problem = SchedulingProblem(
            cadets=context.cadets,
            shifts=context.shifts,
            constraint_index=context.constraint_index,
            t_rest_hours=self.t_rest_hours,
            rho=self.rho
        )

        solver, status = problem.solve()

        if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
            # Assign cadets based on solution
            assigned_shifts: List[Shift] = []
            for s_idx, shift in enumerate(context.shifts):
                assigned_cadet = None
                for c_idx, cadet in enumerate(context.cadets):
                    if solver.Value(problem.X[(c_idx, s_idx)]) == 1:
                        assigned_cadet = cadet
                        break
                
                if assigned_cadet is None:
                    raise ValueError(f"Solver error: no cadet assigned to {shift}")
                    
                shift.assigned_cadet = assigned_cadet
                assigned_shifts.append(shift)
                
            return Schedule(assignments=assigned_shifts)
        elif status == cp_model.INFEASIBLE:
            raise ValueError("The scheduling problem is strictly INFEASIBLE.")
        else:
            raise ValueError(f"Solver finished with status: {solver.StatusName(status)}")
