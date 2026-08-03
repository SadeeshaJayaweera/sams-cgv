#!/usr/bin/env python3
"""SAMS — read a signing sheet photo and work out who was present.

The first of the three commands the coursework brief fixes::

    python sams.py data/sheets/12.07.2019.png data/info.xml

It shows each image processing step as it happens, saves those steps as
numbered images for the report, and writes the attendance to the local
database.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from src import config
from src.utils.logging import get_logger, set_debug

log = get_logger("sams")


def build_parser() -> argparse.ArgumentParser:
    """Command line interface for ``sams.py``."""
    parser = argparse.ArgumentParser(
        prog="sams.py",
        description=(
            "Process a signing sheet photo into attendance records, showing "
            "every image processing step on the way."
        ),
    )
    parser.add_argument("image", type=Path, help="path to a signing sheet photo")
    parser.add_argument("xml", type=Path, help="path to info.xml")
    parser.add_argument(
        "--no-show", action="store_true", help="do not open the montage window"
    )
    parser.add_argument(
        "--no-save", action="store_true", help="do not write step images"
    )
    parser.add_argument("--debug", action="store_true", help="verbose logging")
    return parser


def validate_paths(image: Path, xml: Path) -> None:
    """Stop with a clear message if either input is not a readable file.

    Raises:
        SystemExit: With code 2, the conventional exit code for a usage error.
    """
    for label, path in (("image", image), ("xml", xml)):
        if not path.exists():
            print(f"error: no {label} file at {path}")
            raise SystemExit(2)
        if not path.is_file():
            print(f"error: {label} path {path} is not a file")
            raise SystemExit(2)


def main(argv: list[str] | None = None) -> int:
    """Entry point. Returns a process exit code."""
    args = build_parser().parse_args(argv)
    set_debug(args.debug)
    config.ensure_dirs()
    validate_paths(args.image, args.xml)

    sheet_date = args.image.stem
    log.info("sheet date %s from filename %s", sheet_date, args.image.name)
    return 0


if __name__ == "__main__":
    sys.exit(main())
