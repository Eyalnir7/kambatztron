"""Create (or reset the password of) a manager account.

Manager accounts are not self-service (no open registration endpoint --
that role can edit the whole roster and trigger solves), so this is run
directly against the database instead.

Usage:
    python scripts/create_manager.py <username> <password>
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from db.session import Base, engine, SessionLocal
from db.models import ManagerUser
from api.auth import hash_password


def main(username: str, password: str) -> None:
    Base.metadata.create_all(engine)
    session = SessionLocal()
    try:
        user = session.query(ManagerUser).filter_by(username=username).first()
        if user is None:
            user = ManagerUser(username=username, hashed_password=hash_password(password))
            session.add(user)
            print(f"Created manager '{username}'.")
        else:
            user.hashed_password = hash_password(password)
            print(f"Updated password for manager '{username}'.")
        session.commit()
    finally:
        session.close()


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python scripts/create_manager.py <username> <password>")
        sys.exit(1)
    main(sys.argv[1], sys.argv[2])
