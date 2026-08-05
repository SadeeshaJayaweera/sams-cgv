"""Tests for the pipeline runner, the progress viewer and the CLI shells.

Everything M1 owns that can break silently is covered here: the order stages
run in, whether a failure names the stage that caused it, whether the step
images land where the report expects them, and whether a mistyped filename
gives a message instead of a traceback.

``matplotlib.use("Agg")`` before any pyplot import — the test run must never
try to open a window.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import numpy as np  # noqa: E402
import pytest  # noqa: E402

from src.models import AttendanceRecord, SheetMeta, Student  # noqa: E402
from src.pipeline import Pipeline, PipelineError  # noqa: E402
from src.utils.stage import Stage  # noqa: E402
from src.viz.progress import ProgressViewer  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent


# --- helpers ---------------------------------------------------------------


class RecordingStage(Stage):
    """A stage that notes it ran, so ordering can be asserted."""

    def __init__(self, name: str, log: list[str]) -> None:
        self.name = name
        self._log = log

    def run(self, ctx: dict) -> dict:
        self._log.append(self.name)
        ctx[self.name] = True
        return ctx


class FailingStage(Stage):
    """A stage that always raises, to test error reporting."""

    name = "table"

    def run(self, ctx: dict) -> dict:
        raise ValueError("no horizontal lines found")


class DrawingStage(Stage):
    """A stage that produces figures, to test viewer forwarding."""

    name = "binarize"

    def run(self, ctx: dict) -> dict:
        return ctx

    def figures(self) -> dict[str, np.ndarray]:
        return {"binary": np.zeros((8, 6), np.uint8)}


def a_sheet() -> SheetMeta:
    return SheetMeta(path=REPO_ROOT / "data" / "sheets" / "12.07.2019.png", date="12.07.2019")


# --- the six tests the spec asks for ---------------------------------------


def test_pipeline_runs_stages_in_the_given_order() -> None:
    """Spec section 11.1 — order is the runner's whole job."""
    ran: list[str] = []
    stages = [RecordingStage(name, ran) for name in ("geometry", "enhance", "binarize")]

    ctx = Pipeline(stages).run(a_sheet(), [])

    assert ran == ["geometry", "enhance", "binarize"]
    assert all(ctx[name] for name in ran)


def test_failing_stage_error_names_that_stage() -> None:
    """Spec section 11.2 — with nine people's code, the name is the message."""
    ran: list[str] = []
    stages = [RecordingStage("geometry", ran), FailingStage(), RecordingStage("ink", ran)]

    with pytest.raises(PipelineError) as caught:
        Pipeline(stages).run(a_sheet(), [])

    assert "table" in str(caught.value)
    assert caught.value.stage == "table"
    assert isinstance(caught.value.__cause__, ValueError)
    assert ran == ["geometry"], "the run must stop at the failure, not carry on"


def test_save_all_writes_numbered_files(tmp_path: Path) -> None:
    """Spec section 11.3 — N files, numbered from 01, in order."""
    viewer = ProgressViewer("12.07.2019", show=False, steps_root=tmp_path)
    for name in ("original", "warped", "grey", "binary"):
        viewer.add(name, np.zeros((12, 9, 3), np.uint8))

    written = viewer.save_all()

    assert len(written) == 4
    assert [path.name for path in written] == [
        "01_original.png",
        "02_warped.png",
        "03_grey.png",
        "04_binary.png",
    ]
    assert sorted(p.name for p in (tmp_path / "12.07.2019").iterdir()) == [
        path.name for path in written
    ]


def test_add_accepts_colour_and_single_channel_images() -> None:
    """Spec section 11.4 — stages hand over both kinds."""
    viewer = ProgressViewer("12.07.2019", show=False, save=False)
    viewer.add("colour", np.zeros((10, 10, 3), np.uint8))
    viewer.add("grey", np.zeros((10, 10), np.uint8))

    assert len(viewer) == 2

    colour, colour_cmap = viewer._for_display(viewer.steps[0])
    grey, grey_cmap = viewer._for_display(viewer.steps[1])

    assert colour.ndim == 3 and colour_cmap is None
    assert grey.ndim == 2 and grey_cmap == "gray"


def test_sams_exits_with_code_2_when_the_image_is_missing() -> None:
    """Spec section 11.5 — a user mistake, so a message and no traceback."""
    result = subprocess.run(
        [sys.executable, "sams.py", "no_such_sheet.png", "data/info.xml"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 2
    assert "no signing sheet image" in result.stdout
    assert "Traceback" not in result.stderr


def test_student_index_keeps_its_leading_zeros() -> None:
    """Spec section 11.6 — the single most damaging thing to get wrong."""
    student = Student("007", "James Bond")

    assert student.index == "007"
    assert isinstance(student.index, str)


# --- further cover for the same code ---------------------------------------


def test_pipeline_forwards_stage_figures_to_the_viewer() -> None:
    viewer = ProgressViewer("12.07.2019", show=False, save=False)

    Pipeline([DrawingStage()], viewer=viewer).run(a_sheet(), [])

    assert [step.name for step in viewer.steps] == ["binary"]


def test_pipeline_records_a_timing_for_every_stage() -> None:
    ran: list[str] = []
    pipeline = Pipeline([RecordingStage(name, ran) for name in ("enhance", "binarize")])

    pipeline.run(a_sheet(), [])

    assert sorted(pipeline.timings()) == ["binarize", "enhance"]
    assert pipeline.duration() >= 0.0


def test_bad_step_image_is_rejected_where_it_was_produced() -> None:
    viewer = ProgressViewer("12.07.2019", show=False, save=False)

    with pytest.raises(ValueError, match="numpy array"):
        viewer.add("oops", "not an image")  # type: ignore[arg-type]


def test_save_all_does_nothing_when_saving_is_off(tmp_path: Path) -> None:
    viewer = ProgressViewer("12.07.2019", show=False, save=False, steps_root=tmp_path)
    viewer.add("grey", np.zeros((4, 4), np.uint8))

    assert viewer.save_all() == []
    assert not (tmp_path / "12.07.2019").exists()


def test_montage_covers_every_step(tmp_path: Path) -> None:
    viewer = ProgressViewer("12.07.2019", show=False, steps_root=tmp_path)
    for name in ("original", "warped", "grey", "binary", "cells"):
        viewer.add(name, np.zeros((10, 8, 3), np.uint8))

    path = viewer.save_montage(tmp_path / "montage.png")

    assert path.is_file() and path.stat().st_size > 0
    assert ProgressViewer._grid(5) == (2, 4)


def test_montage_of_nothing_is_an_error() -> None:
    with pytest.raises(RuntimeError, match="nothing to show"):
        ProgressViewer("12.07.2019", show=False, save=False).build_montage()


def test_summary_counts_present_absent_and_uncertain() -> None:
    from sams import RunSummary

    records = [
        AttendanceRecord("10000409", "12.07.2019", present=True, confidence=0.95),
        AttendanceRecord("10009301", "12.07.2019", present=False, confidence=0.90),
        AttendanceRecord("10009302", "12.07.2019", present=True, confidence=0.51),
    ]
    summary = RunSummary(
        sheet_date="12.07.2019",
        students=3,
        records=records,
        duration=1.5,
        steps_dir=REPO_ROOT / "outputs" / "steps" / "12.07.2019",
        step_count=8,
    )

    assert (summary.present, summary.absent, summary.uncertain) == (2, 1, 1)

    rendered = summary.render()
    assert " Present   : 2" in rendered
    assert " Absent    : 1" in rendered
    assert " Uncertain : 1" in rendered
    assert "(8 images)" in rendered


@pytest.mark.parametrize("command", ["sams.py", "infovis.py", "investigate.py"])
def test_every_command_has_working_help(command: str) -> None:
    result = subprocess.run(
        [sys.executable, command, "--help"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert result.stdout.startswith(f"usage: {command}")


def test_every_module_under_src_imports() -> None:
    """No module in the project is broken at import time.

    Both M2 modules reached `main` importing constants that did not exist in
    `src/config.py`, and the whole suite stayed green because nothing else
    imported them. A module that cannot be imported cannot be reviewed,
    tested or run, so the suite checks all of them from now on.
    """
    import importlib
    import pkgutil

    import src

    failures: list[str] = []
    for info in pkgutil.walk_packages(src.__path__, prefix="src."):
        try:
            importlib.import_module(info.name)
        except Exception as error:  # noqa: BLE001 - reported, not swallowed
            failures.append(f"{info.name}: {type(error).__name__}: {error}")

    assert not failures, "modules failed to import:\n  " + "\n  ".join(failures)


def test_infovis_without_an_index_explains_itself() -> None:
    result = subprocess.run(
        [sys.executable, "infovis.py"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 2
    assert "give a student index" in result.stdout
    assert "Traceback" not in result.stderr
