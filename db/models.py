"""SQLAlchemy models backing the web layer.

These are persistence rows only. They get translated into the engine's
domain objects (domain.cadet.Cadet, domain.job.Job, ...) by api/adapters.py
before being handed to the untouched scheduling engine.
"""
from datetime import datetime

from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.session import Base


class ManagerUser(Base):
    __tablename__ = "manager_users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(unique=True, index=True)
    hashed_password: Mapped[str]


class CadetAccount(Base):
    __tablename__ = "cadet_accounts"

    id: Mapped[int] = mapped_column(primary_key=True)
    personal_number: Mapped[str] = mapped_column(unique=True, index=True)
    name: Mapped[str]
    gender: Mapped[str] = mapped_column(default="")
    team: Mapped[str] = mapped_column(default="")
    platoon: Mapped[str] = mapped_column(default="")

    unavailable_slots: Mapped[list["CadetUnavailableSlot"]] = relationship(
        back_populates="cadet", cascade="all, delete-orphan"
    )
    forbidden_jobs: Mapped[list["CadetForbiddenJob"]] = relationship(
        back_populates="cadet", cascade="all, delete-orphan"
    )


class CadetUnavailableSlot(Base):
    """One row per unavailable time slot a cadet has submitted."""
    __tablename__ = "cadet_unavailable_slots"

    id: Mapped[int] = mapped_column(primary_key=True)
    cadet_id: Mapped[int] = mapped_column(ForeignKey("cadet_accounts.id"))
    start: Mapped[datetime]
    end: Mapped[datetime]

    cadet: Mapped["CadetAccount"] = relationship(back_populates="unavailable_slots")


class CadetForbiddenJob(Base):
    """One row per job name a cadet is not allowed/willing to do."""
    __tablename__ = "cadet_forbidden_jobs"
    __table_args__ = (UniqueConstraint("cadet_id", "job_name"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    cadet_id: Mapped[int] = mapped_column(ForeignKey("cadet_accounts.id"))
    job_name: Mapped[str]

    cadet: Mapped["CadetAccount"] = relationship(back_populates="forbidden_jobs")


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(unique=True, index=True)
    job_type: Mapped[str]

    shifts: Mapped[list["ShiftDefinition"]] = relationship(
        back_populates="job", cascade="all, delete-orphan"
    )


class ShiftDefinition(Base):
    """A (job, time slot, difficulty) row — one entry of Job.difficulty_by_slot."""
    __tablename__ = "shift_definitions"
    __table_args__ = (UniqueConstraint("job_id", "start", "end"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("jobs.id"))
    start: Mapped[datetime]
    end: Mapped[datetime]
    difficulty: Mapped[float]

    job: Mapped["Job"] = relationship(back_populates="shifts")


class JobConstraintRow(Base):
    __tablename__ = "job_constraints"
    __table_args__ = (UniqueConstraint("job_type_a", "job_type_b"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    job_type_a: Mapped[str]
    job_type_b: Mapped[str]
    can_overlap: Mapped[bool]
    can_be_consecutive: Mapped[bool]


class TeamConstraintSlot(Base):
    """One row per unavailable time slot that applies to an entire team."""
    __tablename__ = "team_constraint_slots"

    id: Mapped[int] = mapped_column(primary_key=True)
    team: Mapped[str] = mapped_column(index=True)
    start: Mapped[datetime]
    end: Mapped[datetime]


class ScheduleRun(Base):
    """Record of one solve attempt, its params, and where its output landed."""
    __tablename__ = "schedule_runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    t_rest: Mapped[float]
    rho: Mapped[float]
    status: Mapped[str]  # "success" | "failed"
    excel_path: Mapped[str | None] = mapped_column(default=None)
    summary_json: Mapped[str | None] = mapped_column(default=None)
    error_message: Mapped[str | None] = mapped_column(default=None)
