# Dependency Timeline

Compute the earliest unlimited-worker schedule for an acyclic job dependency graph.

## Tools

- `schedule_jobs` accepts `TaskInput` and returns `TaskOutput`.
- `schedule-jobs` is a `runner: tool` task using `schedule_jobs`. It requires no model or external service. A RUSH Lab agent can select the task from its structured interface.

### Exact success conditions

Dependencies must form a DAG. Jobs have unlimited parallel workers. start is the maximum finish of direct prerequisites, or zero; finish=start+duration. Rows are ordered by job_id. total is max finish, or zero.

The tool creates a new file at `destination`. The exact file format is UTF-8 JSON of `{"records": [...], "total": integer}`, sorted object keys, compact separators `(',', ':')`, ASCII escapes, and one final newline. Returned records, total, and destination must match the file and the independently computed answer. A matching claim without a matching file fails. Existing files are never overwritten. Paths must be canonical relative `.json` paths, at most 200 characters, with identifier-style directories and filename stems; symlinks are rejected. Identifiers match `[A-Za-z0-9][A-Za-z0-9_-]{0,31}`. Input sizes and numeric bounds are declared in `contract.py` and enforced in `verifier/operation.py`.

The tool performs an iterative topological schedule. The verifier uses memoized recursive longest-path evaluation.

### Example input

```json
{
  "destination": "results/out.json",
  "jobs": [
    {
      "job_id": "D",
      "duration": 1,
      "needs": [
        "B",
        "C"
      ]
    },
    {
      "job_id": "A",
      "duration": 3,
      "needs": []
    },
    {
      "job_id": "C",
      "duration": 2,
      "needs": [
        "A"
      ]
    },
    {
      "job_id": "B",
      "duration": 4,
      "needs": [
        "A"
      ]
    }
  ]
}
```

## Layout

- `contract.py`: typed schemas and tool/task tables.
- `nanoagent.yaml`: tool runner, no network hosts, workspace-only writes.
- `src/plugin/`: MCP runtime and deterministic implementation.
- `verifier/`: independent deterministic checks; no LLM, clock, network, randomness, or writes.
- `tests/test_verifier.py`: known answers, adversarial outputs, boundaries, malformed inputs, artifact changes, and safe paths.
- `ui/` and `product/`: result schema rendering and marketplace presentation.
- `uv.lock`: pinned dependency versions and Git revision of slimconfig.

## Develop and run

Requires Python 3.12 or later, Git, uv, and NanoAgent implementing `nanoagent.plugin/v0001` (tested with the RUSH Lab bundled CLI). First-time dependency installation requires the package index and GitHub; execution requires no network or environment secrets.

```sh
uv sync --frozen --extra dev
uv run --frozen pytest -q
uv run --frozen ruff check .
uv lock --check
rushlab nanoagent plugin inspect .
```

To run: save the example as `/absolute/path/input.json`, then create a YAML file outside the repository:

```yaml
_ > nanoagent.cli.plugin.PluginRunConfig:
plugin: /absolute/path/sz-dependency-timeline
task: schedule-jobs
arguments: /absolute/path/input.json
inputs: []
timeout: 60.0
```

Run `rushlab nanoagent plugin run config=/absolute/path/run.yaml home=/absolute/path/new-run-folder`.
The new run folder contains `workspace/results/out.json`, `result.json`, and `verdict.json`. A successful verifier returns `valid: true` and `score: 1.0`. Use a fresh run folder and destination for each run. Evidence and validation logs belong in the milestone report, outside this repository.

Limitations: No worker capacity, calendars, preemption, deadlines, or communication costs; at most 100 jobs.
