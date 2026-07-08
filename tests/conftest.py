"""Points the web layer at a throwaway SQLite DB before any api/db module is imported."""
import os
import sys
import tempfile
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

_tmp_dir = Path(tempfile.mkdtemp(prefix="kambatztron_test_"))
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp_dir / 'test.db'}"
os.environ["SECRET_KEY"] = "test-secret-not-for-prod"
os.environ["RUNS_DIR"] = str(_tmp_dir / "runs")
