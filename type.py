from enum import Enum
from pydantic import BaseModel, Field
from typing import List, Optional


class Status(Enum):
    NOT_ACTIVE = "NOT_ACTIVE"
    PENDING = "PENDING"
    DONE = "DONE"
    FAILED = "FAILED"
    NEEDS_VERIFICATION = "NEEDS_VERIFICATION"


class Task(BaseModel):
    """Correctly resolved sub-task from the given objective.

    cmd (str): The detailed and specific natural language instruction for web browsing
    url (str): The best URL to start the session based on user instruction"""

    id: int
    name: str
    description: str
    cmd: str
    url: str
    status: Status = Status.NOT_ACTIVE


class TaskList(BaseModel):
    """Correctly resolved set of tasks from the given objective"""

    tasks: List[Task]
