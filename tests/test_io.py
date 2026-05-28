"""Tests for the input layer readers."""

import unittest
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Change to project root for file access
import os
os.chdir(project_root)

# Clear any cached imports of 'io'
# Clear any cached imports of the readers package
if 'readers' in sys.modules:
    del sys.modules['readers']

# Import after changing to project root
from readers.cadet_reader import CadetCSVReader
from readers.job_reader import JobJSONReader
from readers.constraints_reader import ConstraintsCSVReader


class TestCadetCSVReader(unittest.TestCase):
    """Tests for CadetCSVReader."""

    def test_read_example_cadets(self):
        """Test reading the example cadets CSV file."""
        cadets = CadetCSVReader.read("toy_data/example_cadets.csv")

        self.assertEqual(len(cadets), 8)

        # Check first cadet
        david = cadets[0]
        self.assertEqual(david.personal_number, "1001")
        self.assertEqual(david.name, "David Cohen")
        self.assertEqual(david.gender, "M")
        self.assertEqual(david.team, "Alpha")
        self.assertEqual(david.platoon, "1")
        self.assertEqual(len(david.unavailable_slots), 1)
        self.assertEqual(len(david.forbidden_jobs), 1)
        self.assertIn("Kitchen Cleaning", david.forbidden_jobs)

        # Check cadet with multiple unavailable hours
        sarah = [c for c in cadets if c.name == "Sarah Goldstein"][0]
        self.assertEqual(len(sarah.unavailable_slots), 2)

        # Check cadet with no forbidden jobs
        self.assertEqual(len(sarah.forbidden_jobs), 0)

    def test_read_missing_file(self):
        """Test error handling for missing file."""
        with self.assertRaises(FileNotFoundError):
            CadetCSVReader.read("nonexistent.csv")

    def test_required_columns_validation(self):
        """Test that required columns are validated."""
        # This would need a malformed CSV file to test properly
        # For now, we just verify the REQUIRED_COLUMNS constant exists
        self.assertIn("personal_number", CadetCSVReader.REQUIRED_COLUMNS)
        self.assertIn("name", CadetCSVReader.REQUIRED_COLUMNS)
        self.assertIn("unavailable_hours", CadetCSVReader.REQUIRED_COLUMNS)


class TestJobJSONReader(unittest.TestCase):
    """Tests for JobJSONReader."""

    def test_read_example_jobs(self):
        """Test reading the example jobs JSON file."""
        jobs = JobJSONReader.read("toy_data/example_jobs.json")

        self.assertEqual(len(jobs), 6)

        # Check job types
        job_types = {job.job_type for job in jobs}
        expected_types = {"guarding", "cleaning", "standby-team", "ceremony-guarding"}
        self.assertEqual(job_types, expected_types)

        # Check guarding jobs have same time slots
        guarding_jobs = [j for j in jobs if j.job_type == "guarding"]
        self.assertEqual(len(guarding_jobs), 2)

        slots_1 = set(guarding_jobs[0].difficulty_by_slot.keys())
        slots_2 = set(guarding_jobs[1].difficulty_by_slot.keys())
        self.assertEqual(slots_1, slots_2)

        # Check difficulty values are in range [1, 10]
        for job in jobs:
            for difficulty in job.difficulty_by_slot.values():
                self.assertGreaterEqual(difficulty, 1)
                self.assertLessEqual(difficulty, 10)

    def test_read_missing_file(self):
        """Test error handling for missing file."""
        with self.assertRaises(FileNotFoundError):
            JobJSONReader.read("nonexistent.json")

    def test_job_has_name_and_type(self):
        """Test that jobs have required name and type."""
        jobs = JobJSONReader.read("toy_data/example_jobs.json")

        for job in jobs:
            self.assertIsNotNone(job.name)
            self.assertGreater(len(job.name), 0)
            self.assertIsNotNone(job.job_type)
            self.assertGreater(len(job.job_type), 0)
            self.assertGreater(len(job.difficulty_by_slot), 0)


class TestConstraintsCSVReader(unittest.TestCase):
    """Tests for ConstraintsCSVReader."""

    def test_read_example_constraints(self):
        """Test reading the example constraints CSV file."""
        constraints = ConstraintsCSVReader.read("toy_data/example_job_constraints.csv")

        # Test some constraint queries
        self.assertFalse(constraints.can_overlap("guarding", "cleaning"))
        self.assertFalse(constraints.can_be_consecutive("guarding", "cleaning"))

        self.assertTrue(constraints.can_overlap("standby-team", "standby-team"))
        self.assertTrue(constraints.can_be_consecutive("standby-team", "standby-team"))

        # Test bidirectionality
        self.assertEqual(
            constraints.can_overlap("guarding", "cleaning"),
            constraints.can_overlap("cleaning", "guarding"),
        )

        self.assertEqual(
            constraints.can_be_consecutive("standby-team", "ceremony-guarding"),
            constraints.can_be_consecutive("ceremony-guarding", "standby-team"),
        )

    def test_read_missing_file(self):
        """Test error handling for missing file."""
        with self.assertRaises(FileNotFoundError):
            ConstraintsCSVReader.read("nonexistent.csv")

    def test_required_columns_validation(self):
        """Test that required columns are validated."""
        self.assertIn("job_type_a", ConstraintsCSVReader.REQUIRED_COLUMNS)
        self.assertIn("job_type_b", ConstraintsCSVReader.REQUIRED_COLUMNS)
        self.assertIn("can_overlap", ConstraintsCSVReader.REQUIRED_COLUMNS)
        self.assertIn("can_be_consecutive", ConstraintsCSVReader.REQUIRED_COLUMNS)


class TestInputLayerIntegration(unittest.TestCase):
    """Integration tests for the input layer."""

    def test_read_all_example_files(self):
        """Test reading all example files together."""
        cadets = CadetCSVReader.read("toy_data/example_cadets.csv")
        jobs = JobJSONReader.read("toy_data/example_jobs.json")
        constraints = ConstraintsCSVReader.read("toy_data/example_job_constraints.csv")

        # Basic sanity checks
        self.assertGreater(len(cadets), 0)
        self.assertGreater(len(jobs), 0)
        self.assertIsNotNone(constraints)

        # Verify no duplicate cadet personal numbers
        personal_numbers = {c.personal_number for c in cadets}
        self.assertEqual(len(personal_numbers), len(cadets))

        # Verify all job names are unique
        job_names = {j.name for j in jobs}
        self.assertEqual(len(job_names), len(jobs))

        # Verify all jobs have at least one time slot
        for job in jobs:
            self.assertGreater(len(job.difficulty_by_slot), 0)


if __name__ == "__main__":
    unittest.main()
