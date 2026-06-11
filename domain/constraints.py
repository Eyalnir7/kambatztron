"""Job constraints and constraint lookups."""

from pydantic import BaseModel, ConfigDict
from typing import Dict, Tuple, List, Optional
from .time_slot import TimeSlot


class JobConstraint(BaseModel):
    """Defines compatibility between two job types."""
    model_config = ConfigDict(frozen=True)

    job_type_a: str
    job_type_b: str
    can_overlap: bool
    can_be_consecutive: bool


class TeamConstraint(BaseModel):
    """A constraint applied to an entire team."""
    model_config = ConfigDict(frozen=True)

    team: str
    unavailable_slots: List[TimeSlot] = []


class ConstraintIndex:
    """Pre-built lookup structure for O(1) constraint queries."""

    def __init__(self, constraints: List[JobConstraint], team_constraints: List[TeamConstraint] = None):
        """Build the index from a list of constraints."""
        self._constraints: Dict[Tuple[str, str], JobConstraint] = {}
        self.team_constraints = team_constraints or []

        for constraint in constraints:
            # Store constraint in both directions (bidirectional)
            key_forward = (constraint.job_type_a, constraint.job_type_b)
            key_reverse = (constraint.job_type_b, constraint.job_type_a)

            self._constraints[key_forward] = constraint
            self._constraints[key_reverse] = constraint

    def can_overlap(self, job_type_a: str, job_type_b: str) -> bool:
        key = (job_type_a, job_type_b)
        constraint = self._constraints.get(key)
        if constraint is None: #
            return False  # Default: incompatible
        return constraint.can_overlap

    def can_be_consecutive(self, job_type_a: str, job_type_b: str) -> bool:
        # Wildcard rule: 'jobs at the base' and 'dynamic guarding' can be consecutive with any other job
        if job_type_a in ("jobs at the base", "dynamic guarding") or job_type_b in ("jobs at the base", "dynamic guarding"):
            return True

        key = (job_type_a, job_type_b)
        constraint = self._constraints.get(key)
        if constraint is None:
            return False  # Default: incompatible
        return constraint.can_be_consecutive

    def get_team_unavailabilities(self, team: str) -> List[TimeSlot]:
        slots = []
        for tc in self.team_constraints:
            if tc.team == team:
                slots.extend(tc.unavailable_slots)
        return slots

    @classmethod
    def from_csv_rows(cls, rows: List[Dict[str, str]]) -> "ConstraintIndex":
        """Create a ConstraintIndex from CSV rows."""
        constraints = []

        for i, row in enumerate(rows, start=2):  # Start at 2 for 1-indexed, header at 1
            try:
                job_type_a = row.get("job_type_a", "").strip()
                job_type_b = row.get("job_type_b", "").strip()
                can_overlap_str = row.get("can_overlap", "").strip().lower()
                can_be_consecutive_str = (
                    row.get("can_be_consecutive", "").strip().lower()
                )

                if not job_type_a or not job_type_b:
                    continue # Skip empty

                # Parse boolean strings
                can_overlap = can_overlap_str in ("true", "1", "yes")
                can_be_consecutive = can_be_consecutive_str in (
                    "true",
                    "1",
                    "yes",
                )

                constraint = JobConstraint(
                    job_type_a=job_type_a,
                    job_type_b=job_type_b,
                    can_overlap=can_overlap,
                    can_be_consecutive=can_be_consecutive,
                )
                constraints.append(constraint)

            except Exception as e:
                raise ValueError(
                    f"Error parsing constraint row {i}: {e}"
                ) from e

        return cls(constraints)
