"""TimeSlot represents a time range with overlap/consecutive logic."""

from datetime import datetime
from pydantic import BaseModel, ConfigDict, model_validator


class TimeSlot(BaseModel):
    """Represents a time range from start to end.

    Format: datetime objects parsed from "YYYY-MM-DD HH:MM" strings.
    """
    model_config = ConfigDict(frozen=True)

    start: datetime
    end: datetime

    @model_validator(mode='after')
    def check_start_before_end(self) -> 'TimeSlot':
        """Validate that start < end."""
        if self.start >= self.end:
            raise ValueError(f"Invalid time slot: start {self.start} must be before end {self.end}")
        return self

    @classmethod
    def parse(cls, start_str: str, end_str: str) -> "TimeSlot":
        """Parse a time slot from two datetime strings.

        Args:
            start_str: Start datetime in format "YYYY-MM-DD HH:MM"
            end_str: End datetime in format "YYYY-MM-DD HH:MM"

        Returns:
            TimeSlot instance

        Raises:
            ValueError: If format is invalid or start >= end
        """
        try:
            start_dt = datetime.strptime(start_str, "%Y-%m-%d %H:%M")
            end_dt = datetime.strptime(end_str, "%Y-%m-%d %H:%M")
        except ValueError as e:
            raise ValueError(f"Invalid time slot format: {e}")

        return cls(start=start_dt, end=end_dt)

    @classmethod
    def from_string(cls, time_slot_str: str) -> "TimeSlot":
        """Parse a time slot from a single string.

        Format: "YYYY-MM-DD HH:MM-YYYY-MM-DD HH:MM"

        Args:
            time_slot_str: Full time slot string

        Returns:
            TimeSlot instance

        Raises:
            ValueError: If format is invalid
        """
        parts = time_slot_str.strip().split("-")

        if len(parts) < 5:
            raise ValueError(
                f"Invalid time slot format '{time_slot_str}'. "
                "Expected: 'YYYY-MM-DD HH:MM-YYYY-MM-DD HH:MM'"
            )

        start_str = f"{parts[0]}-{parts[1]}-{parts[2]}"
        end_str = f"{parts[3]}-{parts[4]}-{parts[5]}"

        return cls.parse(start_str, end_str)

    def overlaps(self, other: "TimeSlot") -> bool:
        """Check if this time slot overlaps with another."""
        return self.start < other.end and other.start < self.end

    def is_consecutive_with(self, other: "TimeSlot") -> bool:
        """Check if this time slot is consecutive with another."""
        return self.end == other.start or other.end == self.start

    def __repr__(self) -> str:
        """Return a readable string representation."""
        return (
            f"{self.start.strftime('%Y-%m-%d %H:%M')}-"
            f"{self.end.strftime('%Y-%m-%d %H:%M')}"
        )

    def __str__(self) -> str:
        return self.__repr__()

    def __hash__(self) -> int:
        """Make TimeSlot hashable for use in sets and dicts."""
        return hash((self.start, self.end))
