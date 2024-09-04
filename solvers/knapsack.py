from ortools.algorithms.python import knapsack_solver

def solve_knapsack_problem(values, weights, capacity):
    solver = knapsack_solver.KnapsackSolver(knapsack_solver.SolverType.KNAPSACK_MULTIDIMENSION_BRANCH_AND_BOUND_SOLVER,"KnapsackExample",)
    
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