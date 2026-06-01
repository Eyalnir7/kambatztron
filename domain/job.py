"""Job and Shift represent duties and assignable work units."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, model_validator
from typing import Dict, Optional, Any

from .time_slot import TimeSlot

# To avoid circular imports, Cadet will be imported conditionally or defined as Any
# Actually, since Shift has assigned_cadet: Optional[Cadet], we can import it.
# We'll use a string reference 'Cadet' for type hint to avoid circular import issues if needed,
# but let's try direct import first.
from .cadet import Cadet


class Job(BaseModel):
    """A duty/job that needs to be assigned to cadets."""
    model_config = ConfigDict(frozen=True)

    name: str
    job_type: str
    difficulty_by_slot: Dict[TimeSlot, float] = Field(default_factory=dict)

    @model_validator(mode='after')
    def check_difficulty_scores(self) -> 'Job':
        """Validate that all difficulty scores are in range [1, 10]."""
        for slot, difficulty in self.difficulty_by_slot.items():
            if not (1 <= difficulty <= 10):
                raise ValueError(
                    f"Job '{self.name}': difficulty {difficulty} not in range [1, 10]"
                )
        return self


class Shift(BaseModel):
    """An assignable work unit: a Job at a specific TimeSlot."""
    # We allow mutation for assigned_cadet
    model_config = ConfigDict(arbitrary_types_allowed=True)

    job: Job
    time_slot: TimeSlot
    difficulty: float
    assigned_cadet: Optional[Cadet] = None

    @model_validator(mode='after')
    def check_difficulty(self) -> 'Shift':
        """Validate difficulty is in range [1, 10]."""
        if not (1 <= self.difficulty <= 10):
            raise ValueError(
                f"Shift {self.job.name}/{self.time_slot}: "
                f"difficulty {self.difficulty} not in range [1, 10]"
            )
        return self

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

# Rebuild model schema due to forward refs if needed
Shift.model_rebuild()
