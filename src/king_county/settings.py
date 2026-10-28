"""Small, validated settings shared by the notebook and future application."""

import os
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict


class AppSettings(BaseModel):
    """Validate configuration; currently only the Python logging level.

    Attributes:
        log_level: One of DEBUG, INFO, WARNING, ERROR, or CRITICAL.
    """

    model_config = ConfigDict(extra="forbid")

    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"

    @classmethod
    def from_environment(cls) -> Self:
        """Read LOG_LEVEL from the environment and return validated settings.

        Returns:
            AppSettings with INFO when LOG_LEVEL is not set.

        Raises:
            ValidationError: If LOG_LEVEL is not a supported uppercase level.
        """
        return cls.model_validate({"log_level": os.getenv("LOG_LEVEL", "INFO")})
