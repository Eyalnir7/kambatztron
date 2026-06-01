# Kambatztron: Shift Scheduling Optimization Problem

## 1. Problem Description
The goal of Kambatztron is to assign a pool of military cadets to various battalion duties over a defined time horizon. The shift blocks are strictly fixed in time. The difficulty of each shift is dynamically evaluated based on its specific time block (e.g., night shifts are weighted heavier than day shifts). The primary objective is to distribute the workload fairly among cadets while strictly adhering to availability, a unified shift compatibility matrix, and penalizing schedules with inadequate rest time between shifts.

## 2. Mathematical Formulation

### 2.1 Sets and Indices
* $C$: Set of all available cadets, indexed by $c$.
* $S$: Set of all required shifts, indexed by $s$. A shift is defined by a job type, a fixed start time, and a fixed end time.

### 2.2 Parameters
* $D_s$: Dynamic difficulty/weight score of shift $s$.
* $L_s$: Duration (in hours) of shift $s$.
* $R_s$: Number of cadets required for shift $s$.
* $U_c$: Set of time slots where cadet $c$ is unavailable.
* $F_c$: Set of jobs that cadet $c$ is forbidden to perform.
* $Q_{s_1, s_2}$: A quadratic binary compatibility matrix of size $|S| \times |S|$. $Q_{s_1, s_2} = 1$ if a single cadet is allowed to perform both shift $s_1$ and shift $s_2$ (covering both overlapping and consecutive shift logic). $Q_{s_1, s_2} = 0$ if performing both is forbidden.
* $T_{rest}$: Minimum desired rest gap (in hours) between two shifts.
* $\rho$: Penalty weight applied to a cadet's workload for violating the minimum rest gap.

### 2.3 Decision Variables
The main allocation variable is binary:
\[ X_{c, s} \in \{0, 1\} \]
where $X_{c, s} = 1$ if cadet $c$ is assigned to shift $s$, and $0$ otherwise.

Auxiliary binary variables for close-shift penalties:
\[ Y_{c, s_1, s_2} \in \{0, 1\} \]
where $Y_{c, s_1, s_2} = 1$ if cadet $c$ is assigned to both shift $s_1$ and $s_2$, and the time gap between them is strictly greater than 0 but less than $T_{rest}$.

Auxiliary continuous variable for the minimax objective:
\[ W_{max} \ge 0 \]

### 2.4 Constraints

**1. Shift Coverage (Hard):**
Every shift must be filled by the exact number of required cadets.
\[ \sum_{c \in C} X_{c, s} = R_s \quad \forall s \in S \]

**2. Cadet Availability (Hard):**
A cadet cannot be assigned to a shift overlapping with their unavailable time slots.
\[ X_{c, s} = 0 \quad \forall c \in C, \forall s \in S \text{ where } s \cap U_c \neq \emptyset \]

**3. Forbidden Jobs (Hard):**
A cadet cannot be assigned to a job they are not qualified or allowed to do.
\[ X_{c, s} = 0 \quad \forall c \in C, \forall s \in S \text{ if job}(s) \in F_c \]

**4. Unified Shift Compatibility Constraint (Hard):**
This replaces the previous non-overlapping and consecutive constraints. A cadet cannot be assigned to any pair of shifts that are deemed incompatible by the quadratic binary matrix $Q$. This allows for concurrent or consecutive shifts *only* if explicitly permitted by the matrix.
\[ X_{c, s_1} + X_{c, s_2} \le 1 \quad \forall c \in C, \forall (s_1, s_2) \text{ where } Q_{s_1, s_2} = 0 \]

**5. Close-Shift Penalty Trigger (Logical):**
For every pair of compatible shifts $(s_1, s_2)$ where the gap is $0 < \text{start}(s_2) - \text{end}(s_1) < T_{rest}$:
\[ Y_{c, s_1, s_2} \ge X_{c, s_1} + X_{c, s_2} - 1 \quad \forall c \in C \]

### 2.5 Optimization Objective
The objective is to minimize the maximum total workload score across all cadets, where the workload includes the base shift difficulty and any accrued penalties for inadequate rest.

Workload definition for cadet $c$:
\[ W_c = \sum_{s \in S} (X_{c, s} \cdot D_s \cdot L_s) + \rho \sum_{(s_1, s_2) \in E_{close}} Y_{c, s_1, s_2} \quad \forall c \in C \]
*(where $E_{close}$ is the set of all shift pairs with a gap less than $T_{rest}$)*

Minimax constraint:
\[ W_{max} \ge W_c \quad \forall c \in C \]

**Objective:**
\[ \min W_{max} \]