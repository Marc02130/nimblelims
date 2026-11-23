"""Configuring-agent run context (calculations S8, CALC-REQ-34).

The configuring agent's executor sets this context around every step it
dispatches in process. It is a context variable inside the server process. A
client cannot set it: no header, query field, or body field is read into it.

The activation, confirm-token, and review-export services call
:func:`refuse_in_agent_context` first, so an agent step can neither obtain a
token nor activate, even if a route were added to its allow-list by mistake.
"""
from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from typing import Iterator

from fastapi import HTTPException, status

_AGENT_RUN: ContextVar[bool] = ContextVar("configuring_agent_run", default=False)


def in_agent_context() -> bool:
    return _AGENT_RUN.get()


@contextmanager
def agent_run_context() -> Iterator[None]:
    """Mark everything dispatched inside the block as a configuring-agent run."""
    token = _AGENT_RUN.set(True)
    try:
        yield
    finally:
        _AGENT_RUN.reset(token)


def refuse_in_agent_context(what: str) -> None:
    """HTTP 403 when called from a configuring-agent run (CALC-REQ-34)."""
    if in_agent_context():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "agent_context_refused",
                "message": f"{what} is an interactive Admin action. A configuring-agent run "
                "cannot do it, even for the person who started the run.",
            },
        )
