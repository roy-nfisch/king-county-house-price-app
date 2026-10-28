"""Configure standard Python logging explicitly at application startup."""

import logging

from king_county.settings import AppSettings


def configure_logging(settings: AppSettings) -> None:
    """Set up console logging without replacing existing application handlers.

    Args:
        settings: Validated settings containing the desired logging level.

    Returns:
        None. Configures the root logger when it has no handlers yet.
    """
    logging.basicConfig(
        level=settings.log_level,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
