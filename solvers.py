from ortools.linear_solver import pywraplp
from ortools.constraint_solver import pywrapcp
from ortools.constraint_solver import routing_enums_pb2
from ortools.constraint_solver import pywrapcp
import numpy as np

# Linear Programming Solver
def solve_linear_program(objective_coeffs, constraint_coeffs, bounds):
    solver = pywraplp.Solver.CreateSolver('GLOP')
    if not solver:
        return None, "Solver creation failed"

    num_vars = len(objective_coeffs)
    x = [solver.NumVar(0, solver.infinity(), f'x{i}') for i in range(num_vars)]
    solver.Maximize(solver.Sum(objective_coeffs[i] * x[i] for i in range(num_vars)))

    for coeff, bound in zip(constraint_coeffs, bounds):
        solver.Add(solver.Sum(coeff[i] * x[i] for i in range(num_vars)) <= bound)

    status = solver.Solve()

    if status == pywraplp.Solver.OPTIMAL:
        result = {
            'objective_value': solver.Objective().Value(),
            'variable_values': [var.solution_value() for var in x]
        }
        return result, "Optimal solution found"
    else:
        return None, "No optimal solution found"

# Mixed-Integer Programming Solver
def solve_mixed_integer_program(objective_coeffs, constraint_coeffs, bounds, integer_indices):
    solver = pywraplp.Solver.CreateSolver('CBC')
    if not solver:
        return None, "Solver creation failed"

    num_vars = len(objective_coeffs)
    x = []
    for i in range(num_vars):
        if i in integer_indices:
            x.append(solver.IntVar(0, solver.infinity(), f'x{i}'))
        else:
            x.append(solver.NumVar(0, solver.infinity(), f'x{i}'))

    solver.Maximize(solver.Sum(objective_coeffs[i] * x[i] for i in range(num_vars)))

    for coeff, bound in zip(constraint_coeffs, bounds):
        solver.Add(solver.Sum(coeff[i] * x[i] for i in range(num_vars)) <= bound)

    status = solver.Solve()

    if status == pywraplp.Solver.OPTIMAL:
        result = {
            'objective_value': solver.Objective().Value(),
            'variable_values': [var.solution_value() for var in x]
        }
        return result, "Optimal solution found"
    else:
        return None, "No optimal solution found"

# Constraint Programming Solver
def solve_constraint_programming(variables, constraints):
    solver = pywrapcp.Solver('constraint_programming')
    decision_builder = solver.Phase(variables, solver.CHOOSE_FIRST_UNBOUND, solver.ASSIGN_MIN_VALUE)

    solver.NewSearch(decision_builder)
    solutions = []
    while solver.NextSolution():
        solution = [var.Value() for var in variables]
        solutions.append(solution)

    solver.EndSearch()

    if solutions:
        return solutions, "Solutions found"
    else:
        return None, "No solution found"

# Vehicle Routing Problem Solver
def solve_vehicle_routing_problem(distance_matrix, num_vehicles, depot):
    manager = pywrapcp.RoutingIndexManager(len(distance_matrix), num_vehicles, depot)
    routing = pywrapcp.RoutingModel(manager)

    def distance_callback(from_index, to_index):
        from_node = manager.IndexToNode(from_index)
        to_node = manager.IndexToNode(to_index)
        return distance_matrix[from_node][to_node]

    transit_callback_index = routing.RegisterTransitCallback(distance_callback)
    routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)

    search_parameters = pywrapcp.DefaultRoutingSearchParameters()
    search_parameters.first_solution_strategy = (
        routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC)

    solution = routing.SolveWithParameters(search_parameters)

    if solution:
        result = []
        for vehicle_id in range(num_vehicles):
            index = routing.Start(vehicle_id)
            route = []
            while not routing.IsEnd(index):
                route.append(manager.IndexToNode(index))
                index = solution.Value(routing.NextVar(index))
            result.append(route)
        return result, "Optimal routes found"
    else:
        return None, "No solution found"

# Knapsack Problem Solver
def solve_knapsack_problem(values, weights, capacity):
    solver = pywrapknapsack_solver.KnapsackSolver(
        pywrapknapsack_solver.KnapsackSolver.KNAPSACK_DYNAMIC_PROGRAMMING_SOLVER, 'KnapsackExample')
    
    solver.Init(values, [weights], [capacity])
    computed_value = solver.Solve()

    packed_items = []
    packed_weights = []
    total_weight = 0
    for i in range(len(values)):
        if solver.BestSolutionContains(i):
            packed_items.append(i)
            packed_weights.append(weights[i])
            total_weight += weights[i]

    return {
        'Total value': computed_value,
        'Packed items': packed_items,
        'Packed weights': packed_weights,
        'Total weight': total_weight
    }, "Optimal solution found"

# Job Shop Scheduling Solver
def solve_job_shop_scheduling(jobs_data):
    solver = pywrapcp.Solver('job_shop_scheduling')
    machines_count = max(machine for job in jobs_data for machine, _ in job) + 1
    all_machines = range(machines_count)

    horizon = sum(task[1] for job in jobs_data for task in job)

    task_type = collections.namedtuple('task_type', 'start end interval')
    all_tasks = {}
    machine_to_intervals = collections.defaultdict(list)

    for job_id, job in enumerate(jobs_data):
        for task_id, task in enumerate(job):
            machine = task[0]
            duration = task[1]
            suffix = '_%i_%i' % (job_id, task_id)
            start_var = solver.IntVar(0, horizon, 'start' + suffix)
            end_var = solver.IntVar(0, horizon, 'end' + suffix)
            interval_var = solver.FixedDurationIntervalVar(start_var, duration, 'interval' + suffix)
            all_tasks[job_id, task_id] = task_type(start=start_var, end=end_var, interval=interval_var)
            machine_to_intervals[machine].append(interval_var)

    for machine in all_machines:
        solver.Add(solver.DisjunctiveConstraint(machine_to_intervals[machine], 'machine %i' % machine))

    for job_id, job in enumerate(jobs_data):
        for task_id in range(len(job) - 1):
            solver.Add(all_tasks[job_id, task_id + 1].start >= all_tasks[job_id, task_id].end)

    obj_var = solver.Max([all_tasks[job_id, len(job) - 1].end for job_id, job in enumerate(jobs_data)])
    objective = solver.Minimize(obj_var, 1)
    decision_builder = solver.Phase([all_tasks[job_id, task_id].start for job_id, job in enumerate(jobs_data) for task_id in range(len(job))],
                                    solver.CHOOSE_MIN_SIZE_LOWEST_MIN, solver.ASSIGN_MIN_VALUE)
    solver.NewSearch(decision_builder, [objective])
    sol_count = 0
    while solver.NextSolution():
        sol_count += 1
        print('Solution', sol_count)
        print('Optimal Schedule Length:', solver.ObjectiveValue())
        for job_id, job in enumerate(jobs_data):
            for task_id, task in enumerate(job):
                print('Job %i Task %i: Machine %i [%i, %i]' % (
                    job_id, task_id, task[0],
                    all_tasks[job_id, task_id].start.Value(),
                    all_tasks[job_id, task_id].end.Value()))
        print()
    solver.EndSearch()

    return sol_count, "Solution(s) found" if sol_count else "No solution found"

# Network Flow Optimization Solver
def solve_network_flow_optimization(supply, demand, costs):
    solver = pywraplp.Solver.CreateSolver('GLOP')
    if not solver:
        return None, "Solver creation failed"

    num_sources = len(supply)
    num_sinks = len(demand)

    x = {}
    for i in range(num_sources):
        for j in range(num_sinks):
            x[i, j] = solver.NumVar(0, solver.infinity(), '')

    for i in range(num_sources):
        solver.Add(solver.Sum([x[i, j] for j in range(num_sinks)]) <= supply[i])

    for j in range(num_sinks):
        solver.Add(solver.Sum([x[i, j] for i in range(num_sources)]) == demand[j])

    solver.Minimize(solver.Sum([x[i, j] * costs[i][j] for i in range(num_sources) for j in range(num_sinks)]))

    status = solver.Solve()

    if status == pywraplp.Solver.OPTIMAL:
        result = [[x[i, j].solution_value() for j in range(num_sinks)] for i in range(num_sources)]
        return result, "Optimal flow found"
    else:
        return None, "No optimal flow found"
