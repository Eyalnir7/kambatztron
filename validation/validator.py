"""InputValidator and ValidationResult for the project."""
from dataclasses import dataclass
from typing import List, Tuple

from domain.cadet import Cadet
from domain.job import Job
from domain.constraints import JobConstraint, ConstraintIndex


@dataclass
class ValidationResult:
    is_valid: bool
    errors: List[str]


class InputValidator:
    """Validate cadets, jobs, and constraints for basic consistency."""

    @classmethod
    def validate(
        cls, cadets: List[Cadet], jobs: List[Job], constraints: ConstraintIndex
    ) -> ValidationResult:
        errors: List[str] = []

        # Cadets: unique personal numbers
        personal_numbers = [c.personal_number for c in cadets]
        dupes = {pn for pn in personal_numbers if personal_numbers.count(pn) > 1}
        if dupes:
            errors.append(f"Duplicate personal_number(s): {sorted(list(dupes))}")

        # Cadets: required fields
        for c in cadets:
            if not c.personal_number:
                errors.append(f"Cadet with missing personal_number: {c}")
            if not c.name:
                errors.append(f"Cadet with missing name: {c}")

        # Jobs: non-empty and unique names
        if not jobs:
            errors.append("No jobs provided")
        else:
            job_names = [j.name for j in jobs]
            dup_job_names = {n for n in job_names if job_names.count(n) > 1}
            if dup_job_names:
                errors.append(f"Duplicate job name(s): {sorted(list(dup_job_names))}")

        # Constraints: basic presence
        if not isinstance(constraints, ConstraintIndex):
            errors.append("Constraints must be a ConstraintIndex instance")

        is_valid = len(errors) == 0
        return ValidationResult(is_valid=is_valid, errors=errors)
