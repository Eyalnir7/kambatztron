# Extensive Test Situation

This directory contains a larger dataset for exercising the scheduler against a realistic multi-day workload with many overlap and rest-gap decisions.

## Scenario

The fixture spans several days of duty coverage and combines:

- multiple cadets across multiple teams and platoons
- jobs with different types and time-slot patterns
- explicit unavailability windows
- forbidden job lists
- compatibility rules in `job_constraints.csv`

The exact shape of the schedule is driven by the input files in this directory rather than by hardcoded assumptions in the docs.

## How to run

Run the scheduler from the repository root:

```bash
python shift_scheduler.py \
  --cadets extensive_test/cadets.csv \
  --jobs extensive_test/jobs.json \
  --constraints extensive_test/job_constraints.csv \
  --output extensive_test/test_schedule_output.xlsx
```

## What this fixture is useful for

1. Verifying that the readers still accept the real CSV and JSON formats used by the larger dataset.
2. Checking that the CP-SAT solver can produce a complete assignment under denser constraint combinations.
3. Inspecting the workbook output and evaluation folder generated for a larger schedule.
