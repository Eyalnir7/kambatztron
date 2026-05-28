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
  + is_consecutive_with(other: TimeSlot) -> bool
```
A first-class object so that overlap/consecutive logic lives in one place,
not scattered across readers and the solver.

---

### `Cadet`
```
Cadet
  - personal_number: str        # primary key
  - name: str
  - unavailable_slots: list[TimeSlot]
  - forbidden_jobs: list[str]
  - gender: str
  - team: str
  - platoon: str
```

---

### `Job`
```
Job
  - name: str
  - job_type: str
  - difficulty_by_slot: dict[TimeSlot, float]
```

---

### `Shift`  _(the assignable unit — a Job × TimeSlot pair)_
```
Shift
  - job: Job
  - time_slot: TimeSlot
  - difficulty: float
  - assigned_cadet: Cadet | None
```

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

## 2. Input Layer

One reader class per file type, each returning domain objects.

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
  + read(path: str) -> list[JobConstraint]
```

---

## 3. Validation Layer

Receives all parsed data and runs every check defined in the requirements.
Separated from parsing so both layers stay focused and independently testable.

### `InputValidator`
```
InputValidator
  + validate(
      cadets: list[Cadet],
      jobs: list[Job],
      constraints: list[JobConstraint]
    ) -> ValidationResult

  # Internal checks:
  - _validate_cadets()              # unique personal numbers, required fields, time slot format
  - _validate_jobs()                # job types present, time slot format, difficulty range 1–10
  - _validate_constraints()         # referenced job types exist, boolean values valid
  - _validate_cross_references()    # forbidden jobs exist in jobs JSON,
                                    # time slot consistency per job type
```

### `ValidationResult`
```
ValidationResult
  - is_valid: bool
  - errors: list[str]
```

---

## 4. Scheduling Layer

### `ScheduleContext`
A single bag of everything the solver needs — built once after validation passes.
```
ScheduleContext
  - cadets: list[Cadet]
  - shifts: list[Shift]            # flattened from all jobs × time slots
  - constraint_index: ConstraintIndex
```

### `ConstraintIndex`
Pre-built lookup tables for fast O(1) queries during the assignment loop.
```
ConstraintIndex
  - cadet_by_id: dict[str, Cadet]
  - constraint_by_type_pair: dict[tuple[str, str], JobConstraint]
  + can_overlap(type_a: str, type_b: str) -> bool
  + can_be_consecutive(type_a: str, type_b: str) -> bool
```

### `ShiftAssigner`  _(abstract base)_
Defines the solver interface. Swap implementations without touching anything else.
```
ShiftAssigner  (ABC)
  + assign(context: ScheduleContext) -> Schedule
```

### `GreedyShiftAssigner(ShiftAssigner)`  _(MVP implementation)_
```
GreedyShiftAssigner
  - workload_tracker: WorkloadTracker
  + assign(context: ScheduleContext) -> Schedule

  # Internal helpers:
  - _get_eligible_cadets(shift, assigned_so_far) -> list[Cadet]
  - _check_availability(cadet, shift) -> bool
  - _check_forbidden(cadet, shift) -> bool
  - _check_no_overlap(cadet, shift, assigned_so_far) -> bool
  - _check_not_consecutive(cadet, shift, assigned_so_far) -> bool
```

### `WorkloadTracker`
Maintains workload scores and selects the least-loaded eligible cadet.
```
WorkloadTracker
  - scores: dict[Cadet, float]
  + update(cadet: Cadet, shift: Shift)
  + get_score(cadet: Cadet) -> float
  + least_loaded(candidates: list[Cadet]) -> Cadet

  # Workload formula (per requirements §7.1):
  # score = geometric_mean(assigned_difficulties) × total_assigned_hours
```

### `Schedule`
The output of the solver — a list of fully assigned shifts.
```
Schedule
  - assignments: list[Shift]     # all shifts, assigned_cadet filled in
  + is_complete() -> bool        # True if every shift has an assigned cadet
```

---

## 5. Output Layer

### `ExcelExporter`
```
ExcelExporter
  + export(schedule: Schedule, cadets: list[Cadet], path: str)

  # Internal helpers:
  - _build_color_map(cadets: list[Cadet]) -> dict[tuple[str, str], str]
    # maps (team, platoon) → hex color string; generated automatically
  - _write_job_type_sheet(workbook, job_type: str, shifts: list[Shift])
    # rows = job names, columns = time slots, cells = cadet names (colored)
```

Output layout (per requirements §9):
- One worksheet per job type.
- Rows = job names.
- Columns = time slots.
- Cell values = assigned cadet name, colored by team × platoon.

---

## 6. Orchestrator

The script entry point — thin glue that calls each stage in order.

```
ShiftSchedulerApp
  + run(
      cadets_path: str,
      jobs_path: str,
      constraints_path: str,
      output_path: str
    )

  # Execution order:
  # 1. Read all input files via the three readers.
  # 2. Run InputValidator; abort with error messages on failure.
  # 3. Build ScheduleContext (flatten jobs → shifts, build ConstraintIndex).
  # 4. Run ShiftAssigner.assign(); abort if no solution found.
  # 5. Run ExcelExporter.export().
```

CLI usage (per requirements §11):
```bash
python shift_scheduler.py \
  --cadets cadets.csv \
  --jobs jobs.json \
  --constraints job_constraints.csv \
  --output schedule.xlsx
```

---

## 7. Key Design Decisions

| Decision | Rationale |
|---|---|
| `TimeSlot` as a first-class object | Overlap and consecutive logic lives in one place, not scattered |
| Flat `list[Shift]` as solver input | Decouples job structure from assignment logic |
| `ConstraintIndex` pre-built before solving | O(1) lookups during the hot assignment loop |
| Abstract `ShiftAssigner` | Trivial to swap greedy MVP for CP-SAT or local search later |
| Validation as a separate class | Readers stay simple; all cross-file checks are in one auditable place |
| `WorkloadTracker` as a separate class | Fairness logic is isolated and easy to swap out (§7.2 notes the formula may change) |

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
│   └── constraints.py          # JobConstraint, ConstraintIndex
├── io/
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
│   ├── assigner.py             # ShiftAssigner (ABC), GreedyShiftAssigner
│   ├── workload.py             # WorkloadTracker
│   └── schedule.py             # Schedule
└── output/
    ├── __init__.py
    └── excel_exporter.py       # ExcelExporter
```
