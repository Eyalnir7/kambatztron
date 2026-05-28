"""Job constraints and constraint lookups."""

from dataclasses import dataclass
from typing import Dict, Tuple, List, Optional


@dataclass(frozen=True)
class JobConstraint:
    """Defines compatibility between two job types.

    Attributes:
        job_type_a: First job type
        job_type_b: Second job type
        can_overlap: Whether jobs of these types can overlap in time
        can_be_consecutive: Whether jobs of these types can be assigned
                           consecutively to the same cadet
    """

    job_type_a: str
    job_type_b: str
    can_overlap: bool
    can_be_consecutive: bool


@dataclass
class ConstraintIndex:
    """Pre-built lookup structure for O(1) constraint queries.

    Stores constraints by (type_a, type_b) tuple for fast lookups during solving.
    Handles bidirectionality: (A, B) and (B, A) are treated as the same constraint.
    Default behavior (not explicitly listed): incompatible (False).
    """

    _constraints: Dict[Tuple[str, str], JobConstraint]

    def __init__(self, constraints: List[JobConstraint]):
        """Build the index from a list of constraints.

        Args:
            constraints: List of JobConstraint objects
        """
        self._constraints = {}

        for constraint in constraints:
            # Store constraint in both directions (bidirectional)
            key_forward = (constraint.job_type_a, constraint.job_type_b)
            key_reverse = (constraint.job_type_b, constraint.job_type_a)

            self._constraints[key_forward] = constraint
            self._constraints[key_reverse] = constraint

    def can_overlap(self, job_type_a: str, job_type_b: str) -> bool:
        """Check if two job types can overlap in time.

        Args:
            job_type_a: First job type
            job_type_b: Second job type

        Returns:
            True if they can overlap, False otherwise (default: False)
        """
        key = (job_type_a, job_type_b)
        constraint = self._constraints.get(key)

        if constraint is None:
            return False  # Default: incompatible

        return constraint.can_overlap

    def can_be_consecutive(self, job_type_a: str, job_type_b: str) -> bool:
        """Check if two job types can be assigned consecutively.

        Args:
            job_type_a: First job type
            job_type_b: Second job type

        Returns:
            True if they can be consecutive, False otherwise (default: False)
        """
        key = (job_type_a, job_type_b)
        constraint = self._constraints.get(key)

        if constraint is None:
            return False  # Default: incompatible

        return constraint.can_be_consecutive

    @classmethod
    def from_csv_rows(cls, rows: List[Dict[str, str]]) -> "ConstraintIndex":
        """Create a ConstraintIndex from CSV rows.

        Expected columns: job_type_a, job_type_b, can_overlap, can_be_consecutive

        Args:
            rows: List of dictionaries with constraint data

        Returns:
            ConstraintIndex instance

        Raises:
            ValueError: If columns are missing or values are invalid
        """
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
                    raise ValueError("job_type_a or job_type_b is empty")

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
