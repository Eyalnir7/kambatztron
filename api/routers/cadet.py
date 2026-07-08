"""Cadet-facing routes: view own profile, submit availability/forbidden-job preferences."""
from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from db.session import get_session
from db.models import CadetAccount, CadetUnavailableSlot, CadetForbiddenJob, Job

from api.deps import require_cadet

router = APIRouter(prefix="/api/cadet", tags=["cadet"], dependencies=[Depends(require_cadet)])


def _get_self(claims: dict, session: Session) -> CadetAccount:
    cadet = session.get(CadetAccount, claims["cadet_id"])
    if cadet is None:
        raise HTTPException(status_code=404, detail="Cadet account no longer exists")
    return cadet


class SlotOut(BaseModel):
    start: datetime
    end: datetime


class MeOut(BaseModel):
    personal_number: str
    name: str
    gender: str
    team: str
    platoon: str
    unavailable_slots: List[SlotOut]
    forbidden_jobs: List[str]


@router.get("/me", response_model=MeOut)
def get_me(claims: dict = Depends(require_cadet), session: Session = Depends(get_session)):
    cadet = _get_self(claims, session)
    return MeOut(
        personal_number=cadet.personal_number,
        name=cadet.name,
        gender=cadet.gender,
        team=cadet.team,
        platoon=cadet.platoon,
        unavailable_slots=[SlotOut(start=s.start, end=s.end) for s in cadet.unavailable_slots],
        forbidden_jobs=[f.job_name for f in cadet.forbidden_jobs],
    )


@router.get("/jobs")
def list_job_options(session: Session = Depends(get_session)):
    """Read-only list of job names/types, so a cadet knows what to pick from
    when marking jobs they can't/won't do."""
    return [{"name": j.name, "job_type": j.job_type} for j in session.query(Job).all()]


class PreferencesIn(BaseModel):
    unavailable_slots: List[SlotOut] = []
    forbidden_jobs: List[str] = []


@router.put("/preferences", response_model=MeOut)
def submit_preferences(
    body: PreferencesIn,
    claims: dict = Depends(require_cadet),
    session: Session = Depends(get_session),
):
    cadet = _get_self(claims, session)

    for slot in list(cadet.unavailable_slots):
        session.delete(slot)
    for job in list(cadet.forbidden_jobs):
        session.delete(job)
    session.flush()

    for slot in body.unavailable_slots:
        if slot.start >= slot.end:
            raise HTTPException(status_code=422, detail=f"Invalid slot: start {slot.start} must be before end {slot.end}")
        session.add(CadetUnavailableSlot(cadet_id=cadet.id, start=slot.start, end=slot.end))
    for job_name in set(body.forbidden_jobs):
        session.add(CadetForbiddenJob(cadet_id=cadet.id, job_name=job_name))

    session.commit()
    session.refresh(cadet)
    return get_me(claims=claims, session=session)
