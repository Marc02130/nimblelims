"""Shared dev-seed password helper.

No published password, digest, or other secret belongs in this module.
Fresh migrations store ``SEED_LOCKED`` instead. ``backend/seed_dev_passwords.py``
replaces that marker from an env var or a generated value printed once.

``must_change_password`` after ``--apply`` is false. That matches
``seed_config_agent_slice.py``: the operator either chose the env value or
just received the only printed copy. Forcing another change would throw
that copy away before it can be stored.
"""
from __future__ import annotations

import os
import secrets
import string

# Neither bcrypt (``$2…``) nor 64-hex SHA256, so ``verify_password`` returns
# False and the account cannot be used.
SEED_LOCKED = "!seed-locked"

# (username, env var). One variable per persona, not one shared password.
PERSONAS: tuple[tuple[str, str], ...] = (
    ("admin", "DEV_SEED_ADMIN_PASSWORD"),
    ("lab-manager", "DEV_SEED_LAB_MANAGER_PASSWORD"),
    ("lab-tech", "DEV_SEED_LAB_TECH_PASSWORD"),
    ("client", "DEV_SEED_CLIENT_PASSWORD"),
    ("alice-tech", "DEV_SEED_ALICE_TECH_PASSWORD"),
    ("bob-tech", "DEV_SEED_BOB_TECH_PASSWORD"),
    ("carol-manager", "DEV_SEED_CAROL_MANAGER_PASSWORD"),
    ("david-cro", "DEV_SEED_DAVID_CRO_PASSWORD"),
)

_PERSONA_ENV = dict(PERSONAS)


def generate_dev_password() -> str:
    """Strong random password. Meets the app complexity rules. Not logged."""
    required = [
        secrets.choice(string.ascii_uppercase),
        secrets.choice(string.ascii_lowercase),
        secrets.choice(string.digits),
        secrets.choice("!@#$%^&*-_"),
    ]
    pool = string.ascii_letters + string.digits + "!@#$%^&*-_"
    chars = required + [secrets.choice(pool) for _ in range(20)]
    for index in range(len(chars) - 1, 0, -1):
        swap = secrets.randbelow(index + 1)
        chars[index], chars[swap] = chars[swap], chars[index]
    return "".join(chars)


def seed_password_env(username: str) -> str:
    """Env var for a seed persona. Unknown usernames follow the same pattern."""
    known = _PERSONA_ENV.get(username)
    if known:
        return known
    return "DEV_SEED_" + username.upper().replace("-", "_") + "_PASSWORD"


def missing_seed_password_envs(usernames: list[str]) -> list[str]:
    missing = []
    for username in usernames:
        name = seed_password_env(username)
        if not os.environ.get(name, "").strip():
            missing.append(name)
    return missing


def require_seed_passwords(usernames: list[str]) -> dict[str, str]:
    """Return username → password. Exit if any required env var is unset.

    The message lists variable names only. There is no default password.
    """
    missing = missing_seed_password_envs(usernames)
    if missing:
        raise SystemExit(
            "Missing seed password env vars: "
            + ", ".join(missing)
            + ". Set them, or run python backend/seed_dev_passwords.py --apply "
            "and export the printed values. Names are in .env.example. "
            "This runner does not fall back to a default."
        )
    return {
        username: os.environ[seed_password_env(username)]
        for username in usernames
    }


def seed_password(username: str) -> str:
    """One persona password from the environment, or exit naming the variable."""
    return require_seed_passwords([username])[username]
