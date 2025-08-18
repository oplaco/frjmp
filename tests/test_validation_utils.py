import unittest
from datetime import date

from frjmp.model.sets.job import Job
from frjmp.model.sets.position import Position
from frjmp.utils.validation_utils import (
    validate_capacity_feasibility,
    validate_non_overlapping_jobs_per_unit,
)
from tests.setup import BasicTestSetup


class TestCapacityValidation(BasicTestSetup):
    def setUp(self):
        super().setUp()

        # Avoid using compressed timeslots function and adding a dependency
        # Manual compressed time values
        self.compressed_values = [self.date1, self.date2, self.date3, self.date4]

        # Convert to ticks
        self.compressed_ticks = [
            self.adapter.to_tick(d) for d in self.compressed_values
        ]

        # Build mappings manually
        self.tick_to_index = {tick: i for i, tick in enumerate(self.compressed_ticks)}
        self.index_to_tick = {i: tick for tick, i in self.tick_to_index.items()}
        self.index_to_value = {
            i: self.adapter.from_tick(tick) for i, tick in self.index_to_tick.items()
        }

    def test_single_need_globally_overbooked_fails(self):
        """2 units of need1 are required per day but only 1 is available"""
        jobs = [
            Job(self.unit1, self.phase1, self.date1, self.date2),
            Job(self.unit2, self.phase1, self.date1, self.date2),
        ]
        positions = [Position("Position 1", [self.need1], capacity=1)]

        with self.assertRaises(ValueError):
            validate_capacity_feasibility(
                jobs,
                positions,
                self.compressed_ticks,
                self.tick_to_index,
                self.adapter,
                self.index_to_value,
            )

    def test_multiple_need_locally_overbooked_fails(self):
        """3 units of need1 are required per day but only 1 is available as the rest of positions can not serve this need."""
        jobs = [
            Job(self.unit1, self.phase1, self.date1, self.date2),
            Job(self.unit2, self.phase1, self.date1, self.date2),
            Job(self.unit3, self.phase1, self.date1, self.date2),
        ]
        positions = [
            Position("Position 1", [self.need1], capacity=1),
            Position("Position 2", [self.need2], capacity=4),
        ]
        with self.assertRaises(ValueError):
            validate_capacity_feasibility(
                jobs,
                positions,
                self.compressed_ticks,
                self.tick_to_index,
                self.adapter,
                self.index_to_value,
            )

    def test_multiple_needs_one_position_fails(self):
        """1 units of need1, need2 and need3 respectively are required. There is only one position that can handle
        the 3 needs but has not enough capacity at the same. It should fail
        """
        jobs = [
            Job(self.unit1, self.phase1, self.date1, self.date2),
            Job(self.unit2, self.phase2, self.date1, self.date2),
            Job(self.unit3, self.phase4, self.date1, self.date2),
        ]
        positions = [
            Position("Position 1", [self.need1, self.need2, self.need3], capacity=1),
        ]

        with self.assertRaises(ValueError):
            validate_capacity_feasibility(
                jobs,
                positions,
                self.compressed_ticks,
                self.tick_to_index,
                self.adapter,
                self.index_to_value,
            )

        # Test the opossite pass
        positions[0].capacity = 3

        result = validate_capacity_feasibility(
            jobs,
            positions,
            self.compressed_ticks,
            self.tick_to_index,
            self.adapter,
            self.index_to_value,
        )
        self.assertEqual(result[0]["per_need"][self.need1.name], (3, 1))
        self.assertEqual(result[0]["per_need"][self.need2.name], (3, 1))
        self.assertEqual(result[0]["per_need"][self.need3.name], (3, 1))

    def test_single_need_enough_capacity_pass(self):
        """2 units of need1 is required per day and a position with capacity 2 is given"""
        jobs = [
            Job(self.unit1, self.phase1, self.date1, self.date2),
            Job(self.unit2, self.phase1, self.date1, self.date2),
        ]
        positions = [Position("Position 1", [self.need1], capacity=2)]

        result = validate_capacity_feasibility(
            jobs,
            positions,
            self.compressed_ticks,
            self.tick_to_index,
            self.adapter,
            self.index_to_value,
        )
        self.assertEqual(result[0]["per_need"][self.need1.name], (2, 2))
        self.assertEqual(result[1]["per_need"][self.need1.name], (2, 2))


class TestOverlappingJobValidation(BasicTestSetup):
    """Test validate_non_overlapping_jobs_per_unit function"""

    def test_on_job_overlap_for_same_unit_fails(self):
        # End date exact overlap
        jobs = [
            Job(self.unit1, self.phase1, date(2025, 4, 10), date(2025, 4, 15)),
            Job(self.unit1, self.phase2, date(2025, 4, 15), date(2025, 4, 20)),
        ]
        with self.assertRaises(ValueError):
            validate_non_overlapping_jobs_per_unit(jobs, self.adapter)

        # Start date exact overlap
        jobs = [
            Job(self.unit1, self.phase1, date(2025, 4, 10), date(2025, 4, 15)),
            Job(self.unit1, self.phase2, date(2025, 1, 15), date(2025, 4, 10)),
        ]
        with self.assertRaises(ValueError):
            validate_non_overlapping_jobs_per_unit(jobs, self.adapter)

        # Between start and end date overlap
        jobs = [
            Job(self.unit1, self.phase1, date(2025, 4, 10), date(2025, 4, 15)),
            Job(self.unit1, self.phase2, date(2025, 4, 12), date(2025, 4, 13)),
        ]
        with self.assertRaises(ValueError):
            validate_non_overlapping_jobs_per_unit(jobs, self.adapter)

    def test_when_jobs_do_not_overlap_pass(self):
        # No date overlap
        jobs = [
            Job(self.unit1, self.phase1, date(2025, 4, 10), date(2025, 4, 13)),
            Job(self.unit1, self.phase1, date(2025, 4, 14), date(2025, 4, 20)),
        ]
        validate_non_overlapping_jobs_per_unit(jobs, self.adapter)  # Should not raise

        # Overlap but not the same unit
        jobs = [
            Job(self.unit1, self.phase1, date(2025, 4, 10), date(2025, 4, 15)),
            Job(self.unit2, self.phase1, date(2025, 4, 12), date(2025, 4, 13)),
        ]
        validate_non_overlapping_jobs_per_unit(jobs, self.adapter)  # Should not raise


if __name__ == "__main__":
    unittest.main()
