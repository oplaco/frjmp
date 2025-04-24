import unittest
from datetime import date

from frjmp.model.sets.job import Job
from frjmp.model.sets.position import Position
from frjmp.utils.validation_utils import (
    validate_capacity_feasibility,
    validate_non_overlapping_jobs_per_aircraft,
)
from tests.setup import BasicTestSetup


class TestCapacityValidation(BasicTestSetup):
    def setUp(self):
        super().setUp()

        # Avoid using compressed dates function and adding a dependency
        self.compressed_dates = [self.date1, self.date2, self.date3, self.date4]
        self.date_to_index = {d: i for i, d in enumerate(self.compressed_dates)}

    def test_single_need_globally_overbooked_fails(self):
        """2 units of need1 are required per day but only 1 is available"""
        jobs = [
            Job(self.aircraft1, self.phase1, self.date1, self.date2),
            Job(self.aircraft2, self.phase1, self.date1, self.date2),
        ]
        positions = [Position("Hangar A", [self.need1], capacity=1)]

        with self.assertRaises(ValueError):
            validate_capacity_feasibility(
                jobs, positions, self.compressed_dates, self.date_to_index
            )

    def test_multiple_need_locally_overbooked_fails(self):
        """3 units of need1 are required per day but only 1 is available as the rest of positions can not serve this need."""
        jobs = [
            Job(self.aircraft1, self.phase1, self.date1, self.date2),
            Job(self.aircraft2, self.phase1, self.date1, self.date2),
            Job(self.aircraft3, self.phase1, self.date1, self.date2),
        ]
        positions = [
            Position("Hangar A", [self.need1], capacity=1),
            Position("Hangar B", [self.need2], capacity=4),
        ]
        with self.assertRaises(ValueError):
            validate_capacity_feasibility(
                jobs, positions, self.compressed_dates, self.date_to_index
            )

    def test_multiple_needs_one_position_fails(self):
        """1 units of need1, need2 and need3 respectively are required. There is only one position that can handle
        the 3 needs but has not enough capacity at the same. It should fail
        """
        jobs = [
            Job(self.aircraft1, self.phase1, self.date1, self.date2),
            Job(self.aircraft2, self.phase2, self.date1, self.date2),
            Job(self.aircraft3, self.phase4, self.date1, self.date2),
        ]
        positions = [
            Position("Hangar A", [self.need1, self.need2, self.need3], capacity=1),
        ]

        with self.assertRaises(ValueError):
            validate_capacity_feasibility(
                jobs, positions, self.compressed_dates, self.date_to_index
            )

        # Test the opossite pass
        positions[0].capacity = 3

        result = validate_capacity_feasibility(
            jobs, positions, self.compressed_dates, self.date_to_index
        )
        self.assertEqual(result[0]["per_need"][self.need1.name], (3, 1))
        self.assertEqual(result[0]["per_need"][self.need2.name], (3, 1))
        self.assertEqual(result[0]["per_need"][self.need3.name], (3, 1))

    def test_single_need_enough_capacity_pass(self):
        """2 units of need1 is required per day and a position with capacity 2 is given"""
        jobs = [
            Job(self.aircraft1, self.phase1, self.date1, self.date2),
            Job(self.aircraft2, self.phase1, self.date1, self.date2),
        ]
        positions = [Position("Hangar A", [self.need1], capacity=2)]

        result = validate_capacity_feasibility(
            jobs, positions, self.compressed_dates, self.date_to_index
        )
        self.assertEqual(result[0]["per_need"][self.need1.name], (2, 2))
        self.assertEqual(result[1]["per_need"][self.need1.name], (2, 2))


class TestOverlappingJobValidation(BasicTestSetup):
    """Test validate_non_overlapping_jobs_per_aircraft function"""

    def test_on_job_overlap_for_same_aircraft_fails(self):
        # End date exact overlap
        jobs = [
            Job(self.aircraft1, self.phase1, date(2025, 4, 10), date(2025, 4, 15)),
            Job(self.aircraft1, self.phase2, date(2025, 4, 15), date(2025, 4, 20)),
        ]
        with self.assertRaises(ValueError):
            validate_non_overlapping_jobs_per_aircraft(jobs)

        # Start date exact overlap
        jobs = [
            Job(self.aircraft1, self.phase1, date(2025, 4, 10), date(2025, 4, 15)),
            Job(self.aircraft1, self.phase2, date(2025, 1, 15), date(2025, 4, 10)),
        ]
        with self.assertRaises(ValueError):
            validate_non_overlapping_jobs_per_aircraft(jobs)

        # Between start and end date overlap
        jobs = [
            Job(self.aircraft1, self.phase1, date(2025, 4, 10), date(2025, 4, 15)),
            Job(self.aircraft1, self.phase2, date(2025, 4, 12), date(2025, 4, 13)),
        ]
        with self.assertRaises(ValueError):
            validate_non_overlapping_jobs_per_aircraft(jobs)

    def test_when_jobs_do_not_overlap_pass(self):
        # No date overlap
        jobs = [
            Job(self.aircraft1, self.phase1, date(2025, 4, 10), date(2025, 4, 13)),
            Job(self.aircraft1, self.phase1, date(2025, 4, 14), date(2025, 4, 20)),
        ]
        validate_non_overlapping_jobs_per_aircraft(jobs)  # Should not raise

        # Overlap but not the same aircraft
        jobs = [
            Job(self.aircraft1, self.phase1, date(2025, 4, 10), date(2025, 4, 15)),
            Job(self.aircraft2, self.phase1, date(2025, 4, 12), date(2025, 4, 13)),
        ]
        validate_non_overlapping_jobs_per_aircraft(jobs)  # Should not raise


if __name__ == "__main__":
    unittest.main()
