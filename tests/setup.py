import unittest
from datetime import date

from frjmp.model.sets.phase import Phase
from frjmp.model.sets.need import Need
from frjmp.model.sets.aircraft import Aircraft


class SharedTestSetup(unittest.TestCase):
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

        # Avoid using compressed dates function and adding a dependency
        self.compressed_dates = [self.date1, self.date2, self.date3, self.date4]
        self.date_to_index = {d: i for i, d in enumerate(self.compressed_dates)}

        self.aircraft1 = Aircraft("MSN 001")
        self.aircraft2 = Aircraft("MSN 002")
        self.aircraft3 = Aircraft("MSN 003")
