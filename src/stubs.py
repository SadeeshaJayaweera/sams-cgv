"""Placeholder stages, so the pipeline runs end to end from the first hour.

Nine people cannot all wait for stage one. Every module that is not written yet
has a stub here that writes a type-correct value into the context, logs loudly
that it is a stub, and gets out of the way. ``sams.py`` therefore reaches its
summary table on day one, and every member can see their own stage slot in the
montage before they have written a line.

Each stub is deleted the moment its real module is merged — see BUILD_SPEC.md
section 8. Nothing here may survive to submission::

    grep -r "STUB" src/     # must print nothing before tagging

Image stubs read from ``data/fixtures/``, produced by ``tools/make_fixtures.py``.
That folder is not committed, so every stub also has a fallback that keeps a
fresh clone running rather than crashing on a missing file.
"""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np

from src import config
from src.utils.logging import get_logger
from src.utils.stage import Stage

log = get_logger("stubs")


class _Stub(Stage):
    """Shared behaviour: announce loudly that this is not the real thing."""

    owner: str = "M?"
    """Which member owns the module this stub is standing in for."""

    def announce(self) -> None:
        """Log the line every stub must print, exactly once per run."""
        log.warning("STUB %s: returning placeholder data (owned by %s)", self.name, self.owner)

    def _fixture(self, filename: str, flags: int = cv2.IMREAD_COLOR) -> np.ndarray | None:
        """Load one bootstrap fixture, or ``None`` with a helpful warning."""
        path: Path = config.FIXTURES / filename
        if not path.is_file():
            log.warning(
                "fixture %s is missing — run `python tools/make_fixtures.py`",
                path.relative_to(config.ROOT),
            )
            return None
        image = cv2.imread(str(path), flags)
        if image is None:
            log.warning("fixture %s could not be decoded by OpenCV", path)
        return image


# STUB — owned by M3, delete when their module lands
class EnhanceStub(_Stub):
    """Stands in for shadow removal and contrast enhancement.

    Plain ``cvtColor``. No denoising, no illumination correction — that is the
    whole of M3's job and the difference will be visible in the montage.
    """

    name = "enhance"
    owner = "M3"

    def __init__(self) -> None:
        self._grey: np.ndarray | None = None

    def run(self, ctx: dict) -> dict:
        self.announce()
        grey = cv2.cvtColor(ctx["warped"], cv2.COLOR_BGR2GRAY)
        ctx["grey"] = grey
        self._grey = grey
        return ctx

    def figures(self) -> dict[str, np.ndarray]:
        return {} if self._grey is None else {"grey": self._grey}


# STUB — owned by M4, delete when their module lands
class BinarizeStub(_Stub):
    """Stands in for adaptive thresholding and morphology.

    Global Otsu, inverted so that ink is 255 and paper is 0, which is the
    convention the whole project assumes. A single global threshold is exactly
    what fails on a shadowed corner, which is why M4 exists.
    """

    name = "binarize"
    owner = "M4"

    def __init__(self) -> None:
        self._binary: np.ndarray | None = None

    def run(self, ctx: dict) -> dict:
        self.announce()
        threshold, binary = cv2.threshold(
            ctx["grey"], 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU
        )
        log.debug("otsu threshold = %.0f", threshold)
        ctx["binary"] = binary
        self._binary = binary
        return ctx

    def figures(self) -> dict[str, np.ndarray]:
        return {} if self._binary is None else {"binary": self._binary}


# STUB — owned by M5, delete when their module lands
class TableStub(_Stub):
    """Stands in for line detection, grid building and cell extraction.

    Produces no grid and no cells, so everything downstream reports zero. The
    summary table showing 0 students found is the honest answer until M5 lands.
    """

    name = "table"
    owner = "M5"

    def run(self, ctx: dict) -> dict:
        self.announce()
        ctx["grid"] = None
        ctx["cells"] = []
        return ctx


# STUB — owned by M6, delete when their module lands
class InkStub(_Stub):
    """Stands in for cell cleaning and ink segmentation."""

    name = "ink"
    owner = "M6"

    def run(self, ctx: dict) -> dict:
        self.announce()
        ctx["ink"] = []
        return ctx


# STUB — owned by M7, delete when their module lands
class DecisionStub(_Stub):
    """Stands in for the present or absent decision and the database write."""

    name = "decision"
    owner = "M7"

    def run(self, ctx: dict) -> dict:
        self.announce()
        ctx["records"] = []
        return ctx


# STUB — owned by M7, delete when their module lands
def parse_students(xml_path: Path) -> list:
    """Stand-in for ``src.io.xml_parser.parse_students``.

    The real parser returns ``list[Student]`` read from ``info.xml``. Until it
    exists this returns an empty list, so ``sams.py`` reports zero students
    rather than inventing any.
    """
    log.warning("STUB xml_parser: returning no students (owned by M7)")
    return []
