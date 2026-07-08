# Shift Scheduler — OOP Design

## High-Level Architecture

The pipeline has 4 clear stages: **Parse → Validate → Solve → Export**.
Each stage is a clean boundary, designed around the domain model first, then the pipeline components.

```
CLI args
   │
   ▼
ShiftSchedulerApp
   ├── CadetCSVReader    ──┐
   ├── JobJSONReader     ──┼──► InputValidator ──► ScheduleContext
   └── ConstraintsReader ──┘          │
                                      │ (abort on error)
                                      ▼
                              GreedyShiftAssigner
                              + WorkloadTracker
                                      │
                                      ▼
                               Schedule
                                      │
                                      ▼
                               ExcelExporter ──► schedule.xlsx
```

---

## 1. Domain Model

Pure data containers — no business logic, just structure.
Implemented as `@dataclass` or Pydantic models.

### `TimeSlot`
```
TimeSlot
  - start: datetime
  - end: datetime
  + overlaps(other: TimeSlot) -> bool
  # Shift Scheduler — Current Design

  This file mirrors the architecture that is actually implemented in the repository.

  ## High-Level Architecture

  The active pipeline is:

  ```text
  CLI args
     │
     ▼
  ShiftSchedulerApp
     ├── CadetCSVReader
     ├── JobJSONReader
     └── ConstraintsCSVReader
            │
            ▼
     InputValidator
            │
            ▼
     build_context()
            │
            ▼
     CpsatShiftAssigner
            │
            ▼
     Schedule
            │
            ├── ExcelExporter
            └── Evaluator
  ```

  ## 1. Domain Model

  The current code uses Pydantic models for the core domain objects.

  ### `TimeSlot`

  Defined in [domain/time_slot.py](domain/time_slot.py).

  ```text
  TimeSlot
    - start: datetime
    - end: datetime
    + overlaps(other: TimeSlot) -> bool
    + is_consecutive_with(other: TimeSlot) -> bool
    + from_string(value: str) -> TimeSlot
  ```

  ### `Cadet`

  Defined in [domain/cadet.py](domain/cadet.py).

  ```text
  Cadet
    - personal_number: str
    - name: str
    - unavailable_slots: list[TimeSlot]
    - forbidden_jobs: list[str]
    - forbidden_job_names: list[str]
    - gender: str
    - team: str
    - platoon: str
  ```

  ### `Job`

  Defined in [domain/job.py](domain/job.py).

  ```text
  Job
    - name: str
    - job_type: str
    - difficulty_by_slot: dict[TimeSlot, float]
  ```

  ### `Shift`

  Defined in [domain/job.py](domain/job.py).

  ```text
  Shift
    - job: Job
    - time_slot: TimeSlot
    - difficulty: float
    - assigned_cadet: Cadet | None
    + duration_hours() -> float
    + is_assigned -> bool
  ```

  ### `JobConstraint`

  Defined in [domain/constraints.py](domain/constraints.py).

  ```text
  JobConstraint
    - job_type_a: str
    - job_type_b: str
    - can_overlap: bool
    - can_be_consecutive: bool
  ```

  ## 2. Input Layer

  The readers live in [readers/](readers).

  ### `CadetCSVReader`

  ```text
  CadetCSVReader.read(path: str) -> list[Cadet]
  ```

  Current behavior:

  - requires the expected cadet columns
  - splits `unavailable_hours` and `forbidden_jobs` on `;`
  - accepts optional `forbidden_job_names`
  - raises on missing files or malformed rows

  ### `JobJSONReader`

  ```text
  JobJSONReader.read(path: str) -> list[Job]
  ```

  Current behavior:

  - expects a JSON object keyed by job name
  - requires `job_type` and `difficulty_by_time_slot`
  - validates that each difficulty is numeric and in the `1..10` range

  ### `ConstraintsCSVReader`

  ```text
  ConstraintsCSVReader.read(path: str) -> ConstraintIndex
  ```

  Current behavior:

  - requires the four constraints columns
  - converts boolean-like strings such as `true`, `1`, and `yes`
  - builds a bidirectional `ConstraintIndex`

  ## 3. Validation Layer

  `InputValidator` in [validation/validator.py](validation/validator.py) is intentionally lightweight in the current codebase.

  It checks:

  - duplicate cadet personal numbers
  - missing cadet personal numbers or names
  - duplicate job names
  - that at least one job exists
  - that the constraints argument is a `ConstraintIndex`

  Most parsing and range validation happens earlier in the readers and domain models.

  ## 4. Scheduling Layer

  ### `ScheduleContext`

  Built in [scheduling/context.py](scheduling/context.py).

  The context stores:

  - `cadets`
  - `shifts`
  - `constraint_index`
  - `shift_ids`
  - `D`, `L`, `R`
  - `Q`
  - `E_close`
  - `T_rest`
  - `rho`

  ### `ConstraintIndex`

  Defined in [domain/constraints.py](domain/constraints.py).

  It currently exposes:

  - `can_overlap(job_type_a, job_type_b)`
  - `can_be_consecutive(job_type_a, job_type_b)`
  - `get_team_unavailabilities(team)`

  ### `ShiftAssigner`

  `scheduling/assigner.py` defines an abstract base assigner plus two implementations:

  - `CpsatShiftAssigner`, which is what the app uses
  - `GreedyShiftAssigner`, which remains available as a simpler alternative

  ### `WorkloadTracker`

  `WorkloadTracker` in [scheduling/workload.py](scheduling/workload.py) keeps assigned shifts per cadet and computes the score used by evaluation:

  ```text
  geometric_mean(assigned_difficulty_scores) * total_assigned_hours
  ```

  ### `Schedule`

  Defined in [scheduling/schedule.py](scheduling/schedule.py). It is a thin container for the final assigned shifts.

  ## 5. Output Layer

  ### `ExcelExporter`

  Defined in [output/excel_exporter.py](output/excel_exporter.py).

  Current behavior:

  - writes one worksheet per job type for `.xlsx` outputs
  - adds a `Legend` worksheet for team/platoon colors
  - uses cadet names only in the table cells
  - falls back to a CSV directory layout if the path is not `.xlsx`

  ### `Evaluator`

  Defined in [output/evaluator.py](output/evaluator.py).

  It writes:

  - per-cadet CSV statistics
  - a JSON summary
  - histograms for difficulty, hours, and workload
  - a scatter plot for hours vs workload

  ## 6. Orchestrator

  `ShiftSchedulerApp` in [app.py](app.py) currently performs this sequence:

  1. Read cadets, jobs, and constraints.
  2. Validate the parsed data.
  3. Build the `ScheduleContext`.
  4. Run `CpsatShiftAssigner.assign()`.
  5. Export the workbook or CSV fallback.
  6. Run the evaluator.

  The CLI entry point is [shift_scheduler.py](shift_scheduler.py), which also exposes `--t-rest` and `--rho`.

  ## 7. File Structure

  ```text
  shift_scheduler/
  ├── shift_scheduler.py
  ├── app.py
  ├── domain/
  │   ├── __init__.py
  │   ├── time_slot.py
  │   ├── cadet.py
  │   ├── job.py
  │   └── constraints.py
  ├── readers/
  │   ├── __init__.py
  │   ├── cadet_reader.py
  │   ├── job_reader.py
  │   └── constraints_reader.py
  ├── validation/
  │   ├── __init__.py
  │   └── validator.py
  ├── scheduling/
  │   ├── __init__.py
  │   ├── context.py
  │   ├── assigner.py
  │   ├── workload.py
  │   └── schedule.py
  └── output/
      ├── __init__.py
      ├── excel_exporter.py
      └── evaluator.py
  ```
