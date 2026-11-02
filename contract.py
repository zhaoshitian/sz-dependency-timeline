"""Typed input and output declarations for Dependency Timeline."""

from dataclasses import dataclass
from enum import Enum
from typing import Annotated

from slimconfig import Output


class Tool(Enum):
    RUN = "schedule_jobs"


class Task(Enum):
    RUN = "schedule-jobs"


@dataclass
class Job(Output):
    job_id: Annotated[str, "Unique job identifier"]
    duration: Annotated[int, "Nonnegative integer duration"]
    needs: Annotated[list[str], "Unique identifiers of direct prerequisite jobs"]


@dataclass
class ResultRow(Output):
    job_id: Annotated[str, "Job identifier"]
    start: Annotated[int, "Earliest feasible start time"]
    finish: Annotated[int, "Start plus duration"]


@dataclass
class TaskInput(Output):
    jobs: Annotated[list[Job], "At most 100 jobs in a directed acyclic graph"]
    destination: Annotated[str, "New relative .json output path, never overwritten"]


@dataclass
class TaskOutput(Output):
    path: Annotated[str, "Artifact path matching destination"]
    records: Annotated[list[ResultRow], "Complete ordered task results"]
    total: Annotated[int, "Earliest completion time of the whole dependency graph"]


TOOLS = {Tool.RUN: (TaskInput, TaskOutput)}
TASKS = {Task.RUN: (TaskInput, TaskOutput)}
