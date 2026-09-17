"""Tool abstraction used by the Audit Agent.

Tools are narrow, structured operations the orchestration nodes invoke
(``docs/agents/agent-tools.md``): they validate inputs, perform a single
authorized operation against the application layer and return a typed result.
Failures surface explicitly as ``AuditToolError`` carrying an operation code
and retryability hint. Tools never expose raw SQL to the agent.

Each tool opens its **own short-lived transaction** through an injected
``session_factory`` and commits before returning, so no long-lived transaction
is ever held across an LLM/agent call (``docs/backend/reliability.md``).
"""
from abc import ABC, abstractmethod
from contextlib import asynccontextmanager
from typing import Any


class AuditToolError(Exception):
    """Explicit tool failure with context to route and record it."""

    def __init__(
        self,
        message: str,
        *,
        code: str,
        agent: str = "audit_tools",
        retryable: bool = False,
    ):
        super().__init__(message)
        self.message = message
        self.code = code
        self.agent = agent
        self.retryable = retryable


class AuditTool(ABC):
    """Base class for audit workflow tools."""

    name: str = ""
    description: str = ""

    @abstractmethod
    async def run(self, **kwargs: Any) -> Any:
        """Execute the tool's single, authorized operation."""


@asynccontextmanager
async def transaction_session(session_factory):
    """Open a session, commit on success, rollback on failure, always close."""
    session = session_factory()
    try:
        yield session
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()