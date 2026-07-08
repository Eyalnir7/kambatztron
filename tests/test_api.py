"""End-to-end tests for the web layer: auth, CRUD, and a full solve run."""
import pytest
from fastapi.testclient import TestClient

from api.main import app
from api.auth import hash_password
from db.session import Base, engine, SessionLocal
from db.models import ManagerUser


@pytest.fixture(autouse=True)
def reset_db():
    """Each test gets a clean schema -- the DB file is shared across the
    whole test session (set once in conftest.py), so state must not leak
    between tests."""
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    yield


@pytest.fixture()
def manager_client():
    with TestClient(app) as client:
        session = SessionLocal()
        session.add(ManagerUser(username="alice", hashed_password=hash_password("secretpw")))
        session.commit()
        session.close()

        resp = client.post("/api/auth/manager/login", json={"username": "alice", "password": "secretpw"})
        assert resp.status_code == 200
        yield client


def test_health(manager_client):
    resp = manager_client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_manager_login_rejects_bad_password():
    with TestClient(app) as client:
        session = SessionLocal()
        session.add(ManagerUser(username="bob", hashed_password=hash_password("correct")))
        session.commit()
        session.close()

        resp = client.post("/api/auth/manager/login", json={"username": "bob", "password": "wrong"})
        assert resp.status_code == 401


def test_manager_routes_require_auth():
    with TestClient(app) as client:
        resp = client.get("/api/manager/cadets")
        assert resp.status_code == 401


def test_cadet_login_unknown_personal_number(manager_client):
    resp = manager_client.post("/api/auth/cadet/login", json={"personal_number": "does-not-exist"})
    assert resp.status_code == 404


def test_full_roster_job_constraint_and_solve_flow(manager_client):
    # Roster: two cadets
    resp = manager_client.post("/api/manager/cadets", json={
        "personal_number": "001", "name": "Alice", "gender": "F", "team": "A", "platoon": "1",
    })
    assert resp.status_code == 200
    resp = manager_client.post("/api/manager/cadets", json={
        "personal_number": "002", "name": "Bob", "gender": "M", "team": "A", "platoon": "1",
    })
    assert resp.status_code == 200

    # Duplicate personal_number is rejected
    resp = manager_client.post("/api/manager/cadets", json={
        "personal_number": "001", "name": "Alice2", "gender": "F", "team": "A", "platoon": "1",
    })
    assert resp.status_code == 409

    # Job with two consecutive shifts
    resp = manager_client.post("/api/manager/jobs", json={"name": "guard", "job_type": "guarding"})
    assert resp.status_code == 200
    resp = manager_client.post("/api/manager/jobs/guard/shifts", json={
        "start": "2026-01-01T00:00:00", "end": "2026-01-01T08:00:00", "difficulty": 5,
    })
    assert resp.status_code == 200
    resp = manager_client.post("/api/manager/jobs/guard/shifts", json={
        "start": "2026-01-01T08:00:00", "end": "2026-01-01T16:00:00", "difficulty": 3,
    })
    assert resp.status_code == 200

    # Same job type may be assigned consecutively to the same cadet
    resp = manager_client.post("/api/manager/job-constraints", json={
        "job_type_a": "guarding", "job_type_b": "guarding",
        "can_overlap": False, "can_be_consecutive": True,
    })
    assert resp.status_code == 200

    # Cadet 002 (Bob) logs in and marks himself unable to guard
    with TestClient(app) as cadet_client:
        resp = cadet_client.post("/api/auth/cadet/login", json={"personal_number": "002"})
        assert resp.status_code == 200
        assert resp.json()["name"] == "Bob"

        resp = cadet_client.get("/api/cadet/me")
        assert resp.status_code == 200
        assert resp.json()["personal_number"] == "002"

        resp = cadet_client.put("/api/cadet/preferences", json={
            "unavailable_slots": [],
            "forbidden_jobs": ["guard"],
        })
        assert resp.status_code == 200
        assert resp.json()["forbidden_jobs"] == ["guard"]

        # A cadet can't reach manager-only routes
        resp = cadet_client.get("/api/manager/cadets")
        assert resp.status_code == 403

    # Manager triggers a solve; since Bob is forbidden from "guard", both
    # shifts must land on Alice, which the job-constraint row we added permits.
    resp = manager_client.post("/api/manager/solve", json={"t_rest": 8.0, "rho": 2.0})
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "success", body.get("error_message")
    assert body["summary"]["num_assigned_shifts"] == 2
    assert body["summary"]["total_shifts"] == 2

    resp = manager_client.get("/api/manager/schedule-runs")
    assert resp.status_code == 200
    assert len(resp.json()) == 1
    assert resp.json()[0]["status"] == "success"
