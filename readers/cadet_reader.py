"""Reader for cadets CSV file (moved from io package)."""

import csv
from typing import List
from pathlib import Path

from domain import Cadet


class CadetCSVReader:
    """Reads cadets from a CSV file and returns Cadet objects."""

    REQUIRED_COLUMNS = {
        "personal_number",
        "name",
        "unavailable_hours",
        "forbidden_jobs",
        "gender",
        "team",
        "platoon",
    }

    @classmethod
    def read(cls, path: str) -> List[Cadet]:
        file_path = Path(path)

        if not file_path.exists():
            raise FileNotFoundError(f"Cadets file not found: {path}")

        cadets = []

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)

                if reader.fieldnames is None:
                    raise ValueError("Cadets CSV is empty")

                missing_columns = cls.REQUIRED_COLUMNS - set(reader.fieldnames)
                if missing_columns:
                    raise ValueError(
                        f"Missing required columns in cadets CSV: {missing_columns}"
                    )

                for row_number, row in enumerate(reader, start=2):
                    try:
                        cadet = Cadet.from_csv_row(
                            personal_number=row["personal_number"].strip(),
                            name=row["name"].strip(),
                            unavailable_hours=row["unavailable_hours"].strip(),
                            forbidden_jobs=row["forbidden_jobs"].strip(),
                            gender=row["gender"].strip(),
                            team=row["team"].strip(),
                            platoon=row["platoon"].strip(),
                        )
                        cadets.append(cadet)

                    except ValueError as e:
                        raise ValueError(
                            f"Error parsing cadet at row {row_number}: {e}"
                        ) from e

        except FileNotFoundError:
            raise
        except ValueError:
            raise
        except Exception as e:
            raise ValueError(f"Error reading cadets CSV: {e}") from e

        if not cadets:
            raise ValueError("No cadets found in CSV file")

        return cadets
