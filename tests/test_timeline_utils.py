import unittest
from datetime import date

from frjmp.utils.timeline_utils import compress_dates, trim_jobs_before_t0_inplace
from frjmp.model.sets.job import Job
from frjmp.model.sets.phase import Phase
from frjmp.model.sets.need import Need
from frjmp.model.sets.aircraft import Aircraft


class TestCompressDates(unittest.TestCase):
    def test_compression_pass(self):
        # Setup
        aircraft = Aircraft("185")
        wp = Need("WP")
        phase1 = Phase("4Y", wp)
        phase2 = Phase("WP", wp)

        job1 = Job(aircraft, phase1, date(2024, 12, 1), date(2028, 4, 18))
        job2 = Job(aircraft, phase2, date(2025, 4, 16), date(2027, 7, 20))

        compressed, date_to_index, index_to_date = compress_dates([job1, job2])

        # Assert correct compression
        self.assertEqual(
            compressed,
            sorted(set([job1.start, job1.end, job2.start, job2.end])),
        )
        self.assertEqual(date_to_index[job1.start], 0)
        self.assertTrue(date_to_index[job2.end] in range(len(compressed)))
        self.assertEqual(
            index_to_date[date_to_index[date(2025, 4, 16)]], date(2025, 4, 16)
        )

    def test_trim_jobs_pass(self):
        aircraft = Aircraft("185")
        wp = Need("WP")
        phase = Phase("4Y", wp)

        t0 = date(2025, 7, 1)
        # end < t0. Should be removed.
        job1 = Job(aircraft, phase, date(2025, 1, 2), date(2025, 4, 18))
        # start < t0 < end. Start should be set to t0.
        job2 = Job(aircraft, phase, date(2025, 4, 16), date(2025, 7, 20))
        # start > t0. Should be left unmodified.
        job3 = Job(aircraft, phase, date(2025, 7, 16), date(2025, 7, 20))

        jobs = [job1, job2, job3]
        trim_jobs_before_t0_inplace(jobs, t0)
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
