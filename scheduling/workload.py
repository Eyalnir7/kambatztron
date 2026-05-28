"""WorkloadTracker implementing the proposed workload score."""
from typing import Dict, List, Optional
import math

from domain.cadet import Cadet
from domain.job import Shift


class WorkloadTracker:
    """Track assigned shifts and compute workload scores."""

    def __init__(self):
        # Map personal_number -> list of assigned difficulties and hours
        self._assigned: Dict[str, List[Shift]] = {}

    def update(self, cadet: Cadet, shift: Shift) -> None:
        self._assigned.setdefault(cadet.personal_number, []).append(shift)

    def get_score(self, cadet: Cadet) -> float:
        shifts = self._assigned.get(cadet.personal_number, [])
        if not shifts:
            return 0.0

        difficulties = [s.difficulty for s in shifts]
        hours = sum(s.duration_hours for s in shifts)

        # geometric mean of difficulties
        geom = math.prod(difficulties) ** (1.0 / len(difficulties))

        return geom * hours

    def least_loaded(self, candidates: List[Cadet]) -> Optional[Cadet]:
        best = None
        best_score = float("inf")
        for c in candidates:
            score = self.get_score(c)
            if score < best_score:
                best_score = score
                best = c
        return best
