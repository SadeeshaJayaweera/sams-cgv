"""Stage timing.

The report has to say how long each processing step takes, and M9 draws a bar
chart of it. Rather than sprinkle ``time.perf_counter()`` through nine modules,
everything measured goes through here and lands in one dictionary.

Two ways in, both recording to the same place::

    @timed                      # on a Stage.run method or any function
    def run(self, ctx): ...

    with time_block("binarize"):    # around a block the Pipeline controls
        ...
"""

from __future__ import annotations

import functools
import time
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from typing import Any, TypeVar

from src.utils.logging import get_logger

log = get_logger("timing")

_TIMINGS: dict[str, float] = {}
"""Label to seconds, in the order the labels were first recorded."""

F = TypeVar("F", bound=Callable[..., Any])


def record(label: str, seconds: float) -> None:
    """Store one measurement and log it.

    Args:
        label: Stage name, e.g. ``"binarize"``.
        seconds: Wall clock duration.

    A label recorded twice accumulates, so a stage run over five sheets in one
    process reports its total rather than only the last sheet.
    """
    _TIMINGS[label] = _TIMINGS.get(label, 0.0) + seconds
    log.info("stage %r finished in %.2f s", label, seconds)


def timings() -> dict[str, float]:
    """A copy of every measurement taken so far, in insertion order."""
    return dict(_TIMINGS)


def total() -> float:
    """Seconds across every recorded label."""
    return sum(_TIMINGS.values())


def reset() -> None:
    """Forget every measurement. Used between sheets and in tests."""
    _TIMINGS.clear()


def _label_for(func: Callable[..., Any], args: tuple[Any, ...]) -> str:
    """Prefer the stage's own ``name`` over the function's qualified name."""
    if args:
        name = getattr(args[0], "name", None)
        if isinstance(name, str) and name:
            return name
    return func.__qualname__


def timed(func: F) -> F:
    """Measure how long the wrapped callable takes and record it.

    Applied to a :class:`~src.utils.stage.Stage` method the label is the
    stage's :attr:`~src.utils.stage.Stage.name`; anywhere else it is the
    function's qualified name.

    The measurement is taken in a ``finally`` block, so a stage that raises is
    still timed and still reported. It does not swallow the exception.
    """

    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        started = time.perf_counter()
        try:
            return func(*args, **kwargs)
        finally:
            record(_label_for(func, args), time.perf_counter() - started)

    return wrapper  # type: ignore[return-value]


@contextmanager
def time_block(label: str) -> Iterator[None]:
    """Time an arbitrary block of code under ``label``.

    This is how :class:`~src.pipeline.Pipeline` times stages it did not write,
    without needing every member to remember the decorator.
    """
    started = time.perf_counter()
    try:
        yield
    finally:
        record(label, time.perf_counter() - started)
