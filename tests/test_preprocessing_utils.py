from datetime import date
from frjmp.model.sets.job import Job
from frjmp.utils.preprocessing_utils import insert_waiting_jobs
from tests.setup import SharedTestSetup


class TestCapacityValidation(SharedTestSetup):
    def test_insert_waiting_jobs_creates_one_gap(self):
        jobs = [
            Job(self.aircraft1, self.phase1, date(2025, 1, 1), date(2025, 1, 2)),
            Job(self.aircraft1, self.phase2, date(2025, 1, 5), date(2025, 1, 6)),
        ]
        new_jobs = insert_waiting_jobs(jobs, self.waiting_phase)

        self.assertEqual(len(new_jobs), 3)  # One job has been added
        self.assertEqual(new_jobs[2].start, date(2025, 1, 3))
        self.assertEqual(new_jobs[2].end, date(2025, 1, 4))
        self.assertEqual(new_jobs[2].phase, self.waiting_phase)

    def test_insert_waiting_jobs_creates_two_gaps(self):
        jobs = [
            Job(self.aircraft1, self.phase1, date(2025, 1, 1), date(2025, 1, 2)),
            Job(self.aircraft1, self.phase2, date(2025, 1, 5), date(2025, 1, 8)),
            Job(self.aircraft1, self.phase3, date(2025, 2, 5), date(2025, 2, 15)),
        ]
        new_jobs = insert_waiting_jobs(jobs, self.waiting_phase)

        self.assertEqual(len(new_jobs), 5)  # Two jobs have been added
        self.assertEqual(new_jobs[3].start, date(2025, 1, 3))
        self.assertEqual(new_jobs[3].end, date(2025, 1, 4))
        self.assertEqual(new_jobs[3].phase, self.waiting_phase)
        self.assertEqual(new_jobs[4].start, date(2025, 1, 9))
        self.assertEqual(new_jobs[4].end, date(2025, 2, 4))
        self.assertEqual(new_jobs[4].phase, self.waiting_phase)

    def test_insert_waiting_jobs_skips_consecutive_jobs(self):
        jobs = [
            Job(self.aircraft1, self.waiting_phase, date(2025, 1, 1), date(2025, 1, 2)),
            Job(self.aircraft1, self.waiting_phase, date(2025, 1, 3), date(2025, 1, 5)),
        ]
        new_jobs = insert_waiting_jobs(jobs, self.waiting_phase)
        self.assertEqual(len(new_jobs), 2)  # No job has been added
