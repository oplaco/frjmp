import unittest
from datetime import date

from ortools.sat.python import cp_model

from frjmp.model.constraints.assignment import add_job_assignment_constraints
from frjmp.model.constraints.capacity import add_position_capacity_constraints
from frjmp.model.constraints.movement import (
    add_movement_dependency_constraints,
    add_aircraft_movement_constraint,
    link_aircraft_movements_to_position_movements,
)
from frjmp.model.parameters.positions_configuration import PositionsConfiguration
from frjmp.model.parameters.position_aircraft_model import (
    PositionsAircraftModelDependency,
)
from frjmp.model.sets.aircraft import Aircraft, AircraftModel
from frjmp.model.sets.job import Job
from frjmp.model.sets.need import Need
from frjmp.model.sets.phase import Phase
from frjmp.model.sets.position import Position
from frjmp.model.variables.assignment import create_assignment_variables
from frjmp.model.variables.movement import (
    create_aircraft_movement_variables,
    create_movement_in_position_variables,
)
from frjmp.model.variables.pattern_assignment import create_pattern_assignment_variables
from frjmp.utils.timeline_utils import compress_dates


class TestMovementConstraint(unittest.TestCase):
    def setUp(self):
        self.aircraft_model1 = AircraftModel("C295")
        self.aircraft_models = [self.aircraft_model1]
        self.aircraft = Aircraft("AC1", self.aircraft_model1)
        self.aircraft2 = Aircraft("AC2", self.aircraft_model1)
        self.need = Need("repair")
        self.phase1 = Phase("repair-phase-1", self.need)
        self.phase2 = Phase("repair-phase-2", self.need)

        self.pos1 = Position("Hangar A", [self.need], capacity=1)
        self.pos2 = Position("Hangar B", [self.need], capacity=1)
        self.pos3 = Position("Hangar C", [self.need], capacity=1)
        self.positions = [self.pos1, self.pos2, self.pos3]

    def create_local_problem(self):
        """Create the optimization problem resembling the frjmp.project.Problem object but with ONLY the necessary constraints and variables."""
        # Calculate compressed time scale
        compressed_dates, date_to_index, index_to_date = compress_dates(self.jobs)
        self.compressed_dates = compressed_dates
        self.date_to_index = date_to_index
        self.index_to_date = index_to_date
        # Currently use compressed dates as time_step_indexes in the future they might be actual int values
        self.time_step_indexes = compressed_dates

        self.model = cp_model.CpModel()

        self.aircraft_movement_vars = create_aircraft_movement_variables(
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

        pos_aircraft_model_dependency = PositionsAircraftModelDependency(
            self.aircraft_models, self.positions
        )

        self.pattern_assigned_vars = create_pattern_assignment_variables(
            self.model,
            self.jobs,
            self.compressed_dates,
            self.date_to_index,
            pos_aircraft_model_dependency,
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
            pos_aircraft_model_dependency,
        )

        add_position_capacity_constraints(
            self.model,
            self.assigned_vars,
            self.positions,
            self.jobs,
            num_timesteps=len(self.time_step_indexes),
        )

        add_aircraft_movement_constraint(
            self.model,
            self.pattern_assigned_vars,
            self.aircraft_movement_vars,
            self.jobs,
            num_timesteps=len(self.time_step_indexes),
        )
        link_aircraft_movements_to_position_movements(
            self.model,
            self.assigned_vars,
            self.movement_in_position_vars,
            self.aircraft_movement_vars,
            self.jobs,
        )
        pos_aircraft_model_dependency = PositionsConfiguration(positions=self.positions)
        add_movement_dependency_constraints(
            self.model,
            self.movement_in_position_vars,
            pos_aircraft_model_dependency,
            num_timesteps=len(self.time_step_indexes),
        )

        all_moves = []
        for p_idx, p_dict in self.movement_in_position_vars.items():
            for t_idx, var in p_dict.items():
                all_moves.append(var)

        total_movements = sum(all_moves)
        self.model.Minimize(total_movements)

    def test_movement_detected_when_pattern_changes_same_job(self):
        self.job1 = Job(
            self.aircraft, self.phase1, date(2025, 4, 10), date(2025, 4, 15)
        )
        self.job3 = Job(
            self.aircraft2, self.phase2, date(2025, 4, 13), date(2025, 4, 15)
        )
        self.job2 = Job(
            self.aircraft2, self.phase2, date(2025, 4, 16), date(2025, 4, 20)
        )
        self.jobs = [self.job1, self.job2, self.job3]
        self.create_local_problem()
        # To isolate the movement constraint. Fake the other crucial constraint, the assigment constraint by setting some values.
        # Move assign aircraft 0 to pos1 in t0 and in pos2 in t1 and t2.
        pattern0 = 0
        pattern1 = 1
        self.model.Add(self.pattern_assigned_vars[0][0][pattern0] == 1)  # t0
        self.model.Add(self.pattern_assigned_vars[0][0][pattern1] == 0)

        self.model.Add(self.pattern_assigned_vars[0][1][pattern0] == 0)
        self.model.Add(self.pattern_assigned_vars[0][1][pattern1] == 1)  # t1

        solver = cp_model.CpSolver()
        status = solver.Solve(self.model)

        # Aircraft movement.
        self.assertEqual(status, cp_model.OPTIMAL)
        # Movement at t0
        self.assertEqual(
            solver.Value(self.aircraft_movement_vars[self.aircraft.name][0]), 1
        )
        # No movements at t1
        self.assertEqual(
            solver.Value(self.aircraft_movement_vars[self.aircraft.name][1]), 0
        )
        # Last time step for this aircraft is considered a movement because there are no more jobs
        self.assertEqual(
            solver.Value(self.aircraft_movement_vars[self.aircraft.name][2]), 1
        )

    def test_movement_detected_when_pattern_changes_different_job_same_aircraft(self):
        self.job1 = Job(
            self.aircraft, self.phase1, date(2025, 4, 10), date(2025, 4, 15)
        )
        self.job2 = Job(
            self.aircraft, self.phase2, date(2025, 4, 16), date(2025, 4, 20)
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
        # job j=0 and j=1 belong to the same aircraft
        self.assertEqual(self.jobs[0].aircraft.name, self.jobs[1].aircraft.name)
        # Should detect movement at t1
        self.assertEqual(
            solver.Value(self.aircraft_movement_vars[self.aircraft.name][1]), 1
        )
        # No movement at t0,t2 and t3
        for t in [0, 2, 3]:
            self.assertEqual(
                solver.Value(self.aircraft_movement_vars[self.aircraft.name][t]), 0
            )

    def test_link_between_aircraft_movement_and_position_movement_direct(self):
        """An aircraft movement between t and t+1 (i.e at t) between position p and p' must enforce
        a position movement at t in both p and p'.
        """
        self.job1 = Job(
            self.aircraft, self.phase1, date(2025, 4, 10), date(2025, 4, 15)
        )
        self.job2 = Job(
            self.aircraft, self.phase2, date(2025, 4, 16), date(2025, 4, 20)
        )
        self.jobs = [self.job1, self.job2]

        self.create_local_problem()

        # Create movement from pattern 0 (Hangar A) to pattern 1 (Hangar B) between t and t+1
        t_idx = 0
        aircraft_name = self.aircraft.name
        pp_idx = 0  # previous position index
        np_idx = 1  # next position index
        self.model.Add(self.aircraft_movement_vars[aircraft_name][t_idx] == 1)
        self.model.Add(self.pattern_assigned_vars[0][t_idx][0] == 1)
        self.model.Add(self.pattern_assigned_vars[0][t_idx + 1][1] == 1)

        solver = cp_model.CpSolver()
        status = solver.Solve(self.model)

        self.assertEqual(status, cp_model.OPTIMAL)
        # There is a position movement in both the previous and target positions of the movement at t0.
        self.assertEqual(solver.Value(self.movement_in_position_vars[pp_idx][0]), 1)
        self.assertEqual(solver.Value(self.movement_in_position_vars[np_idx][0]), 1)

        # There is no position movement at the target position at t1 as the aircraft is assigned.
        self.assertEqual(solver.Value(self.movement_in_position_vars[np_idx][1]), 0)

    def test_link_between_aircraft_movement_and_position_movement_reverse(self):
        """On the contrary, if there is a movement in postion p at time t. There is only an aircraft movement
        if any of the jobs of that aircraft is assigned to that position according to assigned_var[j][p][t] (for all j).
        """
        self.job1 = Job(
            self.aircraft, self.phase1, date(2025, 4, 10), date(2025, 4, 15)
        )
        self.job2 = Job(
            self.aircraft, self.phase2, date(2025, 4, 16), date(2025, 4, 20)
        )
        self.jobs = [self.job1, self.job2]

        self.create_local_problem()

        # Create position movement assigment and pattern assignments.
        t0_idx = 0
        aircraft_name = self.aircraft.name
        source_pattern_idx = 0
        target_pattern_idx = 1
        source_pattern = self.aircraft.model.allowed_patterns[source_pattern_idx]
        target_pattern = self.aircraft.model.allowed_patterns[target_pattern_idx]

        self.model.Add(self.pattern_assigned_vars[0][t0_idx][source_pattern_idx] == 1)
        for pos in source_pattern.positions + target_pattern.positions:
            pos_idx = self.positions.index(pos)
            self.model.Add(self.movement_in_position_vars[pos_idx][t0_idx] == 1)

        solver = cp_model.CpSolver()
        status = solver.Solve(self.model)

        self.assertEqual(status, cp_model.OPTIMAL)
        # There is an aircraft movement at t0 as there are two positions movements at t0 and one aircraft is assigned to one of those positions.
        self.assertEqual(
            solver.Value(self.aircraft_movement_vars[aircraft_name][t0_idx]), 1
        )
