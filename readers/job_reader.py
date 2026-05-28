"""Reader for jobs JSON file (moved from io package)."""

import json
from typing import List, Dict, Any
from pathlib import Path

from domain import Job, TimeSlot


class JobJSONReader:
    @classmethod
    def read(cls, path: str) -> List[Job]:
        file_path = Path(path)

        if not file_path.exists():
            raise FileNotFoundError(f"Jobs file not found: {path}")

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)

        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in jobs file: {e}") from e
        except Exception as e:
            raise ValueError(f"Error reading jobs file: {e}") from e

        if not isinstance(data, dict):
            raise ValueError("Jobs JSON must be an object/dictionary")

        if not data:
            raise ValueError("No jobs found in JSON file")

        jobs = []

        for job_name, job_info in data.items():
            try:
                job = cls._parse_job(job_name, job_info)
                jobs.append(job)

            except ValueError as e:
                raise ValueError(f"Error parsing job '{job_name}': {e}") from e

        return jobs

    @classmethod
    def _parse_job(cls, job_name: str, job_info: Dict[str, Any]) -> Job:
        if not isinstance(job_info, dict):
            raise ValueError(f"Job data must be a dictionary")

        if "job_type" not in job_info:
            raise ValueError("Missing field: job_type")

        if "difficulty_by_time_slot" not in job_info:
            raise ValueError("Missing field: difficulty_by_time_slot")

        job_type = job_info["job_type"]
        if not isinstance(job_type, str) or not job_type.strip():
            raise ValueError("job_type must be a non-empty string")

        difficulty_by_slot = {}
        difficulty_data = job_info["difficulty_by_time_slot"]

        if not isinstance(difficulty_data, dict):
            raise ValueError("difficulty_by_time_slot must be a dictionary")

        if not difficulty_data:
            raise ValueError("Job must have at least one time slot")

        for time_slot_str, difficulty in difficulty_data.items():
            try:
                try:
                    difficulty_float = float(difficulty)
                except (ValueError, TypeError):
                    raise ValueError(
                        f"Difficulty '{difficulty}' for slot '{time_slot_str}' "
                        f"must be numeric"
                    )

                if not (1 <= difficulty_float <= 10):
                    raise ValueError(
                        f"Difficulty {difficulty_float} for slot '{time_slot_str}' "
                        f"is not in range [1, 10]"
                    )

                time_slot = TimeSlot.from_string(time_slot_str)
                difficulty_by_slot[time_slot] = difficulty_float

            except ValueError as e:
                raise ValueError(
                    f"Error parsing time slot '{time_slot_str}': {e}"
                ) from e

        return Job(
            name=job_name,
            job_type=job_type.strip(),
            difficulty_by_slot=difficulty_by_slot,
        )
