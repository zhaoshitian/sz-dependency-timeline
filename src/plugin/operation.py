from slimconfig import build_output

from contract import TaskOutput
from verifier.checks import encoded, safe_path
from verifier.operation import verify_input


def solve(v):
    pending = {r.job_id: r for r in v.jobs}
    finished = {}
    rows = []
    while pending:
        ready = sorted(k for k, r in pending.items() if all(n in finished for n in r.needs))
        for key in ready:
            job = pending.pop(key)
            start = max((finished[n] for n in job.needs), default=0)
            finished[key] = start + job.duration
            rows.append({"job_id": key, "start": start, "finish": finished[key]})
    return sorted(rows, key=lambda r: r["job_id"]), max(finished.values(), default=0)


def operate(value, workspace):
    verdict = verify_input(value)
    if not verdict["valid"]:
        raise ValueError(verdict["message"])
    path = safe_path(workspace, value.destination)
    if path is None:
        raise ValueError("destination crosses a symlink or leaves the workspace")
    rows, total = solve(value)
    output = build_output({"path": value.destination, "records": rows, "total": total}, TaskOutput)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(encoded(rows, total))
    return output
