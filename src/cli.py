"""Shared helpers for the three command line programs.

``sams.py``, ``infovis.py`` and ``investigate.py`` are deliberately thin: parse
arguments, check them, hand over to a module. What they must all do identically
is fail — same wording, same exit codes, same hints — so a marker who mistypes
an index in one command already knows what the other two will say.

Exit codes follow section 10 of the spec:

* ``0`` — it worked, or there was simply nothing to do
* ``2`` — the user made a mistake: missing file, unknown index, empty database

A missing module is **not** an error while the project is being built. It
prints *module not ready yet* and exits 0, so the group can demonstrate the
commands from the first week.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, NoReturn

from src import config
from src.utils.logging import get_logger

log = get_logger("cli")

MAX_SUGGESTED_INDICES = 10
"""How many valid indices to list when the user gets one wrong."""


def fail(message: str, *hints: str) -> NoReturn:
    """Print a user mistake and stop. Never a traceback.

    Args:
        message: One line saying what is wrong.
        hints: Optional follow-up lines, indented under it.

    Raises:
        SystemExit: Always, with code 2.
    """
    print(f"error: {message}")
    for hint in hints:
        print(f"       {hint}")
    raise SystemExit(2)


def not_ready(module: str, owner: str) -> int:
    """Report that a module has not landed yet, and succeed anyway.

    Args:
        module: What is missing, e.g. ``"src/viz/charts.py"``.
        owner: Who is writing it, e.g. ``"M9"``.

    Returns:
        ``0`` — an unwritten module is a schedule fact, not a failure.
    """
    print(f"{owner} module not ready yet — this command will work once {module} lands")
    return 0


def optional_import(path: str, attribute: str) -> Callable[..., Any] | None:
    """Import one function, or return ``None`` if its module is unwritten.

    Args:
        path: Dotted module path, e.g. ``"src.viz.charts"``.
        attribute: Function name inside it.

    Returns:
        The function, or ``None`` when the module or the function is missing.
        Only :class:`ImportError` and :class:`AttributeError` are treated as
        *not written yet* — a module that exists and raises on import is a real
        bug and is allowed to propagate.
    """
    try:
        module = __import__(path, fromlist=[attribute])
    except ImportError:
        log.debug("%s is not importable yet", path)
        return None
    function = getattr(module, attribute, None)
    if function is None:
        log.debug("%s has no %s yet", path, attribute)
    return function


def known_indices() -> list[str]:
    """Every student index the project knows about.

    Prefers the database, because that is what the charts read from. Falls back
    to ``info.xml`` so the command can still be helpful before any sheet has
    been processed.
    """
    from_db = optional_import("src.io.db", "known_indices")
    if from_db is not None:
        indices = [str(index) for index in from_db()]
        if indices:
            return sorted(set(indices))

    parse_students = optional_import("src.io.xml_parser", "parse_students")
    if parse_students is None:
        from src.stubs import parse_students  # STUB — owned by M7
    students = parse_students(config.INFO_XML)
    return sorted({student.index for student in students})


def database_is_empty() -> bool:
    """``True`` when no attendance has been stored yet.

    Before M7 lands there is no database module, so the answer is taken from
    whether the file exists at all.
    """
    is_empty = optional_import("src.io.db", "is_empty")
    if is_empty is not None:
        return bool(is_empty())
    return not config.DB_PATH.is_file()


def require_database() -> None:
    """Stop with a hint if there is nothing to visualise yet."""
    if database_is_empty():
        fail(
            "the attendance database is empty",
            "run sams.py on a sheet first, for example:",
            "  python sams.py data/sheets/12.07.2019.png data/info.xml",
        )


def resolve_index(index: str) -> str:
    """Check a student index against the ones we know, or stop helpfully.

    Args:
        index: Whatever the user typed.

    Returns:
        The index, unchanged. It is returned rather than merely validated so
        call sites read as ``index = resolve_index(args.index)``.

    Raises:
        SystemExit: With code 2, when the index is not one we hold.
    """
    index = index.strip()
    if not index:
        fail("no student index given")

    valid = known_indices()
    if not valid:
        log.warning("no student list available, accepting index %r unchecked", index)
        return index
    if index in valid:
        return index

    shown = valid[:MAX_SUGGESTED_INDICES]
    hints = ["valid indices:"] + [f"  {value}" for value in shown]
    if len(valid) > len(shown):
        hints.append(f"  … and {len(valid) - len(shown)} more")
    fail(f"unknown student index {index!r}", *hints)
