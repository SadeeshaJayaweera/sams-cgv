"""Measure the real input data so BUILD_SPEC.md section 4 can be filled in.

Task T0. This runs *before* ``src/config.py`` exists, so it deliberately
imports nothing from ``src`` and resolves its own paths from the repository
root. Nothing here is part of the pipeline.

Usage::

    python tools/inspect_inputs.py
"""

from __future__ import annotations

import sys
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
SHEETS = ROOT / "data" / "sheets"
INFO_XML = ROOT / "data" / "info.xml"

#: EXIF tag id for image orientation, from the TIFF specification.
EXIF_ORIENTATION = 274
#: How many lines of info.xml to echo, as required by task T0.
XML_PREVIEW_LINES = 40

IMAGE_SUFFIXES = (".png", ".jpg", ".jpeg", ".tif", ".tiff")


class SheetInspector:
    """Report the measurable facts about one signing sheet photo."""

    def __init__(self, path: Path) -> None:
        self.path = path

    def describe(self) -> dict[str, object]:
        """Return the facts BUILD_SPEC.md section 4 asks for."""
        with Image.open(self.path) as image:
            width, height = image.size
            mode = image.mode
            exif = self._exif(image)
            array = np.asarray(image)

        channels = 1 if array.ndim == 2 else array.shape[2]
        return {
            "filename": self.path.name,
            "resolution": f"{width} x {height}",
            "mode": mode,
            "channels": channels,
            "dtype": str(array.dtype),
            "size_mb": self.path.stat().st_size / (1024 * 1024),
            "orientation": exif.get(EXIF_ORIENTATION, "absent"),
            "greyscale_in_practice": self._is_greyscale(array),
        }

    @staticmethod
    def _exif(image: Image.Image) -> dict[int, object]:
        """EXIF tags as a plain dict; an empty dict when the photo has none."""
        raw = getattr(image, "_getexif", lambda: None)()
        return dict(raw) if raw else {}

    @staticmethod
    def _is_greyscale(array: np.ndarray) -> bool:
        """True when a three channel image carries no real colour."""
        if array.ndim == 2 or array.shape[2] == 1:
            return True
        rgb = array[:, :, :3].astype(np.int16)
        spread = rgb.max(axis=2) - rgb.min(axis=2)
        return bool(spread.max() <= 2)

    def report(self) -> None:
        """Print one block of facts for this sheet."""
        facts = self.describe()
        print(f"  {facts['filename']}")
        print(f"    resolution        : {facts['resolution']}")
        print(f"    pillow mode       : {facts['mode']}")
        print(f"    channels          : {facts['channels']}")
        print(f"    dtype             : {facts['dtype']}")
        print(f"    file size         : {facts['size_mb']:.2f} MB")
        print(f"    exif orientation  : {facts['orientation']}")
        print(f"    greyscale content : {facts['greyscale_in_practice']}")
        print()


class XmlInspector:
    """Report the tag structure of ``info.xml``."""

    def __init__(self, path: Path) -> None:
        self.path = path

    def preview(self, lines: int = XML_PREVIEW_LINES) -> None:
        """Echo the first ``lines`` lines of the file."""
        print(f"  first {lines} lines of {self.path.name}")
        print("  " + "-" * 60)
        text = self.path.read_text(encoding="utf-8").splitlines()
        for number, line in enumerate(text[:lines], start=1):
            print(f"  {number:>3} | {line}")
        if len(text) > lines:
            print(f"  ... {len(text) - lines} more lines")
        print()

    def structure(self) -> None:
        """Print every distinct element path and how often it appears."""
        root = ET.parse(self.path).getroot()
        paths: Counter[str] = Counter()
        self._walk(root, root.tag, paths)

        print("  element paths found")
        print("  " + "-" * 60)
        for path, count in paths.items():
            print(f"  {count:>4} x  {path}")
        print()

        students = root.findall(".//student")
        print(f"  students          : {len(students)}")
        if students:
            fields = [child.tag for child in students[0]]
            print(f"  fields per student: {', '.join(fields)}")
            indices = [
                (s.findtext("index") or "").strip() for s in students
            ]
            print(f"  first index       : {indices[0]!r}")
            widths = {len(i) for i in indices}
            print(f"  index lengths     : {sorted(widths)}")
            print(f"  all indices       : {', '.join(indices)}")
        print()

    def _walk(self, node: ET.Element, path: str, paths: Counter[str]) -> None:
        paths[path] += 1
        for child in node:
            self._walk(child, f"{path}/{child.tag}", paths)


def _sheet_paths() -> list[Path]:
    return sorted(
        p for p in SHEETS.iterdir() if p.suffix.lower() in IMAGE_SUFFIXES
    )


def main() -> int:
    """Print the full inspection report. Returns a process exit code."""
    if not SHEETS.is_dir():
        print(f"error: no sheet folder at {SHEETS}")
        return 2

    sheets = _sheet_paths()
    print("=" * 64)
    print(f" SHEETS  ({len(sheets)} found in {SHEETS.relative_to(ROOT)})")
    print("=" * 64)
    for path in sheets:
        SheetInspector(path).report()

    if not INFO_XML.is_file():
        print(f"error: no info.xml at {INFO_XML}")
        return 2

    print("=" * 64)
    print(f" INFO.XML  ({INFO_XML.relative_to(ROOT)})")
    print("=" * 64)
    xml = XmlInspector(INFO_XML)
    xml.preview()
    xml.structure()
    return 0


if __name__ == "__main__":
    sys.exit(main())
