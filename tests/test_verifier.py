import copy

import pytest
from slimconfig import build_output, plain_output

import verifier
from contract import TaskInput, TaskOutput
from plugin.operation import operate

SAMPLE = {
    "jobs": [
        {"job_id": "D", "duration": 1, "needs": ["B", "C"]},
        {"job_id": "A", "duration": 3, "needs": []},
        {"job_id": "C", "duration": 2, "needs": ["A"]},
        {"job_id": "B", "duration": 4, "needs": ["A"]},
    ]
}
EXPECTED_ROWS = [
    {"job_id": "A", "start": 0, "finish": 3},
    {"job_id": "B", "start": 3, "finish": 7},
    {"job_id": "C", "start": 3, "finish": 5},
    {"job_id": "D", "start": 7, "finish": 8},
]
EXPECTED_TOTAL = 8
EMPTY = {"jobs": []}
INVALID = {"jobs": [{"job_id": "A", "duration": 1, "needs": ["missing"]}]}
TOOL = "schedule_jobs"
TASK = "schedule-jobs"


def given(data):
    return build_output({"destination": "results/out.json", **data}, TaskInput)


def valid_input(data):
    return verifier.verify_input(TOOL, given(data))["valid"]


def execute(data, workspace):
    value = given(data)
    assert verifier.verify_input(TOOL, value)["valid"]
    output = build_output(plain_output(operate(value, workspace)), TaskOutput)
    assert verifier.verify_output(TOOL, value, output, str(workspace))["valid"]
    verdict = verifier.verify_task(TASK, value, output, None, str(workspace))
    assert verdict["valid"] and verdict["score"] == 1.0
    assert verdict == verifier.verify_task(TASK, value, output, None, str(workspace))
    return output


def test_known_answer(tmp_path):
    out = execute(SAMPLE, tmp_path)
    assert plain_output(out)["records"] == EXPECTED_ROWS
    assert out.total == EXPECTED_TOTAL


def test_empty_boundary(tmp_path):
    out = execute(EMPTY, tmp_path)
    assert out.records == [] and out.total == 0


def test_wrong_total_rejected(tmp_path):
    out = execute(SAMPLE, tmp_path)
    out.total += 1
    assert not verifier.verify_task(TASK, given(SAMPLE), out, None, str(tmp_path))["valid"]


def test_omitted_row_rejected(tmp_path):
    out = execute(SAMPLE, tmp_path)
    out.records.pop()
    assert not verifier.verify_task(TASK, given(SAMPLE), out, None, str(tmp_path))["valid"]


def test_duplicate_row_rejected(tmp_path):
    out = execute(SAMPLE, tmp_path)
    out.records.append(out.records[0])
    assert not verifier.verify_task(TASK, given(SAMPLE), out, None, str(tmp_path))["valid"]


def test_order_is_canonical(tmp_path):
    out = execute(SAMPLE, tmp_path)
    out.records.reverse()
    assert not verifier.verify_task(TASK, given(SAMPLE), out, None, str(tmp_path))["valid"]


def test_missing_file_rejected(tmp_path):
    out = execute(SAMPLE, tmp_path)
    (tmp_path / out.path).unlink()
    assert not verifier.verify_task(TASK, given(SAMPLE), out, None, str(tmp_path))["valid"]


@pytest.mark.parametrize(
    "text", ["{", "null", "{}", '{"records":[],"total":NaN}', '{"records":[],"total":0,"total":1}']
)
def test_malformed_or_incorrect_file_rejected(tmp_path, text):
    out = execute(SAMPLE, tmp_path)
    (tmp_path / out.path).write_text(text)
    assert not verifier.verify_task(TASK, given(SAMPLE), out, None, str(tmp_path))["valid"]


def test_invalid_utf8_rejected(tmp_path):
    out = execute(SAMPLE, tmp_path)
    (tmp_path / out.path).write_bytes(b"\xff")
    assert not verifier.verify_task(TASK, given(SAMPLE), out, None, str(tmp_path))["valid"]


def test_claimed_path_mismatch_rejected(tmp_path):
    out = execute(SAMPLE, tmp_path)
    out.path = "different.json"
    assert not verifier.verify_task(TASK, given(SAMPLE), out, None, str(tmp_path))["valid"]


@pytest.mark.parametrize(
    "destination", ["../escape.json", "/absolute.json", "result.txt", "", "a/../b.json", "./x.json", "a\\b.json"]
)
def test_destination_rejected(destination):
    assert not valid_input({**SAMPLE, "destination": destination})


def test_invalid_input_and_tool_failure(tmp_path):
    data = {**SAMPLE, **INVALID}
    assert not valid_input(data)
    with pytest.raises(ValueError):
        operate(given(data), tmp_path)


def test_schema_rejects_missing_or_malformed():
    with pytest.raises((ValueError, TypeError)):
        build_output({}, TaskInput)
    with pytest.raises((ValueError, TypeError)):
        build_output({"path": "out.json", "records": "wrong", "total": "wrong"}, TaskOutput)
    with pytest.raises((ValueError, TypeError)):
        build_output({"path": "out.json", "records": [], "total": 0, "extra": 1}, TaskOutput)


def test_existing_file_is_never_overwritten(tmp_path):
    out = execute(SAMPLE, tmp_path)
    content = (tmp_path / out.path).read_bytes()
    with pytest.raises(FileExistsError):
        operate(given(SAMPLE), tmp_path)
    assert (tmp_path / out.path).read_bytes() == content


def test_symlink_file_rejected(tmp_path):
    out = execute(SAMPLE, tmp_path)
    path = tmp_path / out.path
    target = tmp_path / "target.json"
    path.rename(target)
    path.symlink_to(target)
    assert not verifier.verify_task(TASK, given(SAMPLE), out, None, str(tmp_path))["valid"]


def test_symlink_directory_rejected(tmp_path):
    (tmp_path / "actual").mkdir()
    (tmp_path / "results").symlink_to(tmp_path / "actual", target_is_directory=True)
    with pytest.raises(ValueError):
        operate(given(SAMPLE), tmp_path)


def test_input_permutation_does_not_change_result(tmp_path):
    data = copy.deepcopy(SAMPLE)
    for value in data.values():
        if isinstance(value, list):
            value.reverse()
    assert plain_output(execute(data, tmp_path))["records"] == EXPECTED_ROWS


def test_edited_row_even_with_matching_file_is_rejected(tmp_path):
    import json

    out = execute(SAMPLE, tmp_path)
    data = plain_output(out)
    row = data["records"][0]
    key = next(k for k, v in row.items() if type(v) is int)
    row[key] += 1
    forged = build_output(data, TaskOutput)
    artifact = {"records": data["records"], "total": data["total"]}
    (tmp_path / out.path).write_text(json.dumps(artifact, sort_keys=True, separators=(",", ":")) + "\n")
    assert not verifier.verify_task(TASK, given(SAMPLE), forged, None, str(tmp_path))["valid"]


def test_cycle_rejected():
    assert not valid_input(
        {"jobs": [{"job_id": "A", "duration": 1, "needs": ["B"]}, {"job_id": "B", "duration": 1, "needs": ["A"]}]}
    )


def test_zero_duration_chain(tmp_path):
    out = execute(
        {"jobs": [{"job_id": "A", "duration": 0, "needs": []}, {"job_id": "B", "duration": 0, "needs": ["A"]}]},
        tmp_path,
    )
    assert out.total == 0 and len(out.records) == 2


def test_disconnected_jobs(tmp_path):
    out = execute(
        {"jobs": [{"job_id": "A", "duration": 7, "needs": []}, {"job_id": "B", "duration": 3, "needs": []}]}, tmp_path
    )
    assert out.total == 7 and all(r.start == 0 for r in out.records)


def test_duplicate_dependency_rejected():
    data = {"jobs": [{"job_id": "A", "duration": 1, "needs": []}, {"job_id": "B", "duration": 1, "needs": ["A", "A"]}]}
    assert not valid_input(data)


def test_crlf_is_not_canonical_bytes(tmp_path):
    out = execute(SAMPLE, tmp_path)
    artifact = tmp_path / out.path
    artifact.write_bytes(artifact.read_bytes().replace(b"\n", b"\r\n"))
    assert not verifier.verify_task(TASK, given(SAMPLE), out, None, str(tmp_path))["valid"]
