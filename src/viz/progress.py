"""Step-by-step progress viewer.

The brief asks for the image processing to be *shown* as it happens — greyscale,
binarisation and everything else — not just for a final answer. This class is
how that happens. Each stage hands its pictures over as it finishes, the viewer
keeps them in order, and at the end of the run it writes them out and puts them
on screen as one montage.

Nothing here knows what a signing sheet is. It takes labelled images and shows
them, which is why it can serve all nine modules.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from src.utils.logging import get_logger

log = get_logger("progress")


@dataclass(frozen=True)
class Step:
    """One labelled picture from the pipeline, in the order it arrived."""

    name: str
    """Short label, e.g. ``"binarize"``. Becomes part of the filename."""

    image: np.ndarray
    """The picture itself, in whatever form the stage produced it."""

    cmap: str | None = None
    """Matplotlib colormap for single channel images. ``None`` picks a default."""


class ProgressViewer:
    """Collects the images a pipeline run produces, in order.

    Args:
        sheet_date: Identifies the run. Used as the output folder name.
        show: Whether the montage is allowed to open a window.
        save: Whether step images are allowed to be written to disk.
    """

    def __init__(self, sheet_date: str, show: bool = True, save: bool = True) -> None:
        self.sheet_date = sheet_date
        self.show = show
        self.save = save
        self._steps: list[Step] = []

    @property
    def steps(self) -> list[Step]:
        """The steps collected so far, in insertion order."""
        return list(self._steps)

    def __len__(self) -> int:
        return len(self._steps)

    def __repr__(self) -> str:
        return (
            f"<ProgressViewer sheet={self.sheet_date!r} "
            f"steps={len(self._steps)} show={self.show} save={self.save}>"
        )

    def add(self, name: str, image: np.ndarray, cmap: str | None = None) -> None:
        """Register one pipeline step image.

        Args:
            name: Short label for the step.
            image: The picture. Colour images are BGR, as OpenCV produces them.
            cmap: Colormap for a single channel image.

        Raises:
            ValueError: If ``image`` is not a NumPy array with 2 or 3 dimensions.
                Catching this here means a mistake surfaces at the stage that
                made it, not three steps later in Matplotlib.
        """
        if not isinstance(image, np.ndarray):
            raise ValueError(
                f"step {name!r}: expected a numpy array, got {type(image).__name__}"
            )
        if image.ndim not in (2, 3):
            raise ValueError(
                f"step {name!r}: expected a 2D or 3D array, got shape {image.shape}"
            )

        self._steps.append(Step(name=name, image=image, cmap=cmap))
        log.info("[%d] %s … collected  %s", len(self._steps), name, image.shape)

    def add_all(self, figures: dict[str, np.ndarray]) -> None:
        """Register every figure a stage produced, preserving its order."""
        for name, image in figures.items():
            self.add(name, image)
