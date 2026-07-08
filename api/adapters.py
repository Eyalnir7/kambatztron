"""Turns DB rows into the engine's domain objects.

This is the only seam between the web layer (db/) and the untouched
scheduling engine (domain/, scheduling/, output/). Nothing here changes
engine behavior -- it just builds the same Cadet/Job/TimeSlot/ConstraintIndex
objects the CSV/JSON readers already build from files.
"""
from collections import defaultdict
from typing import List

from sqlalchemy.orm import Session

from domain.cadet import Cadet
from domain.job import Job
from domain.time_slot import TimeSlot
from domain.constraints import ConstraintIndex, JobConstraint, TeamConstraint

from db.models import CadetAccount, Job as JobRow, JobConstraintRow, TeamConstraintSlot


def build_cadets(session: Session) -> List[Cadet]:
    """Build Cadet objects, folding each cadet's team-wide blackout slots
    into their individual unavailable_slots (the engine has no separate
    notion of team-level unavailability applied automatically)."""
    team_slots = defaultdict(list)
    for row in session.query(TeamConstraintSlot).all():
        team_slots[row.team].append(TimeSlot(start=row.start, end=row.end))

    cadets: List[Cadet] = []
    for row in session.query(CadetAccount).all():
        unavailable = [
            TimeSlot(start=s.start, end=s.end) for s in row.unavailable_slots
        ] + team_slots.get(row.team, [])
        forbidden = [f.job_name for f in row.forbidden_jobs]

        cadets.append(
            Cadet(
                personal_number=row.personal_number,
                name=row.name,
                unavailable_slots=unavailable,
                forbidden_jobs=forbidden,
                gender=row.gender,
                team=row.team,
                platoon=row.platoon,
            )
        )
    return cadets


def build_jobs(session: Session) -> List[Job]:
    jobs: List[Job] = []
    for row in session.query(JobRow).all():
        difficulty_by_slot = {
            TimeSlot(start=s.start, end=s.end): s.difficulty for s in row.shifts
        }
        jobs.append(
            Job(name=row.name, job_type=row.job_type, difficulty_by_slot=difficulty_by_slot)
        )
    return jobs


def build_constraint_index(session: Session) -> ConstraintIndex:
    job_constraints = [
        JobConstraint(
            job_type_a=row.job_type_a,
            job_type_b=row.job_type_b,
            can_overlap=row.can_overlap,
            can_be_consecutive=row.can_be_consecutive,
        )
        for row in session.query(JobConstraintRow).all()
    ]

    team_constraints_by_team = defaultdict(list)
    for row in session.query(TeamConstraintSlot).all():
        team_constraints_by_team[row.team].append(TimeSlot(start=row.start, end=row.end))
    team_constraints = [
        TeamConstraint(team=team, unavailable_slots=slots)
        for team, slots in team_constraints_by_team.items()
    ]

    return ConstraintIndex(job_constraints, team_constraints)
