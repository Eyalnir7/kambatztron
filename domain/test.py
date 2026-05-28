
"""Test parsing of example CSV/JSON data.

This script is a convenience demo and should only run when executed
directly. Wrapping in a `main()` prevents unittest discovery from
executing it at import time.
"""

import csv
import json
from domain import Cadet, Job, TimeSlot, JobConstraint, ConstraintIndex


def main():
    # Test 1: Parse cadets from CSV
    print("=== Test 1: Parse Cadets from CSV ===")
    cadets = []
    with open("example_cadets.csv", "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            cadet = Cadet.from_csv_row(
                personal_number=row["personal_number"],
                name=row["name"],
                unavailable_hours=row["unavailable_hours"],
                forbidden_jobs=row["forbidden_jobs"],
                gender=row["gender"],
                team=row["team"],
                platoon=row["platoon"],
            )
            cadets.append(cadet)
            print(
                f"  {cadet.name} ({cadet.personal_number}): "
                f"{len(cadet.unavailable_slots)} unavailable slots, "
                f"{len(cadet.forbidden_jobs)} forbidden jobs"
            )

    print(f"Total cadets: {len(cadets)}")
    print()

    # Test 2: Parse jobs from JSON
    print("=== Test 2: Parse Jobs from JSON ===")
    jobs = []
    with open("example_jobs.json", "r", encoding="utf-8") as f:
        jobs_data = json.load(f)

    for job_name, job_info in jobs_data.items():
        difficulty_by_slot = {}
        for slot_str, difficulty in job_info["difficulty_by_time_slot"].items():
            slot = TimeSlot.from_string(slot_str)
            difficulty_by_slot[slot] = float(difficulty)

        job = Job(
            name=job_name,
            job_type=job_info["job_type"],
            difficulty_by_slot=difficulty_by_slot,
        )
        jobs.append(job)
        print(
            f"  {job.name} (type: {job.job_type}): "
            f"{len(job.difficulty_by_slot)} time slots"
        )

    print(f"Total jobs: {len(jobs)}")
    print()

    # Test 3: Parse constraints from CSV
    print("=== Test 3: Parse Constraints from CSV ===")
    constraints = []
    with open("example_job_constraints.csv", "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    index = ConstraintIndex.from_csv_rows(rows)
    print(f"Total constraint pairs: {len(index._constraints)}")
    print("Sample constraint queries:")
    print(
        f"  guarding & cleaning can overlap? {index.can_overlap('guarding', 'cleaning')}"
    )
    print(
        f"  standby-team & standby-team can overlap? {index.can_overlap('standby-team', 'standby-team')}"
    )
    print()

    print("✅ CSV/JSON parsing successful!")


if __name__ == "__main__":
    main()