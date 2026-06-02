"""CP-SAT Formulation for the Shift Scheduling Problem."""

from ortools.sat.python import cp_model
from typing import List, Dict, Tuple, Any

from domain.cadet import Cadet
from domain.job import Shift
from domain.constraints import ConstraintIndex


class SchedulingProblem:
    def __init__(
        self,
        cadets: List[Cadet],
        shifts: List[Shift],
        constraint_index: ConstraintIndex,
        t_rest_hours: float = 8.0,
        rho: float = 10.0,
    ):
        self.cadets = cadets
        self.shifts = shifts
        self.constraint_index = constraint_index
        self.t_rest_hours = t_rest_hours
        self.rho = rho

        self.model = cp_model.CpModel()
        
        # Scaling factor to convert floats to ints for CP-SAT
        self.SCALE = 100

        self._create_variables()
        self._add_constraints()
        self._set_objective()

    def _create_variables(self):
        self.X = {}
        for c_idx, cadet in enumerate(self.cadets):
            for s_idx, shift in enumerate(self.shifts):
                self.X[(c_idx, s_idx)] = self.model.NewBoolVar(f'X_c{c_idx}_s{s_idx}')

        self.Y = {}
        # Y[c, s1, s2] triggers if cadet c does s1 and s2 and gap < t_rest_hours
        for c_idx in range(len(self.cadets)):
            for s1_idx in range(len(self.shifts)):
                for s2_idx in range(len(self.shifts)):
                    if s1_idx != s2_idx:
                        s1 = self.shifts[s1_idx]
                        s2 = self.shifts[s2_idx]
                        
                        # Only consider pairs where s1 ends before s2 starts
                        if s1.time_slot.end <= s2.time_slot.start:
                            gap_hours = (s2.time_slot.start - s1.time_slot.end).total_seconds() / 3600.0
                            if 0 <= gap_hours < self.t_rest_hours:
                                self.Y[(c_idx, s1_idx, s2_idx)] = self.model.NewBoolVar(f'Y_c{c_idx}_s{s1_idx}_s{s2_idx}')

        # Minimax objective variable (max workload among all cadets)
        self.W_max = self.model.NewIntVar(0, 99999999, 'W_max')

    def _add_constraints(self):
        # 1. Shift Coverage (Hard): Every shift must be filled by exactly 1 cadet.
        for s_idx in range(len(self.shifts)):
            self.model.AddExactlyOne(self.X[(c_idx, s_idx)] for c_idx in range(len(self.cadets)))

        # 2 & 3. Cadet Availability & Forbidden Jobs (Hard)
        for c_idx, cadet in enumerate(self.cadets):
            for s_idx, shift in enumerate(self.shifts):
                if not cadet.is_available_during(shift.time_slot):
                    self.model.Add(self.X[(c_idx, s_idx)] == 0)
                if not cadet.can_take_job(shift.job.name):
                    self.model.Add(self.X[(c_idx, s_idx)] == 0)

        # 4. Unified Shift Compatibility Constraint (Hard)
        for c_idx in range(len(self.cadets)):
            for s1_idx in range(len(self.shifts)):
                for s2_idx in range(s1_idx + 1, len(self.shifts)):
                    s1 = self.shifts[s1_idx]
                    s2 = self.shifts[s2_idx]
                    
                    incompatible = False
                    if s1.time_slot.overlaps(s2.time_slot):
                        if not self.constraint_index.can_overlap(s1.job.job_type, s2.job.job_type):
                            incompatible = True
                    elif s1.time_slot.is_consecutive_with(s2.time_slot):
                        if not self.constraint_index.can_be_consecutive(s1.job.job_type, s2.job.job_type):
                            incompatible = True
                            
                    if incompatible:
                        self.model.Add(self.X[(c_idx, s1_idx)] + self.X[(c_idx, s2_idx)] <= 1)

        # 5. Close-Shift Penalty Trigger (Logical)
        for (c_idx, s1_idx, s2_idx), y_var in self.Y.items():
            # Y >= X_s1 + X_s2 - 1
            self.model.Add(y_var >= self.X[(c_idx, s1_idx)] + self.X[(c_idx, s2_idx)] - 1)

    def _set_objective(self):
        workloads = []
        rho_scaled = int(self.rho * self.SCALE)
        
        for c_idx in range(len(self.cadets)):
            w_c = 0
            
            # Base shift workload: sum(X * D_s * L_s)
            for s_idx, shift in enumerate(self.shifts):
                workload_scaled = int(shift.difficulty * shift.duration_hours * self.SCALE)
                w_c += self.X[(c_idx, s_idx)] * workload_scaled
                
            # Penalties: sum(Y * rho)
            for s1_idx in range(len(self.shifts)):
                for s2_idx in range(len(self.shifts)):
                    if (c_idx, s1_idx, s2_idx) in self.Y:
                        w_c += self.Y[(c_idx, s1_idx, s2_idx)] * rho_scaled
                        
            # W_max >= w_c
            self.model.Add(self.W_max >= w_c)
            
        self.model.Minimize(self.W_max)

    def solve(self) -> cp_model.CpSolver:
        solver = cp_model.CpSolver()
        # Optionally set time limit or other parameters here
        solver.parameters.max_time_in_seconds = 60.0
        
        status = solver.Solve(self.model)
        return solver, status
