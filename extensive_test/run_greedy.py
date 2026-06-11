import sys
sys.path.append('..')
from readers.cadet_reader import CadetCSVReader
from readers.job_reader import JobJSONReader
from readers.constraints_reader import ConstraintsCSVReader
from scheduling.context import build_context
from scheduling.assigner import GreedyShiftAssigner

cadets = CadetCSVReader.read("cadets.csv")
jobs = JobJSONReader.read("jobs.json")
constraints = ConstraintsCSVReader.read("job_constraints.csv")
context = build_context(cadets=cadets, jobs=jobs, constraint_index=constraints)

assigner = GreedyShiftAssigner()
try:
    assigner.assign(context)
    print("Greedy check passed: Feasible.")
except Exception as e:
    print(f"Greedy check failed: {e}")
