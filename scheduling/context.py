"""ScheduleContext builder and container.

Includes mathematical artifacts used by solvers:
- shift_ids: stable string ids for shifts
- D, L, R: difficulty, duration, required cadets per shift
- Q: compatibility matrix mapping (s1_id, s2_id) -> bool
- E_close: list of shift id pairs with gap in (0, T_rest)
- T_rest, rho: evaluation parameters
"""

from dataclasses import dataclass
from typing import List, Dict, Tuple
from datetime import timedelta

from domain.cadet import Cadet
from domain.job import Job, Shift
from domain.constraints import ConstraintIndex


@dataclass
class ScheduleContext:
    cadets: List[Cadet]
    shifts: List[Shift]
    constraint_index: ConstraintIndex

    # Mathematical properties
    shift_ids: List[str]
    D: Dict[str, float]
    L: Dict[str, float]
    R: Dict[str, int]
    Q: Dict[Tuple[str, str], bool]
    E_close: List[Tuple[str, str]]
    T_rest: float
    rho: float

    def can_assign_both(self, s1_id: str, s2_id: str) -> bool:
        return self.Q.get((s1_id, s2_id), True)


def build_context(
    cadets: List[Cadet],
    jobs: List[Job],
    constraint_index: ConstraintIndex,
    T_rest: float = 8.0,
    rho: float = 2.0,
) -> ScheduleContext:
    """Build a ScheduleContext by flattening jobs into shifts and computing math props.

    Args:
        cadets: list of Cadet
        jobs: list of Job
        constraint_index: constraints by job type
        T_rest: rest gap in hours to mark close-shift penalties
        rho: penalty weight (stored in context)

    Returns:
        ScheduleContext with additional mappings used by solvers
    """
    shifts: List[Shift] = []
    for job in jobs:
        for time_slot, difficulty in job.difficulty_by_slot.items():
            shifts.append(Shift(job=job, time_slot=time_slot, difficulty=difficulty))

    # Assign stable ids
    shift_ids: List[str] = [f"s{idx}" for idx in range(len(shifts))]

    # D, L, R
    D: Dict[str, float] = {}
    L: Dict[str, float] = {}
    R: Dict[str, int] = {}
    for sid, shift in zip(shift_ids, shifts):
        D[sid] = float(shift.difficulty)
        L[sid] = float(shift.duration_hours)
        R[sid] = 1  # per specification

    # Build Q: compatibility. By default non-overlapping non-consecutive pairs are allowed.
    Q: Dict[Tuple[str, str], bool] = {}
    n = len(shifts)
    for i in range(n):
        for j in range(n):
            if i == j:
                Q[(shift_ids[i], shift_ids[j])] = False
                continue

            s1 = shifts[i]
            s2 = shifts[j]
            t1 = s1.time_slot
            t2 = s2.time_slot

            # overlapping
            if t1.overlaps(t2):
                allowed = constraint_index.can_overlap(s1.job.job_type, s2.job.job_type)
            elif t1.is_consecutive_with(t2):
                allowed = constraint_index.can_be_consecutive(s1.job.job_type, s2.job.job_type)
            else:
                # non-overlapping, non-consecutive -> allowed
                allowed = True

            Q[(shift_ids[i], shift_ids[j])] = bool(allowed)

    # Ensure symmetry
    for (a, b), val in list(Q.items()):
        Q[(b, a)] = Q[(a, b)]

    # Compute E_close: pairs with positive gap < T_rest (exclude overlapping pairs)
    E_close: List[Tuple[str, str]] = []
    rest_delta = timedelta(hours=T_rest)
    for i in range(n):
        for j in range(n):
            if i == j:
                continue
            s1 = shifts[i]
            s2 = shifts[j]
            # if s1 ends before s2 starts
            if s1.time_slot.end <= s2.time_slot.start:
                gap = s2.time_slot.start - s1.time_slot.end
                if timedelta(0) < gap < rest_delta:
                    E_close.append((shift_ids[i], shift_ids[j]))

    return ScheduleContext(
        cadets=cadets,
        shifts=shifts,
        constraint_index=constraint_index,
        shift_ids=shift_ids,
        D=D,
        L=L,
        R=R,
        Q=Q,
        E_close=E_close,
        T_rest=T_rest,
        rho=rho,
    )
