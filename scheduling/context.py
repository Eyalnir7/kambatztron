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
    """Build a ScheduleContext by flattening jobs into shifts and injecting team constraints."""
    
    # 1. Apply team constraints to cadets
    processed_cadets = []
    for cadet in cadets:
        if cadet.team:
            team_unavailabilities = constraint_index.get_team_unavailabilities(cadet.team)
            if team_unavailabilities:
                # Cadet is a frozen pydantic model, use model_copy
                new_unavailabilities = list(cadet.unavailable_slots) + team_unavailabilities
                processed_cadet = cadet.model_copy(update={'unavailable_slots': new_unavailabilities})
                processed_cadets.append(processed_cadet)
            else:
                processed_cadets.append(cadet)
        else:
            processed_cadets.append(cadet)

    # 2. Flatten jobs into shifts
    shifts: List[Shift] = []
    for job in jobs:
        for time_slot, difficulty in job.difficulty_by_slot.items():
            shifts.append(Shift(job=job, time_slot=time_slot, difficulty=difficulty))

    return ScheduleContext(cadets=processed_cadets, shifts=shifts, constraint_index=constraint_index)
