"""ShiftAssigner ABC and GreedyShiftAssigner implementation."""
from abc import ABC, abstractmethod
from typing import List, Dict

from domain.cadet import Cadet
from domain.job import Shift
from domain.constraints import ConstraintIndex
from .workload import WorkloadTracker
from .schedule import Schedule


class ShiftAssigner(ABC):
    @abstractmethod
    def assign(self, context) -> Schedule:
        raise NotImplementedError()


class GreedyShiftAssigner(ShiftAssigner):
    """A simple greedy assigner that honors hard constraints."""

    def __init__(self):
        self.workload = WorkloadTracker()

    def assign(self, context) -> Schedule:
        # context: ScheduleContext
        assigned_shifts: List[Shift] = []
        # track assigned shifts per cadet personal_number
        cadet_assignments: Dict[str, List[Shift]] = {c.personal_number: [] for c in context.cadets}

        for shift in context.shifts:
            candidates = []
            for cadet in context.cadets:
                if not cadet.is_available_during(shift.time_slot):
                    continue
                if not cadet.can_take_job(shift.job.name):
                    continue

                # check assigned shifts for overlaps and consecutive rules
                ok = True
                for a in cadet_assignments.get(cadet.personal_number, []):
                    # Overlap check
                    if a.time_slot.overlaps(shift.time_slot):
                        if not context.constraint_index.can_overlap(a.job.job_type, shift.job.job_type):
                            ok = False
                            break
                    # Consecutive check
                    if a.time_slot.is_consecutive_with(shift.time_slot):
                        if not context.constraint_index.can_be_consecutive(a.job.job_type, shift.job.job_type):
                            ok = False
                            break

                if ok:
                    candidates.append(cadet)

            if not candidates:
                raise ValueError(f"No eligible cadet found for shift: {shift}")

            chosen = self.workload.least_loaded(candidates)
            if chosen is None:
                raise ValueError(f"No candidate chosen for shift: {shift}")

            shift.assigned_cadet = chosen
            self.workload.update(chosen, shift)
            cadet_assignments[chosen.personal_number].append(shift)
            assigned_shifts.append(shift)

        return Schedule(assignments=assigned_shifts)
