from ortools.linear_solver import pywraplp

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


def solve_integer_program(objective_coeffs, constraint_coeffs, bounds):
    solver = pywraplp.Solver.CreateSolver('CBC')
    if not solver:
        return None, "Solver creation failed"

    num_vars = len(objective_coeffs)
    x = [solver.IntVar(0, solver.infinity(), f'x{i}') for i in range(num_vars)]
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
