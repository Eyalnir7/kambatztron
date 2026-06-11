# Shift Scheduler — CP-SAT Design

## High-Level Architecture

The current pipeline is:

**Parse → Validate → Solve → Export → Evaluate**

```
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
   ScheduleContext
          │
          ▼
   CpsatShiftAssigner
          │
          ▼
   SchedulingProblem (OR-Tools CP-SAT)
          │
          ▼
   Schedule
          ├── ExcelExporter ──► schedule.xlsx
          └── Evaluator ──► evaluation/ (CSV, JSON, PNG)
```

---

## 1. Domain Model

The domain layer is made of small data objects that keep scheduling logic concentrated in one place.

### `TimeSlot`

```
TimeSlot
  - start: datetime
  - end: datetime
  + overlaps(other: TimeSlot) -> bool
  + is_consecutive_with(other: TimeSlot) -> bool
```

This class owns the overlap and consecutive checks so the readers and solver do not duplicate date logic.

---

### `Cadet`

```
Cadet
  - personal_number: str
  - name: str
  - unavailable_slots: list[TimeSlot]
  - forbidden_jobs: list[str]
  - gender: str
  - team: str
  - platoon: str
```

`team` and `platoon` are used for output coloring, not for scheduling constraints.

---

### `Job`

```
Job
  - name: str
  - job_type: str
  - difficulty_by_slot: dict[TimeSlot, float]
```

Each job is defined with a difficulty value for every required time slot.

---

### `Shift`

```
Shift
  - job: Job
  - time_slot: TimeSlot
  - difficulty: float
  - assigned_cadet: Cadet | None
```

A shift is the atomic assignment unit used by the solver.

---

### `JobConstraint`

```
JobConstraint
  - job_type_a: str
  - job_type_b: str
  - can_overlap: bool
  - can_be_consecutive: bool
```

---

### `TeamConstraint`

```
TeamConstraint
  - team: str
  - unavailable_slots: list[TimeSlot]
```

Team constraints are injected into cadet unavailability during context construction.

---

### `ConstraintIndex`

```
ConstraintIndex
  - _constraints: dict[tuple[str, str], JobConstraint]
  - team_constraints: list[TeamConstraint]
  + can_overlap(type_a: str, type_b: str) -> bool
  + can_be_consecutive(type_a: str, type_b: str) -> bool
  + get_team_unavailabilities(team: str) -> list[TimeSlot]
```

The index stores job-type compatibility in both directions for fast lookups during solver setup.

---

## 2. Input Layer

Each file type has its own reader class.

### `CadetCSVReader`

```
CadetCSVReader
  + read(path: str) -> list[Cadet]
```

### `JobJSONReader`

```
JobJSONReader
  + read(path: str) -> list[Job]
```

### `ConstraintsCSVReader`

```
ConstraintsCSVReader
  + read(path: str) -> ConstraintIndex
```

The constraints reader returns a prebuilt `ConstraintIndex`, not a raw row list.

---

## 3. Validation Layer

The validator is intentionally narrow in the current codebase: it checks basic structural consistency, while the requirements document captures the broader intended validation rules.

### `InputValidator`

```
InputValidator
  + validate(cadets: list[Cadet], jobs: list[Job], constraints: ConstraintIndex) -> ValidationResult
```

Current checks include:

- duplicate cadet personal numbers
- missing cadet names or personal numbers
- duplicate job names
- constraints object type sanity

### `ValidationResult`

```
ValidationResult
  - is_valid: bool
  - errors: list[str]
```

---

## 4. Scheduling Layer

### `ScheduleContext`

```
ScheduleContext
  - cadets: list[Cadet]
  - shifts: list[Shift]
  - constraint_index: ConstraintIndex
```

`build_context()` also injects team-level unavailabilities into the cadet list before the solver runs.

---

### `ShiftAssigner`

```
ShiftAssigner  (ABC)
  + assign(context: ScheduleContext) -> Schedule
```

This interface keeps the solver isolated from the orchestration and export code.

---

### `CpsatShiftAssigner`

```
CpsatShiftAssigner
  - t_rest_hours: float
  - rho: float
  + assign(context: ScheduleContext) -> Schedule
```

The current implementation creates a `SchedulingProblem`, solves it with OR-Tools CP-SAT, and writes the chosen cadets back into the shift objects.

---

### `SchedulingProblem`

```
SchedulingProblem
  - X[(cadet_idx, shift_idx)] -> BoolVar
  - Y[(cadet_idx, shift_idx_a, shift_idx_b)] -> BoolVar
  - W_max: IntVar
  + solve() -> (CpSolver, status)
```

The model enforces:

- exactly one cadet per shift
- cadet availability
- forbidden jobs
- overlap compatibility by job type
- consecutive compatibility by job type
- a minimax workload objective with close-shift penalties

The objective minimizes the maximum workload across cadets, where workload is encoded as `difficulty × duration + penalty`.

---

### `Schedule`

```
Schedule
  - assignments: list[Shift]
  + is_complete() -> bool
```

The schedule is considered complete when every shift has an assigned cadet.

---

## 5. Output Layer

### `ExcelExporter`

```
ExcelExporter
  + export(schedule: Schedule, cadets: list[Cadet], path: str)
```

Internal behavior:

- One worksheet per job type.
- Rows are job names.
- Columns are time slots.
- Cell values are cadet names.
- Cadet names are colored by team/platoon combination.
- A legend sheet is added automatically.
- If the output path does not end in `.xlsx`, a CSV fallback directory is written instead.

### `Evaluator`

```
Evaluator
  + evaluate(schedule: Schedule, cadets: list[Cadet], output_path: str) -> None
```

The evaluator writes development artifacts beside the schedule output:

- `cadet_stats.csv`
- `summary.json`
- difficulty, hours, and workload plots as PNG files

---

## 6. Orchestrator

### `ShiftSchedulerApp`

```
ShiftSchedulerApp
  + run(cadets_path: str, jobs_path: str, constraints_path: str, output_path: str)
```

Execution order:

1. Read cadets, jobs, and constraints.
2. Validate the parsed inputs.
3. Build a `ScheduleContext`.
4. Run `CpsatShiftAssigner.assign()`.
5. Export the workbook.
6. Generate evaluation artifacts.

---

## 7. Key Design Decisions

| Decision | Rationale |
|---|---|
| `TimeSlot` as a first-class object | Keeps date arithmetic centralized |
| Flat `list[Shift]` as solver input | Makes the CP-SAT model simple to index |
| `ConstraintIndex` built before solving | Fast compatibility checks during model construction |
| `CpsatShiftAssigner` behind an ABC | Keeps the solver swappable in the future |
| Separate `Evaluator` | Keeps diagnostics out of the core export path |

---

## 8. File Structure

```
shift_scheduler/
├── shift_scheduler.py          # CLI entry point
├── app.py                      # ShiftSchedulerApp orchestrator
├── domain/
│   ├── __init__.py
│   ├── time_slot.py            # TimeSlot
│   ├── cadet.py                # Cadet
│   ├── job.py                  # Job, Shift
│   └── constraints.py          # JobConstraint, TeamConstraint, ConstraintIndex
├── readers/
│   ├── __init__.py
│   ├── cadet_reader.py         # CadetCSVReader
│   ├── job_reader.py           # JobJSONReader
│   └── constraints_reader.py   # ConstraintsCSVReader
├── validation/
│   ├── __init__.py
│   └── validator.py            # InputValidator, ValidationResult
├── scheduling/
│   ├── __init__.py
│   ├── context.py              # ScheduleContext
│   ├── assigner.py             # ShiftAssigner, CpsatShiftAssigner
│   ├── solver.py               # SchedulingProblem
│   └── schedule.py             # Schedule
└── output/
    ├── __init__.py
    ├── evaluator.py            # Evaluator
    └── excel_exporter.py       # ExcelExporter
```
