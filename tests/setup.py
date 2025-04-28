import unittest
from datetime import date

from frjmp.model.problem import Problem
from frjmp.model.sets.aircraft import Aircraft
from frjmp.model.sets.need import Need
from frjmp.model.sets.job import Job
from frjmp.model.sets.phase import Phase
from frjmp.model.sets.position import Position


"""Classes with setup methods that already include information we can reuse between test cases.
"""


class BasicTestSetup(unittest.TestCase):
    def setUp(self):
        self.need1 = Need("E")
        self.need2 = Need("WP")
        self.need3 = Need("H")
        self.need4 = Need("F")

        self.phase1 = Phase("EDV", self.need1)
        self.phase2 = Phase("4Y", self.need2)
        self.phase3 = Phase("WP", self.need2)
        self.phase4 = Phase("ACCEPTANCE", self.need3)
        self.phase5 = Phase("DGAM", self.need3)
        self.phase6 = Phase("ST75", self.need4)
        self.waiting_phase = Phase("WAITING", self.need2)

        self.date1 = date(2025, 1, 25)
        self.date2 = date(2025, 2, 1)
        self.date3 = date(2025, 2, 12)
        self.date4 = date(2025, 3, 4)

        self.aircraft1 = Aircraft("MSN 001")
        self.aircraft2 = Aircraft("MSN 002")
        self.aircraft3 = Aircraft("MSN 003")


class ProblemTestSetup(BasicTestSetup):
    def setUp(self):
        super().setUp()
        job1 = Job(self.aircraft1, self.phase1, self.date1, self.date3)
        job2 = Job(self.aircraft2, self.phase1, self.date1, self.date2)
        job3 = Job(self.aircraft3, self.phase1, self.date1, self.date2)
        jobs = [job1, job2, job3]
        self.position1 = Position("Hangar A", [self.need1], capacity=1)
        self.position2 = Position("Hangar B", [self.need1], capacity=1)
        self.position3 = Position("Hangar C", [self.need1], capacity=1)
        positions = [self.position1, self.position2, self.position3]
        t0 = self.date1
        self.problem = Problem(jobs, positions, t0)
