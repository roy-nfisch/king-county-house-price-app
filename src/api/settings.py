"""API configuration; artifact identity remains pinned in trusted code."""

import os
from pathlib import Path
from typing import Self

from king_county.artifacts import DEFAULT_MODEL_PATH
from king_county.settings import AppSettings


class ApiSettings(AppSettings):
    """Extend logging settings with the path of the approved local artifact."""

    model_path: Path = DEFAULT_MODEL_PATH

    @classmethod
    def from_environment(cls) -> Self:
        """Return settings from LOG_LEVEL and MODEL_PATH, or validation errors."""
        return cls(
            log_level=os.getenv("LOG_LEVEL", "INFO"),
            model_path=Path(os.getenv("MODEL_PATH", str(DEFAULT_MODEL_PATH))),
        )
