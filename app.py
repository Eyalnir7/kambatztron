"""Orchestrator for the shift scheduler MVP."""
from typing import List

from readers.cadet_reader import CadetCSVReader
from readers.job_reader import JobJSONReader
from readers.constraints_reader import ConstraintsCSVReader
from validation.validator import InputValidator
from scheduling.context import build_context
from scheduling.assigner import GreedyShiftAssigner
from output.excel_exporter import ExcelExporter
from output.evaluator import Evaluator


class ShiftSchedulerApp:
    def run(self, cadets_path: str, jobs_path: str, constraints_path: str, output_path: str) -> None:
        cadets = CadetCSVReader.read(cadets_path)
        jobs = JobJSONReader.read(jobs_path)
        constraints = ConstraintsCSVReader.read(constraints_path)

        result = InputValidator.validate(cadets=cadets, jobs=jobs, constraints=constraints)
        if not result.is_valid:
            raise ValueError("Validation failed: " + "; ".join(result.errors))

        context = build_context(cadets=cadets, jobs=jobs, constraint_index=constraints)

        assigner = GreedyShiftAssigner()
        schedule = assigner.assign(context)

        exporter = ExcelExporter()
        exporter.export(schedule, cadets, output_path)

        # Run evaluation and write stats/plots next to output
        evaluator = Evaluator()
        evaluator.evaluate(schedule, cadets, output_path)
