from ortools.constraint_solver import pywrapcp

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