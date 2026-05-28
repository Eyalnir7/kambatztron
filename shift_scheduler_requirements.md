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
- Personal number
- Unavailable hours
- Jobs they cannot take
- Gender
- Team
- Platoon

The MVP does not use gender, team, or platoon as scheduling constraints.

Team and platoon are used only for output visualization.

---

### 3.2 Job

A job is a specific duty that needs to be assigned to a cadet at one or more time slots.

Examples of job types from a previous use case:

- `guarding`
- `standby-team`
- `ceremony-guarding`
- `ceremony-missions`
- `cleaning`

The job types are not fixed and may change between different uses of the software.

Each job has:

- Job name
- Job type
- A set of time slots
- A difficulty score for each time slot

A job can require more than one cadet in reality, but for the MVP this should be modeled as multiple separate jobs. Therefore, each job/time-slot combination receives at most one cadet assignment.

---

### 3.3 Shift

A shift is a combination of:

- Job name
- Job type
- Time slot
- Difficulty score
- Assigned cadet

For example:

```text
Job name: Gate Guard 1
Job type: guarding
Time slot: 2026-06-01 08:00-12:00
Difficulty: 4
Assigned cadet: David Cohen
```

---

## 4. Time Slot Format

The project should use a single time slot format across all files.

Recommended format:

```text
YYYY-MM-DD HH:MM-YYYY-MM-DD HH:MM
```

Example:

```text
2026-06-01 08:00-2026-06-01 12:00
```

This format supports shifts that span multiple days.

For readability, a shorter display format may be used in the output if the start and end dates are the same, but the internal/input format should remain consistent.

### Validation

The software must validate that every time slot matches the agreed format.

---

## 5. Input Files

### 5.1 Cadets CSV

The cadets CSV contains one row per cadet.

The primary key is `personal_number`.

Suggested columns:

| Column | Description | Required |
|---|---|---|
| `personal_number` | Unique military ID / personal number | Yes |
| `name` | Cadet name | Yes |
| `unavailable_hours` | Time slots where the cadet cannot participate | Yes |
| `forbidden_jobs` | Jobs the cadet cannot take due to medical or other hard constraints | Yes |
| `gender` | Cadet gender | Yes |
| `team` | Cadet team | Yes |
| `platoon` | Cadet platoon | Yes |

### 5.1.1 Unavailable Hours Format

Unavailable hours should use the global time slot format:

```text
YYYY-MM-DD HH:MM-YYYY-MM-DD HH:MM
```

If a cadet has multiple unavailable ranges, they can be separated by a delimiter.

Proposed delimiter:

```text
;
```

Example:

```text
2026-06-01 08:00-2026-06-01 12:00;2026-06-02 00:00-2026-06-02 04:00
```

### 5.1.2 Forbidden Jobs Format

Forbidden jobs are hard constraints.

The jobs should be selected from a predefined list, not written as free text in the form.

In the CSV, multiple forbidden jobs can be separated by a delimiter.

Proposed delimiter:

```text
;
```

Example:

```text
Gate Guard 1;Kitchen Cleaning
```

---

### 5.2 Jobs JSON

The jobs JSON defines the jobs, their job types, their time slots, and their difficulty scores.

The keys are job names.

The values include:

- Job type
- Dictionary of time slots to difficulty scores

Example structure:

```json
{
  "Gate Guard 1": {
    "job_type": "guarding",
    "difficulty_by_time_slot": {
      "2026-06-01 08:00-2026-06-01 12:00": 4,
      "2026-06-01 12:00-2026-06-01 16:00": 5
    }
  },
  "Cleaning Hallway": {
    "job_type": "cleaning",
    "difficulty_by_time_slot": {
      "2026-06-01 08:00-2026-06-01 12:00": 2,
      "2026-06-01 12:00-2026-06-01 16:00": 3
    }
  }
}
```

### 5.2.1 Difficulty Scores

Difficulty scores are numeric.

For now, the scale is:

```text
1 = easiest
10 = hardest
```

The difficulty score reflects all general difficulty factors, including:

- Time of day
- Whether the job is pleasant or unpleasant
- Whether the job is done alone or with others
- Night/weekend/holiday difficulty
- Any other general difficulty consideration

The difficulty score is not personal to a specific cadet.

---

### 5.3 Job Constraints File

Some job types can overlap, and some jobs may be allowed to be consecutive.

These constraints should be specified in a separate file.

The exact format still needs to be finalized.

The file should support at least:

1. Which job types are compatible and may overlap.
2. Which job types are allowed to be consecutive.
3. Potentially, job-level compatibility rules if needed later.

Possible CSV structure:

| job_type_a | job_type_b | can_overlap | can_be_consecutive |
|---|---|---:|---:|
| guarding | cleaning | false | false |
| standby-team | ceremony-missions | true | true |
| guarding | guarding | false | false |

---

## 6. Hard Constraints

Hard constraints must always be enforced.

The MVP should enforce the following:

### 6.1 Cadet Availability

A cadet cannot be assigned to a shift that overlaps with one of their unavailable time ranges.

### 6.2 Forbidden Jobs

A cadet cannot be assigned to a job that appears in their forbidden jobs list.

### 6.3 No Overlapping Jobs

A cadet cannot be assigned to two jobs that overlap in time, unless those job types are explicitly marked as compatible in the job constraints file.

### 6.4 Consecutive Jobs

By default, a cadet cannot be assigned to two consecutive jobs.

Exception: consecutive assignment is allowed if the relevant job types are explicitly marked as allowed to be consecutive in the job constraints file.

### 6.5 One Cadet Per Job/Time Slot

Each job/time-slot combination should be assigned to at most one cadet.

If a real-world duty requires two cadets at the same time, it should be modeled as two separate jobs.

### 6.6 Every Shift Must Be Filled

For the MVP, every required job/time-slot combination must be assigned.

If no valid assignment exists, the software should return an error and print that no solution was found.

---

## 7. Fairness Objective

The fairness objective should balance the workload between individual cadets.

For the MVP, the solution does not need to be mathematically optimal.

A simple initial fairness score should be used and studied further later.

### 7.1 Proposed Workload Score

For each cadet, calculate a workload score based on:

- The difficulty scores of their assigned shifts
- The total number of hours assigned

Proposed formula:

```text
cadet_workload_score = geometric_mean(assigned_shift_difficulty_scores) * total_assigned_hours
```

Rationale:

- The geometric mean can summarize the difficulty of the assigned shifts.
- Multiplying by total assigned hours prevents the algorithm from ignoring how much total work a cadet received.

### 7.2 Fairness Goal

The algorithm should try to keep the cadet workload scores as balanced as possible between individuals.

Possible simple MVP objective:

```text
minimize max(cadet_workload_score) - min(cadet_workload_score)
```

or:

```text
minimize variance(cadet_workload_score)
```

The exact fairness objective should be studied and may change later.

---

## 8. Algorithm Requirements

The MVP algorithm should:

1. Load all input files.
2. Validate all data.
3. Build all required shifts from the jobs JSON.
4. Assign cadets to shifts while enforcing hard constraints.
5. Try to improve fairness between individuals.
6. Return an assignment if a valid solution is found.
7. Return an error if no valid solution is found.

The MVP does not need to guarantee the mathematically optimal solution.

A simple heuristic, greedy algorithm, backtracking algorithm, or local-search approach is acceptable.

Hard constraints must never be violated.

The algorithm does not need to be deterministic.

---

## 9. Output Requirements

The output should be a table-based schedule.

Preferred output format:

```text
Excel file (.xlsx)
```

The output should contain one table per job type.

All tables should be in the same Excel file.

Possible formats:

1. One worksheet per job type.
2. One worksheet containing multiple separated tables.
3. One worksheet per day, with tables grouped by job type.

Preferred MVP option:

```text
One worksheet per job type
```

### 9.1 Table Format

For each job type:

- Rows are job names.
- Columns are time slots.
- Cell values are assigned cadet names.

Example:

| Job name | 2026-06-01 08:00-12:00 | 2026-06-01 12:00-16:00 |
|---|---|---|
| Gate Guard 1 | David Cohen | Yossi Levi |
| Gate Guard 2 | Amit Mizrahi | Noa Bar |

### 9.2 Time Slot Consistency

All jobs of the same job type must have the same time slots.

This must be validated before solving.

### 9.3 Coloring

Cadet names in the output should be colored according to their team/platoon combination.

The exact color mapping can be generated automatically or configured later.

The output should show only cadet names, not personal numbers.

---

## 10. Validation Requirements

Before solving, the software should validate the input files.

Validation errors should stop the program.

Required validations:

### 10.1 Cadets CSV

- Every cadet has a personal number.
- Personal numbers are unique.
- Required columns exist.
- Unavailable hours use the global time slot format.
- Forbidden jobs are valid job names that exist in the jobs JSON.

### 10.2 Jobs JSON

- Every job has a job type.
- Every job has at least one time slot.
- Every time slot uses the global time slot format.
- Every difficulty score is numeric.
- Every difficulty score is in the range 1–10.
- Every required job/time-slot combination has a difficulty score.

### 10.3 Job Type Time Slot Consistency

For every job type:

- All jobs of that type must have the same set of time slots.

Example:

If `Gate Guard 1` and `Gate Guard 2` are both of type `guarding`, then they must have exactly the same time slots.

### 10.4 Job Constraints File

- Every job type referenced in the constraints file exists in the jobs JSON.
- Compatibility values are valid booleans.
- Consecutive-job values are valid booleans.
- The file should define behavior clearly enough to decide whether two assignments may overlap or be consecutive.

---

## 11. Command-Line Interface

The MVP should be run as a Python script.

Example command:

```bash
python shift_scheduler.py \
  --cadets cadets.csv \
  --jobs jobs.json \
  --constraints job_constraints.csv \
  --output schedule.xlsx
```

The script should:

1. Read the input files.
2. Validate them.
3. Attempt to solve the assignment.
4. Write the output file if successful.
5. Print an error if no valid solution is found.

---

## 12. Error Handling

The software should stop and return a clear error message if:

- An input file is missing.
- A required column is missing.
- A time slot has an invalid format.
- Personal numbers are duplicated.
- A forbidden job does not exist.
- A job type has inconsistent time slots.
- A difficulty score is missing.
- A difficulty score is not numeric or not in the range 1–10.
- A hard constraint makes the problem impossible to solve.
- No valid assignment is found.

---

## 13. Out of Scope for MVP

The following are intentionally out of scope for the MVP:

- Web app or desktop app.
- User login or permission levels.
- Manual editing of assignments inside the software.
- Locking certain assignments before solving.
- Preserving parts of a previous assignment.
- Historical memory of previous schedules.
- Previous workload from earlier weeks.
- Soldier rank, seniority, or command position.
- Personal preferences.
- Location handling.
- Summary statistics.
- Per-cadet workload reports.
- Security and privacy features beyond local file handling.
- Displaying personal numbers in the output.

---

## 14. Future Improvements

Possible future additions:

1. Web interface or app.
2. Input forms for cadets.
3. Job/time-slot editor.
4. Manual assignment locking.
5. Support for previous schedules and accumulated fairness over time.
6. More advanced optimization methods.
7. Configurable fairness formulas.
8. Per-cadet summary reports.
9. Warnings for uneven or suspicious assignments.
10. Export to multiple formats: Excel, HTML, PDF, CSV.
11. Permissions for commanders and other users.
12. Privacy/security handling for sensitive military data.
13. More detailed compatibility rules between specific jobs, not only job types.

---

## 15. Open Design Questions

These questions should be resolved before or during implementation:

1. What exact format should the job constraints file use?
2. Should job compatibility be defined only by job type, or also by specific job?
3. What exact fairness objective should be used first?
4. Should the Excel output use one sheet per job type or one sheet with all tables?
5. Should colors be assigned automatically by team/platoon, or configured manually?
6. Should unavailable hours support recurring rules, or only explicit date-time ranges?
7. Should the solver use a greedy heuristic, backtracking, local search, or a constraint solver library?
8. How should the system behave if there are multiple valid solutions with similar fairness?
9. Should the system print partial diagnostic information when no solution is found?
10. Should the input form generate exactly the same schema as the CSV expected by the script?

---

## 16. MVP Success Criteria

The MVP is successful if:

1. The user can provide cadets, jobs, and constraints as input files.
2. The system validates the files and catches common data errors.
3. The system creates a valid schedule when one exists.
4. The system never violates hard constraints.
5. The resulting schedule is reasonably fair between cadets.
6. The output is readable as Excel tables.
7. Cadet names are colored by team/platoon combination.
8. The script clearly reports failure when no valid assignment exists.
