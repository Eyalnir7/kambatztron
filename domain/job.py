"""Job and Shift represent duties and assignable work units."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Optional

from .time_slot import TimeSlot
from .cadet import Cadet


@dataclass(frozen=True)
class Job:
    """A duty/job that needs to be assigned to cadets.

    Attributes:
        name: Unique job name (e.g., "Gate Guard 1")
        job_type: Type of job (e.g., "guarding", "cleaning")
        difficulty_by_slot: Mapping of TimeSlot to difficulty score (1-10)
    """

    name: str
    job_type: str
    difficulty_by_slot: Dict[TimeSlot, float] = field(default_factory=dict)

    def __post_init__(self):
        """Validate that all difficulty scores are in range [1, 10]."""
        for difficulty in self.difficulty_by_slot.values():
            if not (1 <= difficulty <= 10):
                raise ValueError(
                    f"Job '{self.name}': difficulty {difficulty} not in range [1, 10]"
                )


@dataclass
class Shift:
    """An assignable work unit: a Job at a specific TimeSlot.

    This is the unit that gets assigned to a cadet.

    Attributes:
        job: The job being assigned
        time_slot: The time slot for this assignment
        difficulty: Difficulty score for this specific shift
        assigned_cadet: The cadet assigned to this shift (None if unassigned)
    """

    job: Job
    time_slot: TimeSlot
    difficulty: float
    assigned_cadet: Optional[Cadet] = None

    def __post_init__(self):
        """Validate difficulty is in range [1, 10]."""
        if not (1 <= self.difficulty <= 10):
            raise ValueError(
                f"Shift {self.job.name}/{self.time_slot}: "
                f"difficulty {self.difficulty} not in range [1, 10]"
            )

    @property
    def is_assigned(self) -> bool:
        """Check if a cadet has been assigned to this shift."""
        return self.assigned_cadet is not None

    @property
    def duration_hours(self) -> float:
        """Calculate the duration of this shift in hours."""
        delta = self.time_slot.end - self.time_slot.start
        return delta.total_seconds() / 3600

    def __repr__(self) -> str:
        """Return a readable string representation."""
        cadet_name = (
            self.assigned_cadet.name
            if self.assigned_cadet
            else "Unassigned"
        )
        return (
            f"Shift({self.job.name}, {self.time_slot}, "
            f"difficulty={self.difficulty}, cadet={cadet_name})"
        )
