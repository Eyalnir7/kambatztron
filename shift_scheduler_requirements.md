# Shift Scheduler — MVP Requirements

## 1. Project Overview

**Project name:** Shift Scheduler

The project is a scheduling system for assigning shifts to cadets in a battalion.

The shifts are mostly guarding shifts, usually around 4 hours long, but may also include cleaning shifts, standby-team shifts, ceremony-guarding, ceremony-missions, and other job types. The exact job types can change between different uses of the software.

The main goal is to assign cadets to jobs and time slots while enforcing hard constraints and trying to keep the distribution of work fair between individuals.

For the MVP, the system will be implemented as a Python script that receives input files as command-line arguments and outputs the resulting schedule as an Excel file.

---

## 2. Main Goals

The MVP should:

1. Read cadet availability and restrictions from a CSV file.
2. Read job definitions, time slots, and difficulty scores from a JSON file.
3. Read job compatibility and consecutive-job constraints from an additional constraints file.
4. Validate the input data before attempting to solve the schedule.
5. Assign cadets to shifts while enforcing all hard constraints.
6. Try to produce a fair distribution of work between individual cadets.
7. Output the assignment as tables, preferably in Excel format.
8. Color cadet names in the output according to their team/platoon combination.

---

## 3. Core Concepts

### 3.1 Cadet

A cadet is a person who may be assigned to shifts.

Each cadet is identified by a unique **personal number**, which is the primary key in the cadet CSV file.

Each cadet has:

- Name
# Shift Scheduler — Current Behavior

This document tracks the behavior implemented in the repository today, not the earlier aspirational MVP wording.

## 1. Project Overview

The project is a Python scheduling system for assigning cadets to battalion duties. The current implementation reads cadets, jobs, and job-compatibility rules from files, validates the inputs, solves the assignment with OR-Tools CP-SAT, exports a workbook, and writes evaluation outputs next to the result.

## 2. Core Concepts

### 2.1 Cadet

A cadet is represented by the `Cadet` model in [domain/cadet.py](domain/cadet.py). The current model stores:

- `personal_number`
- `name`
- `unavailable_slots`
- `forbidden_jobs`
- `forbidden_job_names`
- `gender`
- `team`
- `platoon`

`team` and `platoon` are used for workbook coloring and evaluation grouping. They are not currently part of solver constraints.

### 2.2 Job

A job is represented by the `Job` model in [domain/job.py](domain/job.py). Each job has:

- `name`
- `job_type`
- `difficulty_by_slot`

Each key in `difficulty_by_slot` is a `TimeSlot`.

### 2.3 Shift

The assignable unit is the `Shift` model in [domain/job.py](domain/job.py). A shift contains:

- `job`
- `time_slot`
- `difficulty`
- `assigned_cadet`

The solver operates on flattened shifts built from the jobs JSON.

### 2.4 Time Slot

The shared time-slot format is `YYYY-MM-DD HH:MM-YYYY-MM-DD HH:MM`. Parsing and overlap checks live in [domain/time_slot.py](domain/time_slot.py).

## 3. Input Files

### 3.1 Cadets CSV

The reader in [readers/cadet_reader.py](readers/cadet_reader.py) currently requires these columns:

| Column | Description |
|---|---|
| `personal_number` | Unique cadet identifier |
| `name` | Cadet name |
| `unavailable_hours` | Semicolon-separated unavailable time slots |
| `forbidden_jobs` | Semicolon-separated forbidden job names |
| `gender` | Cadet gender |
| `team` | Cadet team |
| `platoon` | Cadet platoon |

An optional `forbidden_job_names` column is also accepted and stored separately on the model.

### 3.2 Jobs JSON

The reader in [readers/job_reader.py](readers/job_reader.py) expects a JSON object keyed by job name. Each job entry must contain:

- `job_type`
- `difficulty_by_time_slot`

Each time-slot entry must parse through `TimeSlot.from_string()` and each difficulty must be numeric and within `1` to `10`.

### 3.3 Constraints CSV

The reader in [readers/constraints_reader.py](readers/constraints_reader.py) expects:

| Column | Description |
|---|---|
| `job_type_a` | First job type |
| `job_type_b` | Second job type |
| `can_overlap` | Whether the pair may overlap |
| `can_be_consecutive` | Whether the pair may be consecutive |

The reader builds a bidirectional `ConstraintIndex` in [domain/constraints.py](domain/constraints.py). If a pair is not present, the current default is incompatible.

## 4. Validation Layer

`InputValidator` in [validation/validator.py](validation/validator.py) currently checks:

- duplicate cadet personal numbers
- missing cadet personal numbers or names
- duplicate job names
- that jobs were provided
- that the constraints argument is a `ConstraintIndex`

The parser layers already fail on missing files, malformed CSV/JSON, invalid time slots, and invalid difficulty ranges.

## 5. Scheduling Layer

`build_context()` in [scheduling/context.py](scheduling/context.py) flattens jobs into shifts and builds the solver inputs:

- `shift_ids`
- `D` for shift difficulty
- `L` for shift duration
- `R` for required cadets per shift
- `Q` for overlap/consecutive compatibility
- `E_close` for shift pairs with a positive rest gap smaller than `T_rest`

The current orchestrator in [app.py](app.py) uses `CpsatShiftAssigner` from [scheduling/assigner.py](scheduling/assigner.py). A `GreedyShiftAssigner` implementation also exists in the same module, but it is not the default path.

`WorkloadTracker` in [scheduling/workload.py](scheduling/workload.py) computes the evaluation-style workload score as geometric mean of assigned difficulties multiplied by total assigned hours.

## 6. Output

`ExcelExporter` in [output/excel_exporter.py](output/excel_exporter.py) writes one worksheet per job type when the output path ends in `.xlsx`. It also writes a `Legend` sheet that maps team/platoon combinations to colors.

If the output path does not end in `.xlsx`, the exporter falls back to a CSV directory layout.

`Evaluator` in [output/evaluator.py](output/evaluator.py) writes an `evaluation/` folder with per-cadet stats, a JSON summary, and several plots.

## 7. CLI

The current CLI in [shift_scheduler.py](shift_scheduler.py) accepts:

- `--cadets`
- `--jobs`
- `--constraints`
- `--output`
- `--t-rest`
- `--rho`

Example:

```bash
python shift_scheduler.py \
  --cadets cadets.csv \
  --jobs jobs.json \
  --constraints job_constraints.csv \
  --output schedule.xlsx
```

## 8. Implementation Notes

- The repository keeps the domain models in `domain/`, readers in `readers/`, scheduling logic in `scheduling/`, validation in `validation/`, and exports in `output/`.
- The current code path is exact/constraint-solver based, not greedy by default.
- The codebase currently treats several earlier design ideas as future work rather than enforced behavior.

