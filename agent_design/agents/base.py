"""Abstract base class for all agent implementations."""

from abc import ABC, abstractmethod
from pathlib import Path

from agent_design.agents.types import AgentExecutionResult, AgentType


class BaseAgent(ABC):
    """Abstract base class for all LLM agent implementations.

    This interface enables dependency injection and allows multiple LLM backends
    to be used interchangeably throughout the workflow system.
    """

    @property
    @abstractmethod
    def agent_type(self) -> AgentType:
        """Return the agent type identifier.

        Returns:
            AgentType enum value identifying this agent
        """
        pass

    @property
    def agent_name(self) -> str:
        """Return the agent type name as a string.

        Returns:
            Agent type name (e.g., "architect", "developer")
        """
        return self.agent_type.value

    @property
    @abstractmethod
    def system_prompt(self) -> str:
        """Return the base system prompt for this agent.

        Returns:
            System prompt string defining agent's role and expertise
        """
        pass

    @abstractmethod
    async def execute(
        self,
        user_prompt: str,
        working_dir: Path | None = None,
        timeout: int = 3600,
        additional_dirs: list[Path] | None = None,
    ) -> AgentExecutionResult:
        """Execute agent with the given prompt.

        Args:
            user_prompt: The user prompt to send to the LLM
            working_dir: Working directory for execution (.agent-design/)
            timeout: Timeout in seconds for execution (default: 3600)
            additional_dirs: Additional directories to grant access to (target repo)

        Returns:
            AgentExecutionResult with success/output/error and metadata
        """
        pass
