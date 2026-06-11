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

class GreedyShiftAssigner(ShiftAssigner):
    """A simple greedy assigner to quickly check feasibility."""

    def assign(self, context) -> Schedule:
        # Sort shifts by start time
        sorted_shifts = sorted(context.shifts, key=lambda s: s.time_slot.start)
        
        assigned_shifts = []
        cadet_shifts = {c.personal_number: [] for c in context.cadets}
        
        for shift in sorted_shifts:
            assigned = False
            for cadet in context.cadets:
                # 1. Check basic constraints
                if not cadet.is_available_during(shift.time_slot):
                    continue
                if not cadet.can_take_job(shift.job.name):
                    continue
                
                # 2. Check overlap/consecutive constraints
                incompatible = False
                for prev_shift in cadet_shifts[cadet.personal_number]:
                    if prev_shift.time_slot.overlaps(shift.time_slot):
                        if not context.constraint_index.can_overlap(prev_shift.job.job_type, shift.job.job_type):
                            incompatible = True
                            break
                    elif prev_shift.time_slot.is_consecutive_with(shift.time_slot):
                        if not context.constraint_index.can_be_consecutive(prev_shift.job.job_type, shift.job.job_type):
                            incompatible = True
                            break
                            
                if not incompatible:
                    shift.assigned_cadet = cadet
                    assigned_shifts.append(shift)
                    cadet_shifts[cadet.personal_number].append(shift)
                    assigned = True
                    break
            
            if not assigned:
                raise ValueError(f"Greedy check failed: No available cadet for shift {shift.job.name} at {shift.time_slot}.")
                
        return Schedule(assignments=assigned_shifts)
