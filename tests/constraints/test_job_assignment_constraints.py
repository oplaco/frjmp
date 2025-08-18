import unittest
from datetime import date

from ortools.sat.python import cp_model

from frjmp.model.adapter import DailyAdapter
from frjmp.model.constraints.assignment import add_job_assignment_constraints
from frjmp.model.parameters.position_unit_model import (
    Pattern,
    PositionsUnitTypeDependency,
)
from frjmp.model.sets.unit import Unit, UnitType
from frjmp.model.sets.job import Job
from frjmp.model.sets.need import Need
from frjmp.model.sets.phase import Phase
from frjmp.model.sets.position import Position
from frjmp.model.variables.assignment import create_assignment_variables
from frjmp.model.variables.movement import (
    create_unit_movement_variables,
    create_movement_in_position_variables,
)
from frjmp.model.variables.pattern_assignment import create_pattern_assignment_variables
from frjmp.utils.timeline_utils import compress_timepoints
from frjmp.utils.validation_utils import validate_capacity_feasibility


class TestJobAssignmentConstraints(unittest.TestCase):
    def setUp(self):
        self.unit_model1 = UnitType("C295")
        self.unit_model2 = UnitType("A400M")
        self.unit_types = [self.unit_model1, self.unit_model2]

        self.unit1 = Unit("AC1", self.unit_model1)
        self.unit2 = Unit("AC2", self.unit_model2)
        self.unit3 = Unit("AC3", self.unit_model2)

        self.need1 = Need("repair")
        self.need2 = Need("overhaul")
        self.need3 = Need("fal")

        self.phase1 = Phase("repair-phase", self.need1)
        self.phase2 = Phase("overhaul-phase", self.need2)
        self.phase3 = Phase("fal", self.need3)

        self.job1 = Job(self.unit1, self.phase1, date(2025, 4, 10), date(2025, 4, 12))
        self.job2 = Job(self.unit1, self.phase1, date(2025, 4, 17), date(2025, 4, 20))

        self.job3 = Job(self.unit2, self.phase1, date(2025, 4, 21), date(2025, 4, 30))

        self.job4 = Job(self.unit3, self.phase1, date(2025, 4, 27), date(2025, 5, 5))

        self.jobs = [self.job1, self.job2, self.job3, self.job4]
        self.adapter = DailyAdapter(origin=date(2024, 1, 1))

        self.pos1 = Position(
            "Position 1", [self.need1, self.need2, self.need3], capacity=1
        )
        self.pos2 = Position(
            "Position 2", [self.need1, self.need2, self.need3], capacity=1
        )
        self.pos3 = Position(
            "Position 3", [self.need1, self.need2, self.need3], capacity=1
        )
        self.pos4 = Position(
            "Hangar D", [self.need1, self.need2, self.need3], capacity=1
        )
        self.positions = [self.pos1, self.pos2, self.pos3, self.pos4]

        # Calculate compressed time scale
        compressed_ticks, tick_to_index, index_to_tick, index_to_value = (
            compress_timepoints(self.jobs, self.adapter)
        )
        self.compressed_ticks = compressed_ticks
        self.tick_to_index = tick_to_index
        self.index_to_tick = index_to_tick
        self.index_to_value = index_to_value
        # Currently use compressed dates as time_step_indexes in the future they might be actual int values
        self.time_step_indexes = list(range(len(compressed_ticks)))

        self.model = cp_model.CpModel()

    def create_local_problem(self):
        """Create the optimization problem resembling the frjmp.project.Problem object but with ONLY the necessary constraints and variables."""
        validate_capacity_feasibility(
            self.jobs,
            self.positions,
            self.compressed_ticks,
            self.tick_to_index,
            self.adapter,
            self.index_to_value,
        )
        self.unit_movement_vars = create_unit_movement_variables(
            self.model, self.jobs, self.time_step_indexes
        )

        self.assigned_vars = create_assignment_variables(
            self.model,
            self.jobs,
            self.positions,
            self.compressed_dates,
            self.date_to_index,
        )

        self.movement_in_position_vars = create_movement_in_position_variables(
            self.model, self.positions, self.time_step_indexes
        )

        pos_unit_model_dependency = PositionsUnitTypeDependency(
            self.unit_types, self.positions
        )

        self.pattern_assigned_vars = create_pattern_assignment_variables(
            self.model,
            self.jobs,
            self.compressed_dates,
            self.date_to_index,
            pos_unit_model_dependency,
            self.assigned_vars,
        )

        # Add basic constraints
        add_job_assignment_constraints(
            self.model,
            self.assigned_vars,
            self.pattern_assigned_vars,
            self.jobs,
            self.positions,
            self.date_to_index,
            self.time_step_indexes,
            pos_unit_model_dependency,
        )
        # We intentionally skip capcity constraint and movement constraints as we only want to validate assignment-related conditions.

    def test_link_pattern_assigment(self):
        """Create a pattern containing three positions.
        Force the assignment of one job with an unit model that contains that unit model to one position.
        Test if the constraint assign the job to the other two positions as well."""

        pattern = Pattern([self.pos1, self.pos2, self.pos3])
        self.unit_model2.add_pattern(pattern)

        self.create_local_problem()

        # Job j 2 uses pattern.
        job3_start_idx = self.date_to_index.get(self.job3.start)
        self.model.Add(self.assigned_vars[2][0][job3_start_idx] == 1)

        solver = cp_model.CpSolver()
        status = solver.Solve(self.model)

        self.assertEqual(status, cp_model.OPTIMAL)
        self.assertEqual(solver.Value(self.assigned_vars[2][1][job3_start_idx]), 1)
        self.assertEqual(solver.Value(self.assigned_vars[2][2][job3_start_idx]), 1)
        self.assertEqual(solver.Value(self.assigned_vars[2][3][job3_start_idx]), 0)

    def test_link_pattern_assigment_2(self):
        """Create a pattern containing three positions.
        Force the pattern assignment of one job. See if it triggers the individual assignments.
        """

        pattern = Pattern([self.pos1, self.pos2, self.pos3])
        self.unit_model2.add_pattern(pattern)

        self.create_local_problem()

        j_idx = 2  # job3 uses unit_model_2
        t_idx = self.date_to_index.get(self.job3.start)  # Starting date of job3
        k_idx = 0  # There is only one defined pattern
        self.model.Add(self.pattern_assigned_vars[j_idx][t_idx][k_idx] == 1)

        solver = cp_model.CpSolver()
        status = solver.Solve(self.model)

        # Check if in t_idx, j_idx is assigned to all the positions of its pattern.
        self.assertEqual(status, cp_model.OPTIMAL)
        self.assertEqual(solver.Value(self.assigned_vars[j_idx][0][t_idx]), 1)
        self.assertEqual(solver.Value(self.assigned_vars[j_idx][1][t_idx]), 1)
        self.assertEqual(solver.Value(self.assigned_vars[j_idx][2][t_idx]), 1)
        self.assertEqual(solver.Value(self.assigned_vars[j_idx][3][t_idx]), 0)


if __name__ == "__main__":
    unittest.main()
