"""No route may block the event loop with the sync DB session (UAT RT-7).

An ``async def`` endpoint (or async dependency) that uses the sync Session
runs its blocking DB calls on the event loop: one request waiting on a row
lock froze every request, /health included. Endpoints that touch the DB
must be plain ``def`` (FastAPI runs them in the threadpool).
"""
import asyncio

from fastapi.routing import APIRoute

from app.database import get_db
from app.main import app


def _uses_db(dependant) -> bool:
    return any(d.call is get_db or _uses_db(d) for d in dependant.dependencies)


def _async_db_users(dependant, path):
    found = []
    for d in dependant.dependencies:
        if asyncio.iscoroutinefunction(d.call) and _uses_db(d):
            found.append(f"{path}: dependency {getattr(d.call, '__name__', d.call)}")
        found += _async_db_users(d, path)
    return found


def test_no_async_endpoint_or_dependency_uses_the_sync_session():
    bad = []
    routes = [r for r in app.routes if isinstance(r, APIRoute)]
    assert len(routes) > 150
    for route in routes:
        label = f"{sorted(route.methods)} {route.path}"
        if asyncio.iscoroutinefunction(route.endpoint) and _uses_db(route.dependant):
            bad.append(f"{label}: endpoint {route.endpoint.__name__}")
        bad += _async_db_users(route.dependant, label)
    assert not bad, "async def + sync Session blocks the event loop:\n" + "\n".join(bad)
