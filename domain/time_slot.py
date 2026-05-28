"""TimeSlot represents a time range with overlap/consecutive logic."""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass(frozen=True)
class TimeSlot:
    """Represents a time range from start to end.

    Format: datetime objects parsed from "YYYY-MM-DD HH:MM" strings.
    """
    start: datetime
    end: datetime

    def __post_init__(self):
        """Validate that start < end."""
        if self.start >= self.end:
            raise ValueError(f"Invalid time slot: start {self.start} must be before end {self.end}")

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
            start = datetime.strptime(start_str, "%Y-%m-%d %H:%M")
            end = datetime.strptime(end_str, "%Y-%m-%d %H:%M")
        except ValueError as e:
            raise ValueError(f"Invalid time slot format: {e}")

        return cls(start=start, end=end)

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
        # Split on the separator between start and end times
        # The format is: YYYY-MM-DD HH:MM-YYYY-MM-DD HH:MM
        # We need to find where the separator dash is (after the first HH:MM)
        parts = time_slot_str.strip().split("-")

        if len(parts) < 5:  # YYYY, MM, DD HH:MM, YYYY, MM, DD HH:MM
            raise ValueError(
                f"Invalid time slot format '{time_slot_str}'. "
                "Expected: 'YYYY-MM-DD HH:MM-YYYY-MM-DD HH:MM'"
            )

        # Reconstruct start: YYYY-MM-DD HH:MM
        start_str = f"{parts[0]}-{parts[1]}-{parts[2]}"

        # Reconstruct end: YYYY-MM-DD HH:MM
        end_str = f"{parts[3]}-{parts[4]}-{parts[5]}"

        return cls.parse(start_str, end_str)

    def overlaps(self, other: "TimeSlot") -> bool:
        """Check if this time slot overlaps with another.

        Two time slots overlap if one starts before the other ends.

        Args:
            other: Another TimeSlot

        Returns:
            True if they overlap, False otherwise
        """
        return self.start < other.end and other.start < self.end

    def is_consecutive_with(self, other: "TimeSlot") -> bool:
        """Check if this time slot is consecutive with another.

        Two time slots are consecutive if one ends exactly when the other starts.

        Args:
            other: Another TimeSlot

        Returns:
            True if they are consecutive, False otherwise
        """
        return self.end == other.start or other.end == self.start

    def __repr__(self) -> str:
        """Return a readable string representation."""
        return (
            f"{self.start.strftime('%Y-%m-%d %H:%M')}-"
            f"{self.end.strftime('%Y-%m-%d %H:%M')}"
        )

    def __hash__(self) -> int:
        """Make TimeSlot hashable for use in sets and dicts."""
        return hash((self.start, self.end))
