"""Manager-only routes: roster, jobs/shifts, constraints, and triggering solves."""
import csv
import io
import json
import os
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy.orm import Session

from db.session import get_session
from db.models import (
    CadetAccount,
    CadetUnavailableSlot,
    CadetForbiddenJob,
    Job,
    ShiftDefinition,
    JobConstraintRow,
    TeamConstraintSlot,
    ScheduleRun,
)
from domain.time_slot import TimeSlot
from validation.validator import InputValidator
from scheduling.context import build_context
from scheduling.assigner import CpsatShiftAssigner
from output.excel_exporter import ExcelExporter
from output.evaluator import Evaluator

from api.deps import require_manager
from api.adapters import build_cadets, build_jobs, build_constraint_index

RUNS_DIR = Path(os.environ.get("RUNS_DIR", "./runs"))

router = APIRouter(prefix="/api/manager", tags=["manager"], dependencies=[Depends(require_manager)])


# ---- Roster ----

class CadetIn(BaseModel):
    personal_number: str
    name: str
    gender: str = ""
    team: str = ""
    platoon: str = ""


class CadetOut(CadetIn):
    unavailable_slots: List[str] = []
    forbidden_jobs: List[str] = []


def _cadet_out(row: CadetAccount) -> CadetOut:
    return CadetOut(
        personal_number=row.personal_number,
        name=row.name,
        gender=row.gender,
        team=row.team,
        platoon=row.platoon,
        unavailable_slots=[f"{s.start.isoformat()}/{s.end.isoformat()}" for s in row.unavailable_slots],
        forbidden_jobs=[f.job_name for f in row.forbidden_jobs],
    )


@router.get("/cadets", response_model=List[CadetOut])
def list_cadets(session: Session = Depends(get_session)):
    return [_cadet_out(c) for c in session.query(CadetAccount).all()]


@router.post("/cadets", response_model=CadetOut)
def add_cadet(body: CadetIn, session: Session = Depends(get_session)):
    if session.query(CadetAccount).filter_by(personal_number=body.personal_number).first():
        raise HTTPException(status_code=409, detail="A cadet with that personal_number already exists")
    row = CadetAccount(**body.model_dump())
    session.add(row)
    session.commit()
    return _cadet_out(row)


@router.delete("/cadets/{personal_number}")
def delete_cadet(personal_number: str, session: Session = Depends(get_session)):
    row = session.query(CadetAccount).filter_by(personal_number=personal_number).first()
    if row is None:
        raise HTTPException(status_code=404, detail="Cadet not found")
    session.delete(row)
    session.commit()
    return {"status": "deleted"}


@router.post("/cadets/import-csv")
async def import_cadets_csv(file: UploadFile, session: Session = Depends(get_session)):
    """Bulk-import a roster CSV with the same columns the CLI reader expects:
    personal_number, name, unavailable_hours, forbidden_jobs, gender, team, platoon.
    """
    text = (await file.read()).decode("utf-8")
    reader = csv.DictReader(io.StringIO(text))
    created = 0
    for row in reader:
        personal_number = (row.get("personal_number") or "").strip()
        if not personal_number:
            continue
        existing = session.query(CadetAccount).filter_by(personal_number=personal_number).first()
        if existing is not None:
            continue
        cadet = CadetAccount(
            personal_number=personal_number,
            name=(row.get("name") or "").strip(),
            gender=(row.get("gender") or "").strip(),
            team=(row.get("team") or "").strip(),
            platoon=(row.get("platoon") or "").strip(),
        )
        session.add(cadet)
        session.flush()

        for slot_str in (row.get("unavailable_hours") or "").split(";"):
            slot_str = slot_str.strip()
            if slot_str:
                slot = TimeSlot.from_string(slot_str)
                session.add(CadetUnavailableSlot(cadet_id=cadet.id, start=slot.start, end=slot.end))

        for job_name in (row.get("forbidden_jobs") or "").split(";"):
            job_name = job_name.strip()
            if job_name:
                session.add(CadetForbiddenJob(cadet_id=cadet.id, job_name=job_name))

        created += 1
    session.commit()
    return {"created": created}


# ---- Jobs & shifts ----

class ShiftIn(BaseModel):
    start: datetime
    end: datetime
    difficulty: float


class JobIn(BaseModel):
    name: str
    job_type: str


class JobOut(JobIn):
    shifts: List[ShiftIn] = []


@router.get("/jobs", response_model=List[JobOut])
def list_jobs(session: Session = Depends(get_session)):
    return [
        JobOut(
            name=j.name,
            job_type=j.job_type,
            shifts=[ShiftIn(start=s.start, end=s.end, difficulty=s.difficulty) for s in j.shifts],
        )
        for j in session.query(Job).all()
    ]


@router.post("/jobs", response_model=JobOut)
def add_job(body: JobIn, session: Session = Depends(get_session)):
    if session.query(Job).filter_by(name=body.name).first():
        raise HTTPException(status_code=409, detail="A job with that name already exists")
    row = Job(name=body.name, job_type=body.job_type)
    session.add(row)
    session.commit()
    return JobOut(name=row.name, job_type=row.job_type, shifts=[])


@router.delete("/jobs/{name}")
def delete_job(name: str, session: Session = Depends(get_session)):
    row = session.query(Job).filter_by(name=name).first()
    if row is None:
        raise HTTPException(status_code=404, detail="Job not found")
    session.delete(row)
    session.commit()
    return {"status": "deleted"}


@router.post("/jobs/{name}/shifts")
def add_shift(name: str, body: ShiftIn, session: Session = Depends(get_session)):
    job = session.query(Job).filter_by(name=name).first()
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    if not (1 <= body.difficulty <= 10):
        raise HTTPException(status_code=422, detail="difficulty must be between 1 and 10")
    session.add(ShiftDefinition(job_id=job.id, start=body.start, end=body.end, difficulty=body.difficulty))
    session.commit()
    return {"status": "created"}


# ---- Constraints ----

class JobConstraintIn(BaseModel):
    job_type_a: str
    job_type_b: str
    can_overlap: bool
    can_be_consecutive: bool


@router.get("/job-constraints", response_model=List[JobConstraintIn])
def list_job_constraints(session: Session = Depends(get_session)):
    return [
        JobConstraintIn(
            job_type_a=r.job_type_a, job_type_b=r.job_type_b,
            can_overlap=r.can_overlap, can_be_consecutive=r.can_be_consecutive,
        )
        for r in session.query(JobConstraintRow).all()
    ]


@router.post("/job-constraints", response_model=JobConstraintIn)
def add_job_constraint(body: JobConstraintIn, session: Session = Depends(get_session)):
    session.add(JobConstraintRow(**body.model_dump()))
    session.commit()
    return body


@router.delete("/job-constraints/{job_type_a}/{job_type_b}")
def delete_job_constraint(job_type_a: str, job_type_b: str, session: Session = Depends(get_session)):
    row = session.query(JobConstraintRow).filter_by(job_type_a=job_type_a, job_type_b=job_type_b).first()
    if row is None:
        raise HTTPException(status_code=404, detail="Constraint not found")
    session.delete(row)
    session.commit()
    return {"status": "deleted"}


class TeamConstraintSlotIn(BaseModel):
    team: str
    start: datetime
    end: datetime


@router.get("/team-constraints", response_model=List[TeamConstraintSlotIn])
def list_team_constraints(session: Session = Depends(get_session)):
    return [
        TeamConstraintSlotIn(team=r.team, start=r.start, end=r.end)
        for r in session.query(TeamConstraintSlot).all()
    ]


@router.post("/team-constraints", response_model=TeamConstraintSlotIn)
def add_team_constraint(body: TeamConstraintSlotIn, session: Session = Depends(get_session)):
    session.add(TeamConstraintSlot(**body.model_dump()))
    session.commit()
    return body


# ---- Solve ----

class SolveRequest(BaseModel):
    t_rest: float = 8.0
    rho: float = 2.0


class ScheduleRunOut(BaseModel):
    id: int
    created_at: datetime
    t_rest: float
    rho: float
    status: str
    summary: Optional[dict] = None
    error_message: Optional[str] = None


@router.post("/solve", response_model=ScheduleRunOut)
def solve(body: SolveRequest, session: Session = Depends(get_session)):
    cadets = build_cadets(session)
    jobs = build_jobs(session)
    constraint_index = build_constraint_index(session)

    result = InputValidator.validate(cadets=cadets, jobs=jobs, constraints=constraint_index)
    if not result.is_valid:
        raise HTTPException(status_code=422, detail="Validation failed: " + "; ".join(result.errors))

    run = ScheduleRun(t_rest=body.t_rest, rho=body.rho, status="running")
    session.add(run)
    session.commit()

    run_dir = RUNS_DIR / str(run.id)
    run_dir.mkdir(parents=True, exist_ok=True)
    output_path = str(run_dir / "schedule.xlsx")

    try:
        context = build_context(cadets=cadets, jobs=jobs, constraint_index=constraint_index, T_rest=body.t_rest, rho=body.rho)
        schedule = CpsatShiftAssigner(t_rest_hours=body.t_rest, rho=body.rho).assign(context)

        ExcelExporter().export(schedule, cadets, output_path)
        Evaluator().evaluate(schedule, cadets, output_path)

        summary_path = Path(output_path).with_suffix("") / "evaluation" / "summary.json"
        summary = json.loads(summary_path.read_text()) if summary_path.exists() else None

        run.status = "success"
        run.excel_path = output_path
        run.summary_json = json.dumps(summary) if summary else None
    except ValueError as e:
        run.status = "failed"
        run.error_message = str(e)
    session.commit()

    return ScheduleRunOut(
        id=run.id, created_at=run.created_at, t_rest=run.t_rest, rho=run.rho,
        status=run.status, summary=json.loads(run.summary_json) if run.summary_json else None,
        error_message=run.error_message,
    )


@router.get("/schedule-runs", response_model=List[ScheduleRunOut])
def list_schedule_runs(session: Session = Depends(get_session)):
    return [
        ScheduleRunOut(
            id=r.id, created_at=r.created_at, t_rest=r.t_rest, rho=r.rho,
            status=r.status, summary=json.loads(r.summary_json) if r.summary_json else None,
            error_message=r.error_message,
        )
        for r in session.query(ScheduleRun).order_by(ScheduleRun.id.desc()).all()
    ]
