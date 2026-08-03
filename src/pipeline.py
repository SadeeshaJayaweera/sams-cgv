"""The pipeline runner.

One photo goes in, one context dictionary comes out. The runner owns the order
of the stages and nothing else: it does not know what deskewing is, it does not
know what ink is. That separation is what lets nine people replace one stage at
a time without touching anything here.

The order is fixed by BUILD_SPEC.md section 6.3::

    geometry -> enhance -> binarize -> table -> ink -> decision
"""

from __future__ import annotations

from src.models import SheetMeta, Student
from src.utils.logging import get_logger
from src.utils.stage import Stage

log = get_logger("pipeline")


class Pipeline:
    """Runs a list of stages over one signing sheet.

    Args:
        stages: The stages to run, in order. Whether each one is a real module
            or a stub is the caller's business, not the runner's.
    """

    def __init__(self, stages: list[Stage]) -> None:
        self.stages = list(stages)

    @property
    def stage_names(self) -> list[str]:
        """The names of the stages, in the order they will run."""
        return [stage.name for stage in self.stages]

    def __repr__(self) -> str:
        return f"<Pipeline stages={' -> '.join(self.stage_names)}>"

    def run(self, sheet: SheetMeta, students: list[Student]) -> dict:
        """Run every stage over one sheet.

        Args:
            sheet: Which photo is being processed.
            students: The roll from ``info.xml``, so the decision stage can map
                rows to people.

        Returns:
            The context dictionary, carrying every key the stages wrote. The
            keys are listed in BUILD_SPEC.md section 6.3.
        """
        ctx: dict = {"sheet": sheet, "students": students}
        log.info("processing sheet %s  (%s)", sheet.date, sheet.path.name)
        log.info("stages: %s", " -> ".join(self.stage_names))

        for position, stage in enumerate(self.stages, start=1):
            log.info("[%d/%d] stage %r starting", position, len(self.stages), stage.name)
            ctx = stage.run(ctx)
            log.info("[%d/%d] stage %r done", position, len(self.stages), stage.name)

        return ctx
