"""Encrypt the configuring-agent provider key. The plaintext is never returned."""

from __future__ import annotations

import base64
import hashlib
import os

from cryptography.fernet import Fernet, InvalidToken

from app.core.config import SECRET_KEY

ENV_KEY_NAMES = {
    "openai": "OPENAI_API_KEY",
    "xai": "XAI_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
}


class MissingProviderKey(Exception):
    def __init__(self, provider: str, env_name: str):
        self.provider = provider
        self.env_name = env_name
        super().__init__(
            f"No key for {provider}. Set it here or set {env_name}. "
            "Configuring agent will not call another provider."
        )


def _fernet() -> Fernet:
    digest = hashlib.sha256(SECRET_KEY.encode()).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def encrypt_secret(plain: str) -> str:
    return _fernet().encrypt(plain.encode()).decode()


def decrypt_secret(token: str) -> str:
    try:
        return _fernet().decrypt(token.encode()).decode()
    except InvalidToken as exc:
        raise ValueError("could not decrypt configuring-agent key") from exc


def clear_stored_key(settings) -> None:
    """Clearing the key also clears the model. The provider stays."""
    settings.key_ciphertext = None
    settings.agent_model = None


def resolve_provider_key(provider: str, stored_ciphertext: str | None) -> str:
    """Stored key for this provider, else that provider's env var. Never another vendor."""
    if provider not in ENV_KEY_NAMES:
        raise MissingProviderKey(provider or "unset", "OPENAI_API_KEY")
    env_name = ENV_KEY_NAMES[provider]
    if stored_ciphertext:
        return decrypt_secret(stored_ciphertext)
    value = (os.getenv(env_name) or "").strip()
    if not value:
        raise MissingProviderKey(provider, env_name)
    return value
