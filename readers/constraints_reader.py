"""Reader for job constraints CSV file (moved from io package)."""

import csv
from typing import List
from pathlib import Path

from domain import ConstraintIndex


class ConstraintsCSVReader:
    REQUIRED_COLUMNS = {
        "job_type_a",
        "job_type_b",
        "can_overlap",
        "can_be_consecutive",
    }

    @classmethod
    def read(cls, path: str) -> ConstraintIndex:
        file_path = Path(path)

        if not file_path.exists():
            raise FileNotFoundError(f"Constraints file not found: {path}")

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)

                if reader.fieldnames is None:
                    raise ValueError("Constraints CSV is empty")

                missing_columns = cls.REQUIRED_COLUMNS - set(reader.fieldnames)
                if missing_columns:
                    raise ValueError(
                        f"Missing required columns in constraints CSV: {missing_columns}"
                    )

                rows = list(reader)

        except FileNotFoundError:
            raise
        except ValueError:
            raise
        except Exception as e:
            raise ValueError(f"Error reading constraints CSV: {e}") from e

        if not rows:
            raise ValueError("No constraints found in CSV file")

        try:
            constraint_index = ConstraintIndex.from_csv_rows(rows)
        except ValueError as e:
            raise ValueError(f"Error parsing constraints: {e}") from e

        return constraint_index
