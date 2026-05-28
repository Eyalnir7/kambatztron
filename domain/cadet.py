"""Cadet represents a person who can be assigned to shifts."""

from dataclasses import dataclass, field
from typing import List

from .time_slot import TimeSlot


@dataclass(frozen=True)
class Cadet:
    """A cadet who can be assigned to shifts.

    Attributes:
        personal_number: Unique military ID (primary key)
        name: Cadet name
        unavailable_slots: Time slots when the cadet is not available
        forbidden_jobs: Job names the cadet cannot do
        gender: Cadet gender
        team: Cadet team/unit
        platoon: Cadet platoon
    """

    personal_number: str
    name: str
    unavailable_slots: List[TimeSlot] = field(default_factory=list)
    forbidden_jobs: List[str] = field(default_factory=list)
    gender: str = ""
    team: str = ""
    platoon: str = ""

    @classmethod
    def from_csv_row(
        cls,
        personal_number: str,
        name: str,
        unavailable_hours: str,
        forbidden_jobs: str,
        gender: str,
        team: str,
        platoon: str,
    ) -> "Cadet":
        """Create a Cadet from CSV row data.

        Args:
            personal_number: Unique military ID
            name: Cadet name
            unavailable_hours: Semicolon-delimited time slot strings,
                             empty string means no unavailable hours
            forbidden_jobs: Semicolon-delimited job names,
                          empty string means no forbidden jobs
            gender: Cadet gender
            team: Cadet team
            platoon: Cadet platoon

        Returns:
            Cadet instance

        Raises:
            ValueError: If time slot format is invalid
        """
        # Parse unavailable hours
        unavailable_slots = []
        if unavailable_hours and unavailable_hours.strip():
            for slot_str in unavailable_hours.split(";"):
                slot_str = slot_str.strip()
                if slot_str:
                    unavailable_slots.append(TimeSlot.from_string(slot_str))

        # Parse forbidden jobs
        forbidden_jobs_list = []
        if forbidden_jobs and forbidden_jobs.strip():
            for job_name in forbidden_jobs.split(";"):
                job_name = job_name.strip()
                if job_name:
                    forbidden_jobs_list.append(job_name)

        return cls(
            personal_number=personal_number,
            name=name,
            unavailable_slots=unavailable_slots,
            forbidden_jobs=forbidden_jobs_list,
            gender=gender,
            team=team,
            platoon=platoon,
        )

    def is_available_during(self, time_slot: TimeSlot) -> bool:
        """Check if this cadet is available during a given time slot.

        A cadet is available if the time slot does not overlap with any
        of their unavailable slots.

        Args:
            time_slot: TimeSlot to check

        Returns:
            True if cadet is available, False if conflicted
        """
        return not any(slot.overlaps(time_slot) for slot in self.unavailable_slots)

    def can_take_job(self, job_name: str) -> bool:
        """Check if this cadet can take a specific job.

        Args:
            job_name: Name of the job

        Returns:
            True if job is not forbidden, False otherwise
        """
        return job_name not in self.forbidden_jobs
