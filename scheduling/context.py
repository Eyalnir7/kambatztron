"""ScheduleContext builder and container."""
from dataclasses import dataclass
from typing import List

from domain.cadet import Cadet
from domain.job import Job, Shift
from domain.constraints import ConstraintIndex


@dataclass
class ScheduleContext:
    cadets: List[Cadet]
    shifts: List[Shift]
    constraint_index: ConstraintIndex


def build_context(cadets: List[Cadet], jobs: List[Job], constraint_index: ConstraintIndex) -> ScheduleContext:
    """Build a ScheduleContext by flattening jobs into shifts."""
    shifts: List[Shift] = []
    for job in jobs:
        for time_slot, difficulty in job.difficulty_by_slot.items():
            shifts.append(Shift(job=job, time_slot=time_slot, difficulty=difficulty))

    return ScheduleContext(cadets=cadets, shifts=shifts, constraint_index=constraint_index)
