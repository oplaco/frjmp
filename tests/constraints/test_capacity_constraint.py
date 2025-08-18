import unittest
from datetime import date

from ortools.sat.python import cp_model

from frjmp.model.adapter import DailyAdapter
from frjmp.model.constraints.assignment import add_job_assignment_constraints
from frjmp.model.constraints.capacity import add_position_capacity_constraints
from frjmp.model.parameters.position_unit_model import (
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


class TestMovementConstraint(unittest.TestCase):
    def setUp(self):
        self.unit_model1 = UnitType("C295")
        self.unit_types = [self.unit_model1]
        self.unit1 = Unit("AC1", self.unit_model1)
        self.unit2 = Unit("AC2", self.unit_model1)
        self.need = Need("repair")
        self.phase = Phase("repair-phase", self.need)

        self.job1 = Job(self.unit1, self.phase, date(2025, 4, 10), date(2025, 4, 15))
        self.job2 = Job(self.unit2, self.phase, date(2025, 4, 10), date(2025, 4, 15))
        self.jobs = [self.job1, self.job2]

        self.adapter = DailyAdapter(date(2025, 4, 10))

        self.pos1 = Position("Position 1", [self.need], capacity=1)
        self.pos2 = Position("Position 2", [self.need], capacity=1)
        self.positions = [self.pos1, self.pos2]

        # Calculate compressed time scale
        compressed_ticks, tick_to_index, index_to_tick, index_to_value = (
            compress_timepoints(self.jobs, self.adapter)
        )
        self.compressed_ticks = compressed_ticks
        self.tick_to_index = tick_to_index
        self.index_to_tick = index_to_tick
        self.index_to_value = index_to_value

        self.time_step_indexes = list(range(len(compressed_ticks)))
        self.num_time_steps = len(self.time_step_indexes)

    def create_local_problem(self):
        """Create the optimization problem resembling the frjmp.project.Problem object but with ONLY the necessary constraints and variables."""
        self.model = cp_model.CpModel()
        self.unit_movement_vars = create_unit_movement_variables(
            self.model, self.jobs, self.num_time_steps
        )

        self.assigned_vars = create_assignment_variables(
            self.model,
            self.jobs,
            self.positions,
            self.compressed_ticks,
            self.tick_to_index,
            self.adapter,
        )

        self.movement_in_position_vars = create_movement_in_position_variables(
            self.model, self.positions, self.num_time_steps
        )

        pos_unit_model_dependency = PositionsUnitTypeDependency(
            self.unit_types, self.positions
        )

        self.pattern_assigned_vars = create_pattern_assignment_variables(
            self.model,
            self.jobs,
            self.compressed_ticks,
            self.tick_to_index,
            pos_unit_model_dependency,
            self.assigned_vars,
            self.adapter,
        )

        # Add basic assigment constraints.
        add_job_assignment_constraints(
            self.model,
            self.assigned_vars,
            self.pattern_assigned_vars,
            self.jobs,
            self.positions,
            self.tick_to_index,
            self.compressed_ticks,
            pos_unit_model_dependency,
            self.adapter,
        )

        # Add capacity constraint that needs assigment constraint to make sense.
        add_position_capacity_constraints(
            self.model,
            self.assigned_vars,
            self.positions,
            self.jobs,
            self.num_time_steps,
        )

    def test_capacity_constraint_surpass(self):
        self.create_local_problem()
        # Create two assigments of different jobs in the same position and time step. Hence surpassing the position capacity.
        self.model.Add(self.assigned_vars[0][0][0] == 1)
        self.model.Add(self.assigned_vars[1][0][0] == 1)

        solver = cp_model.CpSolver()
        status = solver.Solve(self.model)

        # The problem proves to be unfeasible
        self.assertEqual(status, cp_model.INFEASIBLE)

    def test_capacity_constraint_valid(self):
        # Increasing default the capacity of position 1 to 2.
        self.pos1.capacity = 2
        self.create_local_problem()

        # Create two assigments of different jobs in the same position and time step.
        self.model.Add(self.assigned_vars[0][0][0] == 1)
        self.model.Add(self.assigned_vars[1][0][0] == 1)

        solver = cp_model.CpSolver()
        status = solver.Solve(self.model)

        # The problem can be solved with optimal results.
        self.assertEqual(status, cp_model.OPTIMAL)
