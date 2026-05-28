"""Schedule container holding assigned shifts."""
from dataclasses import dataclass
from typing import List

from domain.job import Shift


@dataclass
class Schedule:
    assignments: List[Shift]

    def is_complete(self) -> bool:
        return all(s.is_assigned for s in self.assignments)
