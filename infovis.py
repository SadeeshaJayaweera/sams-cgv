#!/usr/bin/env python3
"""Attendance charts for one student, or for the whole class.

The second of the three commands the coursework brief fixes::

    python infovis.py 10000409
    python infovis.py --all

All the drawing lives in ``src/viz/charts.py`` (M9). This file only checks what
the user typed and hands over.
"""

from __future__ import annotations

import argparse
import sys

from src import cli
from src.utils.logging import get_logger, set_debug

log = get_logger("infovis")

CHARTS_MODULE = "src/viz/charts.py"
CHARTS_OWNER = "M9"


def build_parser() -> argparse.ArgumentParser:
    """Command line interface for ``infovis.py``."""
    parser = argparse.ArgumentParser(
        prog="infovis.py",
        description="Show attendance charts for a student, or for everyone.",
    )
    parser.add_argument(
        "index",
        nargs="?",
        help="student index, e.g. 10000409. Omit it and pass --all instead.",
    )
    parser.add_argument(
        "--all", action="store_true", help="chart the whole class rather than one student"
    )
    parser.add_argument(
        "--save-only",
        action="store_true",
        help="write charts to outputs/charts and open no window",
    )
    parser.add_argument("--debug", action="store_true", help="verbose logging")
    return parser


def main(argv: list[str] | None = None) -> int:
    """Entry point. Returns a process exit code."""
    args = build_parser().parse_args(argv)
    set_debug(args.debug)

    if not args.all and args.index is None:
        cli.fail(
            "give a student index, or --all for the whole class",
            "for example: python infovis.py 10000409",
        )
    if args.all and args.index is not None:
        cli.fail("give either a student index or --all, not both")

    # Checked in this order on purpose: an unwritten module is the outer
    # problem, an empty database the next one, and only then is it worth
    # arguing about whether the index exists.
    function_name = "show_all" if args.all else "show_student"
    draw = cli.optional_import("src.viz.charts", function_name)
    if draw is None:
        return cli.not_ready(CHARTS_MODULE, CHARTS_OWNER)

    cli.require_database()

    if args.all:
        log.info("charting attendance for the whole class")
        draw(save_only=args.save_only)
        return 0

    index = cli.resolve_index(args.index)
    log.info("charting attendance for student %s", index)
    draw(index, save_only=args.save_only)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\ninterrupted")
        sys.exit(130)
