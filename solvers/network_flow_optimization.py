from ortools.linear_solver import pywraplp

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