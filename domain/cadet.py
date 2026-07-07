"""Cadet represents a person who can be assigned to shifts."""

from pydantic import BaseModel, ConfigDict, Field
from typing import List

from .time_slot import TimeSlot


class Cadet(BaseModel):
    """A cadet who can be assigned to shifts."""
    model_config = ConfigDict(frozen=True)

    personal_number: str
    name: str
    unavailable_slots: List[TimeSlot] = Field(default_factory=list)
    forbidden_jobs: List[str] = Field(default_factory=list)
    forbidden_job_names: List[str] = Field(default_factory=list)
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
        forbidden_job_names: str = "",
    ) -> "Cadet":
        """Create a Cadet from CSV row data."""
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

        forbidden_job_names_list = []
        if forbidden_job_names and forbidden_job_names.strip():
            for job_name in forbidden_job_names.split(";"):
                job_name = job_name.strip()
                if job_name:
                    forbidden_job_names_list.append(job_name)

        return cls(
            personal_number=personal_number,
            name=name,
            unavailable_slots=unavailable_slots,
            forbidden_jobs=forbidden_jobs_list,
            forbidden_job_names=forbidden_job_names_list,
            gender=gender,
            team=team,
            platoon=platoon,
        )

    def is_available_during(self, time_slot: TimeSlot) -> bool:
        """Check if this cadet is available during a given time slot."""
        return not any(slot.overlaps(time_slot) for slot in self.unavailable_slots)

    def can_take_job(self, job_name: str) -> bool:
        """Check if this cadet can take a specific job."""
        return job_name not in self.forbidden_jobs and job_name not in self.forbidden_job_names
