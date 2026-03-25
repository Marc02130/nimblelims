"""
Anthropic client singleton.
Import `anthropic_client` and call its API directly.
Raises RuntimeError at startup if ANTHROPIC_API_KEY is not set.
"""
import anthropic
from app.core.config import ANTHROPIC_API_KEY


def _build_client() -> anthropic.Anthropic:
    if not ANTHROPIC_API_KEY:
        raise RuntimeError(
            "ANTHROPIC_API_KEY is not set. "
            "Add it to .env (see .env.example)."
        )
    return anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)


anthropic_client: anthropic.Anthropic = _build_client()
