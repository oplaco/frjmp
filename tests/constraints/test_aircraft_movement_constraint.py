import unittest
from datetime import date

from ortools.sat.python import cp_model

from frjmp.model.constraints.assignment import add_job_assignment_constraints
from frjmp.model.constraints.capacity import add_position_capacity_constraints
from frjmp.model.constraints.movement import (
    add_movement_dependency_constraints,
    add_unit_movement_constraint,
    link_unit_movements_to_position_movements,
)
from frjmp.model.parameters.positions_configuration import PositionsConfiguration
from frjmp.model.parameters.position_unit_model import (
    PositionsUnitTypeDependency,
)
from frjmp.model.adapter import DailyAdapter
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
        self.unit = Unit("AC1", self.unit_model1)
        self.unit2 = Unit("AC2", self.unit_model1)
        self.need = Need("repair")
        self.phase1 = Phase("repair-phase-1", self.need)
        self.phase2 = Phase("repair-phase-2", self.need)

        self.pos1 = Position("Position 1", [self.need], capacity=1)
        self.pos2 = Position("Position 2", [self.need], capacity=1)
        self.pos3 = Position("Position 3", [self.need], capacity=1)
        self.positions = [self.pos1, self.pos2, self.pos3]

        self.adapter = DailyAdapter(origin=date(2025, 4, 10))

    def create_local_problem(self):
        """Create the optimization problem resembling the frjmp.project.Problem object but with ONLY the necessary constraints and variables."""
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

        # Add basic constraints
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

        add_position_capacity_constraints(
            self.model,
            self.assigned_vars,
            self.positions,
            self.jobs,
            self.num_time_steps,
        )

        add_unit_movement_constraint(
            self.model,
            self.pattern_assigned_vars,
            self.unit_movement_vars,
            self.jobs,
            self.num_time_steps,
        )
        link_unit_movements_to_position_movements(
            self.model,
            self.assigned_vars,
            self.movement_in_position_vars,
            self.unit_movement_vars,
            self.jobs,
        )
        pos_unit_model_dependency = PositionsConfiguration(positions=self.positions)
        add_movement_dependency_constraints(
            self.model,
            self.movement_in_position_vars,
            self.unit_movement_vars,
            self.pattern_assigned_vars,
            self.jobs,
            pos_unit_model_dependency,
            self.num_time_steps,
        )

        all_moves = []
        for p_idx, p_dict in self.movement_in_position_vars.items():
            for t_idx, var in p_dict.items():
                all_moves.append(var)

        total_movements = sum(all_moves)
        self.model.Minimize(total_movements)

    def test_movement_detected_when_pattern_changes_same_job(self):
        self.job1 = Job(
            self.unit, self.phase1, self.adapter, date(2025, 4, 10), date(2025, 4, 15)
        )
        self.job3 = Job(
            self.unit2, self.phase2, self.adapter, date(2025, 4, 13), date(2025, 4, 15)
        )
        self.job2 = Job(
            self.unit2, self.phase2, self.adapter, date(2025, 4, 16), date(2025, 4, 20)
        )
        self.jobs = [self.job1, self.job2, self.job3]
        self.create_local_problem()
        # To isolate the movement constraint. Fake the other crucial constraint, the assigment constraint by setting some values.
        # Move assign unit 0 to pos1 in t0 and in pos2 in t1 and t2.
        pattern0 = 0
        pattern1 = 1
        self.model.Add(self.pattern_assigned_vars[0][0][pattern0] == 1)  # t0
        self.model.Add(self.pattern_assigned_vars[0][0][pattern1] == 0)

        self.model.Add(self.pattern_assigned_vars[0][1][pattern0] == 0)
        self.model.Add(self.pattern_assigned_vars[0][1][pattern1] == 1)  # t1

        solver = cp_model.CpSolver()
        status = solver.Solve(self.model)

        # Unit movement.
        self.assertEqual(status, cp_model.OPTIMAL)
        # Movement at t0
        self.assertEqual(solver.Value(self.unit_movement_vars[self.unit.name][0]), 1)
        # No movements at t1
        self.assertEqual(solver.Value(self.unit_movement_vars[self.unit.name][1]), 0)
        # Last time step for this unit is considered a movement because there are no more jobs
        self.assertEqual(solver.Value(self.unit_movement_vars[self.unit.name][2]), 1)

    def test_movement_detected_when_pattern_changes_different_job_same_unit(self):
        self.job1 = Job(
            self.unit, self.phase1, self.adapter, date(2025, 4, 10), date(2025, 4, 15)
        )
        self.job2 = Job(
            self.unit, self.phase2, self.adapter, date(2025, 4, 16), date(2025, 4, 20)
        )
        self.jobs = [self.job1, self.job2]

        self.create_local_problem()
        # To isolate the movement constraint. Fake the other crucial constraint, the assigment constraint by setting some values.
        pp_idx = 0  # previous pattern index
        np_idx = 1  # next pattern index

        job1_idx = 0
        job2_idx = 1

        # Movement between job1_idx and job2_idx from pp_idx in  t0,t1 to np_idx in t2 and t3.
        self.model.Add(
            self.pattern_assigned_vars[job1_idx][0][pp_idx] == 1
        )  # t0 = pp_idx
        self.model.Add(
            self.pattern_assigned_vars[job1_idx][1][pp_idx] == 1
        )  # t1 = pp_idx

        self.model.Add(
            self.pattern_assigned_vars[job2_idx][2][np_idx] == 1
        )  # t3 = np_idx
        self.model.Add(
            self.pattern_assigned_vars[job2_idx][3][np_idx] == 1
        )  # t4 = np_idx

        solver = cp_model.CpSolver()
        status = solver.Solve(self.model)

        self.assertEqual(status, cp_model.OPTIMAL)
        # job j=0 and j=1 belong to the same unit
        self.assertEqual(self.jobs[0].unit.name, self.jobs[1].unit.name)
        # Should detect movement at t1
        self.assertEqual(solver.Value(self.unit_movement_vars[self.unit.name][1]), 1)
        # No movement at t0,t2 and t3
        for t in [0, 2, 3]:
            self.assertEqual(
                solver.Value(self.unit_movement_vars[self.unit.name][t]), 0
            )

    def test_link_between_unit_movement_and_position_movement_direct(self):
        """An unit movement between t and t+1 (i.e at t) between position p and p' must enforce
        a position movement at t in both p and p'.
        """
        self.job1 = Job(
            self.unit, self.phase1, self.adapter, date(2025, 4, 10), date(2025, 4, 15)
        )
        self.job2 = Job(
            self.unit, self.phase2, self.adapter, date(2025, 4, 16), date(2025, 4, 20)
        )
        self.jobs = [self.job1, self.job2]

        self.create_local_problem()

        # Create movement from pattern 0 (Position 1) to pattern 1 (Position 2) between t and t+1
        t_idx = 0
        unit_name = self.unit.name
        pp_idx = 0  # previous position index
        np_idx = 1  # next position index
        self.model.Add(self.unit_movement_vars[unit_name][t_idx] == 1)
        self.model.Add(self.pattern_assigned_vars[0][t_idx][0] == 1)
        self.model.Add(self.pattern_assigned_vars[0][t_idx + 1][1] == 1)

        solver = cp_model.CpSolver()
        status = solver.Solve(self.model)

        self.assertEqual(status, cp_model.OPTIMAL)
        # There is a position movement in both the previous and target positions of the movement at t0.
        self.assertEqual(solver.Value(self.movement_in_position_vars[pp_idx][0]), 1)
        self.assertEqual(solver.Value(self.movement_in_position_vars[np_idx][0]), 1)

        # There is no position movement at the target position at t1 as the unit is assigned.
        self.assertEqual(solver.Value(self.movement_in_position_vars[np_idx][1]), 0)

    def test_link_between_unit_movement_and_position_movement_reverse(self):
        """On the contrary, if there is a movement in postion p at time t. There is only an unit movement
        if any of the jobs of that unit is assigned to that position according to assigned_var[j][p][t] (for all j).
        """
        self.job1 = Job(
            self.unit, self.phase1, self.adapter, date(2025, 4, 10), date(2025, 4, 15)
        )
        self.job2 = Job(
            self.unit, self.phase2, self.adapter, date(2025, 4, 16), date(2025, 4, 20)
        )
        self.jobs = [self.job1, self.job2]

        self.create_local_problem()

        # Create position movement assigment and pattern assignments.
        t0_idx = 0
        unit_name = self.unit.name
        source_pattern_idx = 0
        target_pattern_idx = 1
        source_pattern = self.unit.type.allowed_patterns[source_pattern_idx]
        target_pattern = self.unit.type.allowed_patterns[target_pattern_idx]

        self.model.Add(self.pattern_assigned_vars[0][t0_idx][source_pattern_idx] == 1)
        for pos in source_pattern.positions + target_pattern.positions:
            pos_idx = self.positions.index(pos)
            self.model.Add(self.movement_in_position_vars[pos_idx][t0_idx] == 1)

        solver = cp_model.CpSolver()
        status = solver.Solve(self.model)

        self.assertEqual(status, cp_model.OPTIMAL)
        # There is an unit movement at t0 as there are two positions movements at t0 and one unit is assigned to one of those positions.
        self.assertEqual(solver.Value(self.unit_movement_vars[unit_name][t0_idx]), 1)
