"""Agent type definitions and execution result schema."""

from dataclasses import dataclass
from enum import Enum
from uuid import UUID


class AgentType(Enum):
    """Agent role identifiers."""

    ENG_MANAGER = "eng_manager"
    ARCHITECT = "architect"
    DEVELOPER = "developer"
    QA_ENGINEER = "qa_engineer"
    CODE_QUALITY_ENGINEER = "code_quality_engineer"


@dataclass
class AgentExecutionResult:
    """Result from executing an agent with a prompt.

    Attributes:
        agent_type: The type of agent that executed
        success: Whether execution completed successfully
        output: Stdout/response from the agent
        error: Error message if execution failed
        execution_time: Time taken in seconds
        session_id: Claude CLI session ID used
        amendment: System prompt amendment if any
    """

    agent_type: AgentType
    success: bool
    output: str
    error: str | None
    execution_time: float
    session_id: UUID
    amendment: str | None = None
