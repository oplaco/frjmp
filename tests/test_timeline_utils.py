import unittest
from datetime import date

from frjmp.utils.timeline_utils import compress_dates
from frjmp.model.sets.job import Job
from frjmp.model.sets.phase import Phase
from frjmp.model.sets.need import Need
from frjmp.model.sets.aircraft import Aircraft


class TestCompressDates(unittest.TestCase):
    def test_compression_works(self):
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


if __name__ == "__main__":
    unittest.main()
