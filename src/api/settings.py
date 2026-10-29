"""API configuration; artifact identity remains pinned in trusted code."""

import os
import re
from pathlib import Path
from typing import Literal, Self

from pydantic import ConfigDict, SecretStr, model_validator

from king_county.artifacts import DEFAULT_MODEL_PATH
from king_county.settings import AppSettings


class ApiSettings(AppSettings):
    """Validate model location, deployment mode, logging and optional token."""

    model_path: Path = DEFAULT_MODEL_PATH
    database_path: Path = Path("houses.sqlite3")
    mode: Literal["local", "cloud"] = "local"
    api_token: SecretStr | None = None
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)

    @model_validator(mode="after")
    def validate_auth(self) -> Self:
        """Reject missing cloud credentials and malformed bearer tokens."""
        token = (
            self.api_token.get_secret_value() if self.api_token is not None else None
        )
        if self.mode == "cloud" and not token:
            raise ValueError("API_TOKEN is required in cloud mode")
        if self.mode == "cloud" and token is not None and len(token) < 32:
            raise ValueError("API_TOKEN must be at least 32 characters in cloud mode")
        if token is not None and not re.fullmatch(r"[A-Za-z0-9._~-]+", token):
            raise ValueError("API_TOKEN must be a nonempty URL-safe token")
        return self

    @classmethod
    def from_environment(cls) -> Self:
        """Read API settings from the environment or raise a validation error."""
        return cls(
            log_level=os.getenv("LOG_LEVEL", "INFO"),
            model_path=Path(os.getenv("MODEL_PATH", str(DEFAULT_MODEL_PATH))),
            database_path=Path(os.getenv("DATABASE_PATH", "houses.sqlite3")),
            mode=os.getenv("API_MODE", "local"),
            api_token=os.getenv("API_TOKEN"),
        )
