from dataclasses import asdict

from .checks import destination_problem, encoded, identifier, result, safe_path


def input_problem(v):
    problem = destination_problem(v.destination)
    if problem:
        return problem
    if len(v.jobs) > 100:
        return "at most 100 jobs are supported"
    ids = {r.job_id for r in v.jobs}
    if len(ids) != len(v.jobs):
        return "job identifiers must be unique"
    for r in v.jobs:
        if not identifier(r.job_id) or not 0 <= r.duration <= 100000 or len(r.needs) != len(set(r.needs)):
            return "invalid job identifier, duration, or duplicate prerequisite"
        if any(n not in ids or n == r.job_id for n in r.needs):
            return "prerequisites must name other existing jobs"
    done = set()
    while len(done) < len(ids):
        next_ids = {r.job_id for r in v.jobs if r.job_id not in done and set(r.needs) <= done}
        if not next_ids:
            return "dependency graph contains a cycle"
        done.update(next_ids)
    return None


def verify_input(value):
    problem = input_problem(value)
    return result(not problem, problem or "input is valid")


def expected(v):
    jobs = {r.job_id: r for r in v.jobs}
    cache = {}

    def finish(key):
        if key not in cache:
            cache[key] = jobs[key].duration + max((finish(n) for n in jobs[key].needs), default=0)
        return cache[key]

    rows = [{"job_id": key, "start": finish(key) - jobs[key].duration, "finish": finish(key)} for key in sorted(jobs)]
    return rows, max((r["finish"] for r in rows), default=0)


def verify_output(input_value, output_value, workspace):
    problem = input_problem(input_value)
    if problem:
        return result(False, problem)
    rows, total = expected(input_value)
    actual = [asdict(r) for r in output_value.records]
    if actual != rows or output_value.total != total:
        return result(False, "returned rows or total do not match the task rules")
    if output_value.path != input_value.destination:
        return result(False, "returned path does not match destination")
    path = safe_path(workspace, input_value.destination)
    if path is None or not path.is_file():
        return result(False, "artifact is missing, is a symlink, or escapes the workspace")
    try:
        content = path.read_bytes().decode("utf-8")
    except (OSError, UnicodeError):
        return result(False, "artifact cannot be read as UTF-8")
    if content != encoded(rows, total):
        return result(False, "artifact is not the exact canonical JSON result")
    return result(True, "verified rows, total, destination, and artifact bytes", rows=len(rows), total=total)


def verify_task(arguments, output, reference, workspace):
    return verify_output(arguments, output, workspace)
