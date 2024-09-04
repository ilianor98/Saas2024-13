from ortools.constraint_solver import pywrapcp
import collections

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