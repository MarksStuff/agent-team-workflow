"""Claude CLI implementation of BaseAgent."""

import asyncio
import os
import time
import uuid
from pathlib import Path

from agent_design.agents.base import BaseAgent
from agent_design.agents.configs import AgentConfig
from agent_design.agents.types import AgentExecutionResult, AgentType


class ClaudeAgent(BaseAgent):
    """Claude CLI implementation of BaseAgent.

    Executes prompts via Claude CLI subprocess, preserving filesystem access
    and Claude Code's advanced features (file operations, tool use, etc.).
    """

    def __init__(self, config: AgentConfig):
        """Initialize Claude agent with configuration.

        Args:
            config: Agent configuration (system prompt, type)
        """
        self.config = config

    @property
    def agent_type(self) -> AgentType:
        """Return agent type from configuration."""
        return self.config.agent_type

    @property
    def system_prompt(self) -> str:
        """Return base system prompt from configuration."""
        return self.config.system_prompt

    @staticmethod
    def _get_api_key() -> str:
        """Get Anthropic API key from environment or ~/.anthropic_api_key file.

        Returns:
            API key string

        Raises:
            RuntimeError: If API key cannot be found
        """
        # Check environment variable first
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if api_key:
            return api_key

        # Check ~/.anthropic_api_key file
        api_key_file = Path.home() / ".anthropic_api_key"
        if api_key_file.exists():
            return api_key_file.read_text().strip()

        raise RuntimeError("ANTHROPIC_API_KEY not found. Set the environment variable or create ~/.anthropic_api_key")

    @staticmethod
    def build_claude_command(
        system_prompt: str,
        additional_dirs: list[Path] | None = None,
    ) -> list[str]:
        """Build Claude CLI command with all parameters.

        Args:
            system_prompt: Complete system prompt to append
            additional_dirs: Optional list of additional directories to grant access to

        Returns:
            List of command arguments ready for subprocess execution
        """
        cmd = [
            "claude",
            "--print",
            "--dangerously-skip-permissions",
            "--strict-mcp-config",
            "--mcp-config",
            '{"mcpServers":{}}',
        ]

        # Add additional directories if provided
        if additional_dirs:
            for dir_path in additional_dirs:
                cmd.extend(["--add-dir", str(dir_path)])

        # Add system prompt
        cmd.extend(["--append-system-prompt", system_prompt])

        return cmd

    async def execute(
        self,
        user_prompt: str,
        working_dir: Path | None = None,
        timeout: int = 3600,
        additional_dirs: list[Path] | None = None,
    ) -> AgentExecutionResult:
        """Execute this agent with the given prompt via Claude CLI subprocess.

        Args:
            user_prompt: The user prompt to send to Claude
            working_dir: Working directory for execution (.agent-design/)
            timeout: Timeout in seconds for execution
            additional_dirs: Additional directories to grant Claude access to

        Returns:
            AgentExecutionResult with success/output/error and metadata
        """
        start_time = time.time()
        session_id = uuid.uuid4()

        # Get API key
        try:
            api_key = self._get_api_key()
        except RuntimeError as e:
            return AgentExecutionResult(
                agent_type=self.agent_type,
                success=False,
                output="",
                error=str(e),
                execution_time=0.0,
                session_id=session_id,
            )

        # Build Claude CLI command
        cmd = self.build_claude_command(
            system_prompt=self.system_prompt,
            additional_dirs=additional_dirs,
        )

        # Set working directory if provided
        cwd = str(working_dir) if working_dir else None

        # Prepare environment with API key
        env = os.environ.copy()
        env["ANTHROPIC_API_KEY"] = api_key

        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=cwd,
                env=env,
            )

            # Send user prompt via stdin and wait for completion
            stdout, stderr = await asyncio.wait_for(
                process.communicate(input=user_prompt.encode("utf-8")),
                timeout=timeout,
            )

            execution_time = time.time() - start_time

            # Decode outputs
            stdout_str = stdout.decode("utf-8")
            stderr_str = stderr.decode("utf-8")

            if process.returncode == 0:
                return AgentExecutionResult(
                    agent_type=self.agent_type,
                    success=True,
                    output=stdout_str,
                    error=None,
                    execution_time=execution_time,
                    session_id=session_id,
                )
            else:
                return AgentExecutionResult(
                    agent_type=self.agent_type,
                    success=False,
                    output=stdout_str,
                    error=stderr_str,
                    execution_time=execution_time,
                    session_id=session_id,
                )

        except TimeoutError:
            execution_time = time.time() - start_time
            error_msg = f"Agent execution timed out after {timeout} seconds"
            return AgentExecutionResult(
                agent_type=self.agent_type,
                success=False,
                output="",
                error=error_msg,
                execution_time=execution_time,
                session_id=session_id,
            )
        except Exception as e:
            execution_time = time.time() - start_time
            error_msg = f"Agent execution failed: {str(e)}"
            return AgentExecutionResult(
                agent_type=self.agent_type,
                success=False,
                output="",
                error=error_msg,
                execution_time=execution_time,
                session_id=session_id,
            )
