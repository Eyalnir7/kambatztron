import os
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from domain.cadet import Cadet
from domain.job import Job
from domain.time_slot import TimeSlot
from domain.constraints import TeamConstraint, ConstraintIndex
from scheduling.context import build_context
from scheduling.assigner import CpsatShiftAssigner

app = FastAPI(title="Kambatztron API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Basic state for demo purposes (ideally this reads/writes from JSON/CSV)
STATE = {
    "cadets": [],
    "teams": ["Team 9", "Team 10", "Team 11", "Team 12"], # Predefined teams for choices
    "team_constraints": [],
    "jobs": [
        {"name": "Gate Guard 1", "type": "guarding"},
        {"name": "Kitchen Duty", "type": "cleaning"},
        {"name": "Patrol Alpha", "type": "patrol"}
    ],
    "shifts": []
}

@app.get("/api/cadets")
def get_cadets():
    return STATE["cadets"]

@app.post("/api/cadets")
def add_cadet(cadet: dict):
    STATE["cadets"].append(cadet)
    return cadet

@app.get("/api/teams")
def get_teams():
    # Extract unique teams from cadets + predefined teams
    teams = set(STATE["teams"])
    for c in STATE["cadets"]:
        if c.get("team"):
            teams.add(c["team"])
    return list(teams)

@app.post("/api/team_constraints")
def add_team_constraint(constraint: dict):
    STATE["team_constraints"].append(constraint)
    return constraint

@app.post("/api/cadet_constraints")
def add_cadet_constraint(constraint: dict):
    # payload: { personal_number: str, unavailable_slots: [{start, end}] }
    for c in STATE["cadets"]:
        if c.get("personal_number") == constraint["personal_number"]:
            if "unavailable_slots" not in c:
                c["unavailable_slots"] = []
            c["unavailable_slots"].extend(constraint["unavailable_slots"])
            break
    return constraint

@app.get("/api/jobs")
def get_jobs():
    return STATE["jobs"]

@app.post("/api/jobs")
def add_job(job: dict):
    STATE["jobs"].append(job)
    return job

@app.get("/api/shifts")
def get_shifts():
    return STATE["shifts"]

@app.post("/api/shifts")
def add_shift(shift: dict):
    STATE["shifts"].append(shift)
    return shift

@app.get("/api/team_constraints")
def get_team_constraints():
    return STATE["team_constraints"]

@app.post("/api/solve")
def solve_schedule():
    # 1. Build Jobs
    job_objects = []
    for j in STATE["jobs"]:
        diff_by_slot = {}
        for s in STATE["shifts"]:
            if s["job_name"] == j["name"]:
                try:
                    ts = TimeSlot.from_string(s["time_slot"])
                    diff_by_slot[ts] = s["difficulty"]
                except Exception as e:
                    print(f"Error parsing timeslot {s['time_slot']}: {e}")
        if diff_by_slot:
            job_objects.append(Job(name=j["name"], job_type=j["type"], difficulty_by_slot=diff_by_slot))

    # 2. Build Cadets
    cadet_objects = []
    for c in STATE["cadets"]:
        unavail = []
        for u in c.get("unavailable_slots", []):
            try:
                unavail.append(TimeSlot.parse(u["start"], u["end"]))
            except Exception as e:
                print(f"Error parsing cadet unavailable {u}: {e}")
        cadet_objects.append(Cadet(
            personal_number=c.get("personal_number", "unknown"),
            name=c.get("name", "unknown"),
            team=c.get("team", ""),
            forbidden_jobs=c.get("forbidden_jobs", []),
            unavailable_slots=unavail
        ))

    # 3. Build Team Constraints
    tc_objects = []
    for tc in STATE["team_constraints"]:
        unavail = []
        for u in tc.get("unavailable_slots", []):
            try:
                unavail.append(TimeSlot.parse(u["start"], u["end"]))
            except:
                pass
        tc_objects.append(TeamConstraint(team=tc["team"], unavailable_slots=unavail))
    
    constraint_index = ConstraintIndex(constraints=[], team_constraints=tc_objects)

    # 4. Solve
    context = build_context(cadets=cadet_objects, jobs=job_objects, constraint_index=constraint_index)
    assigner = CpsatShiftAssigner(t_rest_hours=8.0, rho=10.0)
    
    try:
        schedule = assigner.assign(context)
        result = []
        for shift in schedule:
            result.append({
                "job": shift.job.name,
                "time_slot": str(shift.time_slot),
                "cadet": shift.assigned_cadet.name if shift.assigned_cadet else "UNASSIGNED",
                "difficulty": shift.difficulty
            })
        return {"status": "success", "message": "Solver executed successfully", "schedule": result}
    except Exception as e:
        return {"status": "error", "message": str(e), "schedule": []}

# Mount the static UI
ui_dir = os.path.join(os.path.dirname(__file__), "..", "ui")
if os.path.exists(ui_dir):
    app.mount("/", StaticFiles(directory=ui_dir, html=True), name="ui")
