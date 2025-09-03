import unittest
from datetime import date

from frjmp.model.adapter import DailyAdapter
from frjmp.model.problem import Problem
from frjmp.model.sets.unit import Unit, UnitType
from frjmp.model.sets.need import Need
from frjmp.model.sets.job import Job
from frjmp.model.sets.phase import Phase
from frjmp.model.sets.position import Position
from frjmp.model.parameters.positions_configuration import PositionsConfiguration
from frjmp.model.parameters.position_unit_model import (
    PositionsUnitTypeDependency,
)


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

        self.adapter = DailyAdapter(self.date1)

        self.unit_model = UnitType("C295")
        self.unit_types = [self.unit_model]
        self.unit1 = Unit("MSN 001", self.unit_model)
        self.unit2 = Unit("MSN 002", self.unit_model)
        self.unit3 = Unit("MSN 003", self.unit_model)
        self.unit4 = Unit("MSN 004", self.unit_model)


class ProblemTestSetup(BasicTestSetup):
    def setUp(self):
        super().setUp()
        job1 = Job(self.unit1, self.phase1, self.adapter, self.date1, self.date3)
        job2 = Job(self.unit2, self.phase1, self.adapter, self.date1, self.date2)
        job3 = Job(self.unit3, self.phase1, self.adapter, self.date1, self.date2)
        self.jobs = [job1, job2, job3]
        self.position1 = Position("Position 1", [self.need1], capacity=1)
        self.position2 = Position("Position 2", [self.need1], capacity=1)
        self.position3 = Position("Position 3", [self.need1], capacity=1)
        self.position4 = Position("Position 4", [self.need1], capacity=1)
        positions = [self.position1, self.position2, self.position3, self.position4]
        self.pc = PositionsConfiguration(positions=positions)
        self.pud = PositionsUnitTypeDependency(self.unit_types, positions)
        self.t_init = self.date1
        self.adapter = DailyAdapter(self.t_init)
        self.problem = Problem(self.jobs, self.pc, self.pud, self.adapter)
