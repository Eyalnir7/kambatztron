# Kambatztron: Shift Scheduling Optimization Problem

## 1. Problem Description
The goal of Kambatztron is to assign a pool of military cadets to various battalion duties over a defined time horizon. The shift blocks are strictly fixed in time. The difficulty of each shift is dynamically evaluated based on its specific time block (e.g., night shifts are weighted heavier than day shifts). The primary objective is to distribute the workload fairly among cadets while strictly adhering to availability, constraints, and penalizing schedules that assign a cadet to non-consecutive but closely spaced shifts (e.g., inadequate rest time between shifts).

## 2. Mathematical Formulation

### 2.1 Sets and Indices
* $C$: Set of all available cadets, indexed by $c$.
* $S$: Set of all required shifts, indexed by $s$. A shift is defined by a job type, a fixed start time, and a fixed end time.

### 2.2 Parameters
* $D_s$: Dynamic difficulty/weight score of shift $s$.
* $L_s$: Duration (in hours) of shift $s$.
* $U_c$: Set of time slots where cadet $c$ is unavailable.
* $F_c$: Set of jobs that cadet $c$ is forbidden to perform.
* $M_{j1, j2}$: Boolean transition matrix; 1 if job $j2$ can immediately follow job $j1$, 0 otherwise.
* $T_{rest}$: Minimum desired rest gap (in hours) between two shifts.
* $\rho$: Penalty weight applied to a cadet's workload for violating the minimum rest gap.

### 2.3 Decision Variables
The main allocation variable is binary:
$$
X_{c, s} \in \{0, 1\}
$$
where $X_{c, s} = 1$ if cadet $c$ is assigned to shift $s$, and $0$ otherwise.

Auxiliary binary variables for close-shift penalties:
$$
Y_{c, s_1, s_2} \in \{0, 1\}
$$
where $Y_{c, s_1, s_2} = 1$ if cadet $c$ is assigned to both shift $s_1$ and $s_2$, and the time gap between them is strictly greater than 0 but less than $T_{rest}$.

Auxiliary continuous variable for the minimax objective:
$$
W_{max} \ge 0
$$

### 2.4 Constraints

**1. Shift Coverage (Hard):**
Every shift must be filled by the exact number of required cadets.
$$
\sum_{c \in C} X_{c, s} = 1 \quad \forall s \in S
$$

**2. Cadet Availability (Hard):**
A cadet cannot be assigned to a shift overlapping with their unavailable time slots.
$$
X_{c, s} = 0 \quad \forall c \in C, \forall s \in S \text{ where } s \cap U_c \neq \emptyset$$

**3. Forbidden Jobs (Hard):**
A cadet cannot be assigned to a job they are not qualified or allowed to do.
$$
X_{c, s} = 0 \quad \forall c \in C, \forall s \in S \text{ if job}(s) \in F_c
$$

**4. Non-Overlapping Shifts (Hard):**
A cadet cannot perform two shifts at the same time.
$$
X_{c, s_1} + X_{c, s_2} \le 1 \quad \forall c \in C, \forall (s_1, s_2) \text{ where } s_1 \cap s_2 \neq \emptyset
$$

**5. Consecutive Shift Constraints (Hard):**
If a cadet is assigned to shift $s_1$, they cannot be assigned to an immediately following shift $s_2$ unless allowed by the transition matrix $M$.
$$
X_{c, s_1} + X_{c, s_2} \le 1 \quad \forall c \in C, \forall (s_1, s_2) \text{ where } s_2 \text{ immediately follows } s_1 \text{ and } M_{\text{job}(s_1), \text{job}(s_2)} = 0
$$

**6. Close-Shift Penalty Trigger (Logical):**
For every pair of shifts $(s_1, s_2)$ where the gap is $0 < \text{start}(s_2) - \text{end}(s_1) < T_{rest}$:
$$
Y_{c, s_1, s_2} \ge X_{c, s_1} + X_{c, s_2} - 1 \quad \forall c \in C
$$

### 2.5 Optimization Objective
The objective is to minimize the maximum total workload score across all cadets, where the workload includes the base shift difficulty and any accrued penalties for inadequate rest.

Workload definition for cadet $c$:
$$
W_c = \sum_{s \in S} (X_{c, s} \cdot D_s \cdot L_s) + \rho \sum_{(s_1, s_2) \in E_{close}} Y_{c, s_1, s_2} \quad \forall c \in C
$$
*(where $E_{close}$ is the set of all shift pairs with a gap less than $T_{rest}$)*

Minimax constraint:
$$
W_{max} \ge W_c \quad \forall c \in C
$$

**Objective:**
$$
\min W_{max}
$$

---

## 3. Software Architecture: Main Object Design

The design uses Pydantic models to easily ingest data from a UI/Database and feed it into a solver-agnostic core object. Because difficulty is dynamic, `ShiftDef` explicitly expects it to be calculated and provided prior to solver initialization.

### 3.1 Data Models (Pydantic)

```python
from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Tuple
from datetime import datetime

class ShiftDef(BaseModel):
    id: str
    job_type: str
    start_time: datetime
    end_time: datetime
    difficulty: float  # Pre-calculated dynamically based on time of day
    required_cadets: int = 1

class CadetDef(BaseModel):
    id: str
    name: str
    unavailable_slots: List[Tuple[datetime, datetime]] = Field(default_factory=list)
    forbidden_jobs: List[str] = Field(default_factory=list)

class SchedulingRules(BaseModel):
    allow_consecutive: Dict[str, List[str]]  # e.g., {"cleaning": ["guarding"]}
    min_rest_gap_hours: float = 8.0          # Threshold for close-shift penalty
    close_shift_penalty_weight: float = 15.0 # How heavily to punish close shifts

```

### 3.2 The Core Problem Object

The `SchedulingProblem` class serves as the bridge between the UI and the solver. It translates the domain rules into constraint programming variables (e.g., for Google OR-Tools CP-SAT).

```python
class SchedulingProblem:
    def __init__(self, cadets: List[CadetDef], shifts: List[ShiftDef], rules: SchedulingRules):
        self.cadets = {c.id: c for c in cadets}
        self.shifts = {s.id: s for s in shifts}
        self.rules = rules

        # Internal storage for solver variables
        self._variables = {}
        self._hard_constraints = []

    def add_custom_constraint(self, constraint_logic):
        """
        Allows the UI to inject ad-hoc rules (e.g., 'Cadet X must not work with Cadet Y').
        """
        self._hard_constraints.append(constraint_logic)

    def _compile_cp_sat(self):
        """
        Translates the agnostic data into OR-Tools CP-SAT model.
        """
        from ortools.sat.python import cp_model
        model = cp_model.CpModel()

        x = {} # Main allocation variables: x[(c_id, s_id)]

        # 1. Initialize variables
        for c_id in self.cadets:
            for s_id in self.shifts:
                x[(c_id, s_id)] = model.NewBoolVar(f'assign_{c_id}_{s_id}')

        # 2. Add Hard Constraints
        # - Coverage
        # - Availability
        # - Forbidden Jobs
        # - Overlaps & Consecutive validity

        # 3. Formulate Soft Constraints (Close Shifts) & Objective
        workloads = []
        for c_id in self.cadets:
            base_workload = sum(
                x[(c_id, s_id)] * self.shifts[s_id].difficulty * self._duration(s_id)
                for s_id in self.shifts
            )

            # Identify close shift pairs for this cadet and formulate Y penalty variables
            penalty_vars = self._build_close_shift_penalties(model, x, c_id)
            total_penalty = sum(penalty_vars) * self.rules.close_shift_penalty_weight

            # Combine into total workload
            c_workload = model.NewIntVar(0, 10000, f'workload_{c_id}')
            model.Add(c_workload == base_workload + total_penalty)
            workloads.append(c_workload)

        # 4. Objective: Minimax
        w_max = model.NewIntVar(0, 10000, 'w_max')
        model.AddMaxEquality(w_max, workloads)
        model.Minimize(w_max)

        return model, x

    def _build_close_shift_penalties(self, model, x, c_id):
        # Implementation to find pairs of shifts with gap < rules.min_rest_gap_hours
        # and enforce Y >= X1 + X2 - 1
        pass

    def _duration(self, s_id: str) -> float:
        # Helper to calculate shift length in hours
        pass

    def solve(self, time_limit_seconds: int = 60) -> Dict[str, List[str]]:
        """
        Executes the optimization and maps the boolean variables back to domain structures.
        Returns: { "shift_id": ["cadet_id_1", "cadet_id_2"] }
        """
        model, x_vars = self._compile_cp_sat()

        from ortools.sat.python import cp_model
        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = time_limit_seconds
        status = solver.Solve(model)

        allocation = {s_id: [] for s_id in self.shifts}
        if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
            for (c_id, s_id), var in x_vars.items():
                if solver.Value(var) == 1:
                    allocation[s_id].append(c_id)

        return allocation
