import unittest
from datetime import date

from frjmp.utils.timeline_utils import (
    trim_jobs_before_time_inplace,
    compress_timepoints,
)

from frjmp.model.adapter import DailyAdapter
from frjmp.model.sets.job import Job
from frjmp.model.sets.phase import Phase
from frjmp.model.sets.need import Need
from frjmp.model.sets.unit import Unit, UnitType


class TestCompressTimepoints(unittest.TestCase):
    def test_compression_pass(self):
        # Setup
        model = UnitType("C295")
        unit = Unit("185", model)
        wp = Need("WP")
        phase1 = Phase("4Y", wp)
        phase2 = Phase("WP", wp)

        job1 = Job(unit, phase1, date(2024, 12, 1), date(2028, 4, 18))
        job2 = Job(unit, phase2, date(2025, 4, 16), date(2027, 7, 20))
        job3 = Job(unit, phase2, date(2025, 5, 16), date(2027, 6, 20))

        adapter = DailyAdapter(origin=date(2024, 1, 1))
        compressed, tick_to_index, index_to_tick, index_to_value = compress_timepoints(
            [job1, job2, job3], adapter=adapter
        )

        # Convert relevant dates to ticks
        ticks = {
            adapter.to_tick(job1.start),
            adapter.to_tick(job1.end),
            adapter.to_tick(job2.start),
            adapter.to_tick(job2.end),
            adapter.to_tick(job3.start),
            adapter.to_tick(job3.end),
        }

        # Assert compressed ticks match expected
        self.assertEqual(compressed, sorted(ticks))
        for tick in ticks:
            index = tick_to_index[tick]
            self.assertEqual(index_to_tick[index], tick)
            self.assertEqual(adapter.to_tick(index_to_value[index]), tick)

    def test_trim_jobs_pass(self):
        model = UnitType("C295")
        unit = Unit("185", model)
        wp = Need("WP")
        phase = Phase("4Y", wp)

        t0 = date(2025, 7, 1)
        adapter = DailyAdapter(t0)

        # end < t0. Should be removed.
        job1 = Job(unit, phase, date(2025, 1, 2), date(2025, 4, 18))
        # start < t0 < end. Start should be set to t0.
        job2 = Job(unit, phase, date(2025, 4, 16), date(2025, 7, 20))
        # start > t0. Should be left unmodified.
        job3 = Job(unit, phase, date(2025, 7, 16), date(2025, 7, 20))

        jobs = [job1, job2, job3]
        trim_jobs_before_time_inplace(jobs, t0, adapter)
        self.assertEqual(len(jobs), 2)  # Len expected to be 2 (job1 removed).
        self.assertFalse(job1 in jobs)  # job1 should no longer be in jobs.
        self.assertTrue(job2 and job3 in jobs)  # job2 and job3 should be in jobs.
        self.assertEqual(
            jobs[0].start, t0
        )  # job2.start should have been updatedt to t2.
        self.assertEqual(
            jobs[1].start, date(2025, 7, 16)
        )  # job3.start should have remain unmodified.


if __name__ == "__main__":
    unittest.main()
