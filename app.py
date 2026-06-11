"""Orchestrator for the shift scheduler MVP."""
from typing import List

from readers.cadet_reader import CadetCSVReader
from readers.job_reader import JobJSONReader
from readers.constraints_reader import ConstraintsCSVReader
from validation.validator import InputValidator
from scheduling.context import build_context
from scheduling.assigner import CpsatShiftAssigner
from output.excel_exporter import ExcelExporter
from output.evaluator import Evaluator


class ShiftSchedulerApp:
    def run(
        self,
        cadets_path: str,
        jobs_path: str,
        constraints_path: str,
        output_path: str,
        T_rest: float = 8.0,
        rho: float = 2.0,
    ) -> None:
        cadets = CadetCSVReader.read(cadets_path)
        jobs = JobJSONReader.read(jobs_path)
        constraints = ConstraintsCSVReader.read(constraints_path)

        result = InputValidator.validate(cadets=cadets, jobs=jobs, constraints=constraints)
        if not result.is_valid:
            raise ValueError("Validation failed: " + "; ".join(result.errors))

        context = build_context(cadets=cadets, jobs=jobs, constraint_index=constraints, T_rest=T_rest, rho=rho)

        assigner = CpsatShiftAssigner(t_rest_hours=8.0, rho=10.0)
        schedule = assigner.assign(context)

        exporter = ExcelExporter()
        exporter.export(schedule, cadets, output_path)

        # Run evaluation and write stats/plots next to output
        evaluator = Evaluator()
        evaluator.evaluate(schedule, cadets, output_path)
