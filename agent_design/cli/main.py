"""Main CLI entry point for agent-design."""

import click

from agent_design.cli.commands.checkpoints import checkpoints
from agent_design.cli.commands.close import close
from agent_design.cli.commands.continue_ import continue_cmd
from agent_design.cli.commands.diff import diff
from agent_design.cli.commands.feedback import feedback
from agent_design.cli.commands.impl import impl
from agent_design.cli.commands.init import init
from agent_design.cli.commands.resume import resume
from agent_design.cli.commands.rollback import rollback
from agent_design.cli.commands.status import status


@click.group()
@click.version_option(version="0.1.0")
def cli() -> None:
    """Multi-agent design workflow tool.

    Orchestrates 5 Claude Code agents to collaboratively design software features.
    """
    pass


# Register all commands
cli.add_command(init)
cli.add_command(status)
cli.add_command(continue_cmd, name="continue")
cli.add_command(continue_cmd, name="next")  # alias: next → continue
cli.add_command(impl)
cli.add_command(feedback)
cli.add_command(checkpoints)
cli.add_command(rollback)
cli.add_command(diff)
cli.add_command(resume)
cli.add_command(close)


if __name__ == "__main__":
    cli()
