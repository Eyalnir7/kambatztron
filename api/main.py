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
    "job_constraints": [
        {
            "job_type_a": "dynamic guarding",
            "job_type_b": "jobs at the base",
            "can_overlap": True,
            "can_be_consecutive": True
        },
        {
            "job_type_a": "dynamic guarding",
            "job_type_b": "dynamic guarding",
            "can_overlap": False,
            "can_be_consecutive": True
        },
        {
            "job_type_a": "jobs at the base",
            "job_type_b": "jobs at the base",
            "can_overlap": False,
            "can_be_consecutive": True
        }
    ],
    "jobs": [
        {"name": "cafcaf_a", "type": "dynamic guarding"},
        {"name": "cafcaf_b", "type": "dynamic guarding"},
        {"name": "abas", "type": "jobs at the base"},
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

@app.post("/api/cadet_constraints")
def add_cadet_constraint(constraint: dict):
    pn = constraint.get("personal_number")
    slots = constraint.get("unavailable_slots", [])
    for c in STATE["cadets"]:
        if c.get("personal_number") == pn:
            c.setdefault("unavailable_slots", []).extend(slots)
            return {"status": "success", "cadet": c}
    return {"status": "error", "message": "Cadet not found"}

@app.delete("/api/cadets/{pn}/constraints/{start}/{end}")
def delete_cadet_constraint(pn: str, start: str, end: str):
    for c in STATE["cadets"]:
        if c.get("personal_number") == pn:
            if "unavailable_slots" in c:
                c["unavailable_slots"] = [
                    s for s in c["unavailable_slots"] 
                    if not (s.get("start") == start and s.get("end") == end)
                ]
            return {"status": "success"}
    return {"status": "error", "message": "Cadet not found"}

@app.post("/api/cadet_forbidden_jobs")
def update_cadet_forbidden_jobs(payload: dict):
    pn = payload.get("personal_number")
    jobs_to_add = payload.get("forbidden_jobs", [])
    for c in STATE["cadets"]:
        if c.get("personal_number") == pn:
            if "forbidden_jobs" not in c:
                c["forbidden_jobs"] = []
            # Merge without duplicates
            for j in jobs_to_add:
                if j not in c["forbidden_jobs"]:
                    c["forbidden_jobs"].append(j)
            return {"status": "success", "cadet": c}
    return {"status": "error", "message": "Cadet not found"}

@app.delete("/api/cadets/{pn}")
def delete_cadet(pn: str):
    STATE["cadets"] = [c for c in STATE["cadets"] if c.get("personal_number") != pn]
    return {"status": "success"}

@app.delete("/api/cadets/{pn}/forbidden_jobs/{job_name}")
def delete_cadet_forbidden_job(pn: str, job_name: str):
    for c in STATE["cadets"]:
        if c.get("personal_number") == pn:
            if "forbidden_jobs" in c and job_name in c["forbidden_jobs"]:
                c["forbidden_jobs"].remove(job_name)
            return {"status": "success"}
    return {"status": "error", "message": "Cadet not found"}

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

@app.delete("/api/team_constraints/{index}")
def delete_team_constraint(index: int):
    if 0 <= index < len(STATE["team_constraints"]):
        STATE["team_constraints"].pop(index)
        return {"status": "success"}
    return {"status": "error", "message": "Index out of range"}

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

@app.delete("/api/jobs/{name}")
def delete_job(name: str):
    STATE["jobs"] = [j for j in STATE["jobs"] if j.get("name") != name]
    # Cascade delete shifts
    STATE["shifts"] = [s for s in STATE["shifts"] if s.get("job_name") != name]
    return {"status": "success"}

@app.get("/api/shifts")
def get_shifts():
    return STATE["shifts"]

@app.post("/api/shifts")
def add_shift(shift: dict):
    STATE["shifts"].append(shift)
    return shift

@app.delete("/api/shifts/{index}")
def delete_shift(index: int):
    if 0 <= index < len(STATE["shifts"]):
        STATE["shifts"].pop(index)
        return {"status": "success"}
    return {"status": "error", "message": "Index out of range"}

@app.get("/api/team_constraints")
def get_team_constraints():
    return STATE["team_constraints"]

@app.get("/api/job_constraints")
def get_job_constraints():
    return STATE["job_constraints"]

@app.post("/api/job_constraints")
def add_job_constraint(constraint: dict):
    STATE["job_constraints"].append(constraint)
    return constraint

@app.delete("/api/job_constraints/{type_a}/{type_b}")
def delete_job_constraint(type_a: str, type_b: str):
    STATE["job_constraints"] = [
        jc for jc in STATE["job_constraints"]
        if not (jc.get("job_type_a") == type_a and jc.get("job_type_b") == type_b) and
           not (jc.get("job_type_a") == type_b and jc.get("job_type_b") == type_a)
    ]
    return {"status": "success"}

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
    
    # 4. Build Job Constraints
    from domain.constraints import JobConstraint
    jc_objects = []
    for jc in STATE["job_constraints"]:
        jc_objects.append(JobConstraint(
            job_type_a=jc["job_type_a"],
            job_type_b=jc["job_type_b"],
            can_overlap=jc["can_overlap"],
            can_be_consecutive=jc["can_be_consecutive"]
        ))

    constraint_index = ConstraintIndex(constraints=jc_objects, team_constraints=tc_objects)

    # 5. Solve
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
