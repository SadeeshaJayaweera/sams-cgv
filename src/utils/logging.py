"""Project logging.

One place decides what a log line looks like, so nine modules produce output a
marker can read as a single trace of one run::

    [14:22:07] INFO    pipeline | stage 'binarize' starting
    [14:22:07] DEBUG   binarize | otsu threshold = 137
    [14:22:08] WARNING decision | 6 rows detected but 7 students in info.xml

Modules call :func:`get_logger` and nothing else. The CLI calls
:func:`set_debug` once, after parsing arguments.
"""

from __future__ import annotations

import logging as _stdlib_logging
import sys

from src import config

ROOT_LOGGER_NAME = "sams"
"""Every project logger is a child of this one, so one handler serves all."""

LINE_FORMAT = "[%(asctime)s] %(levelname)-7s %(short_name)-9s | %(message)s"
TIME_FORMAT = "%H:%M:%S"


class _ShortNameFilter(_stdlib_logging.Filter):
    """Add ``short_name``: the logger name without the ``sams.`` prefix."""

    def filter(self, record: _stdlib_logging.LogRecord) -> bool:
        prefix = f"{ROOT_LOGGER_NAME}."
        name = record.name
        record.short_name = name[len(prefix):] if name.startswith(prefix) else name
        return True


def _configure_root() -> _stdlib_logging.Logger:
    """Attach the single stream handler, once."""
    root = _stdlib_logging.getLogger(ROOT_LOGGER_NAME)
    if not root.handlers:
        handler = _stdlib_logging.StreamHandler(stream=sys.stderr)
        handler.setFormatter(
            _stdlib_logging.Formatter(fmt=LINE_FORMAT, datefmt=TIME_FORMAT)
        )
        handler.addFilter(_ShortNameFilter())
        root.addHandler(handler)
        root.propagate = False
    root.setLevel(_stdlib_logging.DEBUG if config.DEBUG else _stdlib_logging.INFO)
    return root


def get_logger(name: str) -> _stdlib_logging.Logger:
    """Return the logger for one module.

    Args:
        name: Short module name, e.g. ``"pipeline"`` or ``"binarize"``. It is
            what appears in the module column of every line.

    Returns:
        A configured logger. Calling this twice with the same name returns the
        same object, so it is cheap to call at module import.
    """
    _configure_root()
    return _stdlib_logging.getLogger(f"{ROOT_LOGGER_NAME}.{name}")


def set_debug(enabled: bool) -> None:
    """Turn DEBUG level output on or off for the whole project.

    Args:
        enabled: ``True`` after ``sams.py --debug``.
    """
    config.DEBUG = enabled
    _configure_root()
