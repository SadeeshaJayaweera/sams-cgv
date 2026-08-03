# BUILD_SPEC.md — SAMS (Student Attendance Management System)

**Repository root file. This is the single source of truth for Claude Code.**
Owner of this file: **M1 (Lead / Integration)**. Nobody else edits it — they raise a change request.

Module: CS402.3 Computer Graphics and Visualization, NSBM Green University
Coursework weight: 20% — Prototype 60%, Report 25%, Individual contribution 15%
Group size: 9 (brief asks for 10; pending confirmation with the module leader)

---

## 0. How an agent must use this file

1. Read this whole file before writing code.
2. Only implement tasks under **§9 M1 task list**. Every other module belongs to another person.
3. For modules M1 does not own, create **stubs only** (see §8). Never write a real implementation for someone else's file.
4. Work task by task, in order. Commit after each task with the exact message given.
5. After each task, run the verification command listed for it. Do not move on if it fails.
6. If reality contradicts this spec (for example the real `info.xml` has different tags), **update this file first**, commit that change, then write the code.

---

## 1. Goal

Take a phone photo of a paper attendance signing sheet, work out who signed and who did not, store the result in a local database, and visualise it.

Three commands must work. These are fixed by the coursework brief and must never change:

```bash
python sams.py data/sheets/10.07.2019.png data/info.xml
python infovis.py 001
python investigate.py 001
```

The *shape* of those three commands is fixed. The arguments in them are the brief's illustration, not our data: T0 measured that our five sheets are dated `31.05.2019`, `21.06.2019`, `28.06.2019`, `05.07.2019`, `12.07.2019` and that student indices are 8 digits. The equivalent real invocations are:

```bash
python sams.py data/sheets/12.07.2019.png data/info.xml
python infovis.py 10000409
python investigate.py 10000409
```

M1 delivers: the repository skeleton, shared contracts, the pipeline runner, all three CLI programs, the step-by-step progress viewer, and stubs for every other module so the pipeline runs end to end from the first hour.

---

## 2. Non-negotiables

- **CLI only.** No web app, no desktop GUI, no Streamlit, no Flask. It earns no marks and costs time.
- **Ink is 255 (white). Paper is 0 (black).** Every module assumes this.
- **Student indices are strings.** `"007"`, never `7`. Leading zeros must survive.
- **No tunable number is hard-coded in a module.** All constants live in `src/config.py`.
- **Every stage subclasses `Stage`.** OOP quality is explicitly marked.
- **No file is written outside `outputs/` and `data/attendance.db`.**
- Python **3.11+**.
- The pipeline must **never silently swallow an error**. Log the failing stage name and re-raise.

---

## 3. Environment

Development machine is Arch-based Linux (CachyOS), fish shell.

```fish
python -m venv .venv
source .venv/bin/activate.fish
pip install -r requirements.txt
```

`requirements.txt` (unpinned during development, pinned at T10):

```
opencv-python
numpy
scikit-image
scipy
matplotlib
seaborn
pandas
scikit-learn
pytest
Pillow
```

Notes:
- Do **not** `pip install` into the system Python on Arch — it is externally managed. Always use the venv.
- `opencv-python` (not `opencv-python-headless`) — we need `cv2.imshow` availability even though Matplotlib is the primary display.
- Matplotlib backend: use the default interactive backend for normal runs, and `Agg` inside tests (`matplotlib.use("Agg")` at the top of test files).

---

## 4. Input data — verify before coding

The five sheet photos come from `CGV Signing Sheets.zip`. They arrived as `1.jpeg` … `5.jpeg`, so T0 renamed each to the date printed on the sheet and converted it to lossless PNG:

```
data/sheets/31.05.2019.png    # was 1.jpeg
data/sheets/21.06.2019.png    # was 2.jpeg
data/sheets/28.06.2019.png    # was 3.jpeg
data/sheets/05.07.2019.png    # was 4.jpeg
data/sheets/12.07.2019.png    # was 5.jpeg
data/info.xml
data/ground_truth.csv         # transcribed by eye, used by M7 and M9 for accuracy
```

`info.xml` was **not** in the material we received. It is reconstructed from Figure 1 of the brief plus the printed student table on the sheets — see the deviations below.

**Measured facts (T0, `python tools/inspect_inputs.py`):**

| Fact | Value | How to get it |
|---|---|---|
| Number of sheets | 5 | `ls data/sheets` |
| Image resolution (per sheet) | 3024 x 4032 portrait, all five identical | `tools/inspect_inputs.py` |
| Colour or greyscale photos | Colour, 3 channel uint8 RGB (iPhone 7, iOS 12.1.4) | channel check |
| EXIF orientation present | No — tag 274 absent, pixels already upright | Pillow `_getexif()` |
| Table columns on the sheet | **5** — `No`, `Student No`, `Title`, `Student Name`, `Signature` | look at the image |
| Data rows per sheet | 6 on every sheet | count by eye |
| Header row present | Yes, one, printed in bold | look |
| `info.xml` root tag | `nsbm` | `head data/info.xml` |
| `info.xml` student tag path | `nsbm/students/batches/batch/student` with `index`, `title`, `name` | read it |
| Index format in XML | 8 digits, e.g. `10000409` — not `001` | inspection report |
| Do sheet rows match XML order? | Yes — the XML was transcribed in sheet row order | compare |

**Deviations from the assumptions this spec was written under. Every one of these is load-bearing:**

1. **The signature column is index 4, not 3.** The sheet has a `Title` column (`Mr` / `Ms`) between the student number and the name. `SIGNATURE_COL = 4` in §6.4, and `Cell.col` in §6.1 means `0=No, 1=Student No, 2=Title, 3=Student Name, 4=Signature`.
2. **There are two tables on each sheet.** A one-row lecture header table (`Date | time | Lecture's Name | Signatue`) sits directly above the student table. M5 must take the **lower, taller** table and ignore the header table, otherwise the lecturer's own signature is read as a student's.
3. **Indices are 8 digits, not 3.** They are still strings — `"10000409"` — and `infovis.py 001` from the brief has no matching student in our data. The CLIs accept any index string and report unknown ones helpfully.
4. **The brief's `info.xml` is not well-formed.** Figure 1 shows `<15>` as the batch element. XML tag names may not start with a digit, so no standard parser will read that document. We carry the batch as `<batch year="2016.1">`. M7's parser should locate students with `.//student` so it survives either shape.
5. **`info.xml` carries a `<title>` element** per student, matching the sheet's Title column. Figure 1 has only `index` and `name`.
6. **Signature strokes routinely cross cell borders.** On `31.05.2019` and `05.07.2019` a signature spills a long way into the row below. M5's cells and M6's ink masks cannot assume a signature is contained by its box.
7. **Ink is not always a signature.** On `21.06.2019` the last cell holds the lecturer's handwritten `ab` (absent); on `05.07.2019` one cell holds a stray red pen tick. Both are ink and both mean *absent*. Pure ink-ratio thresholding gets these wrong — this is exactly the discussion M7's decision stage must handle and the report must cover.
8. **Six students, five sheets = 30 records** in total. Small enough that the summary table in §7 shows single digit counts, not the 42 in the illustration.

Once measured, **replace the TBDs in this file and commit** before writing pipeline code. M5 and M7 depend on these answers.

---

## 5. Repository layout

```
sams-cgv/
├── BUILD_SPEC.md              # this file — M1
├── README.md                  # M1
├── requirements.txt           # M1
├── .gitignore                 # M1
├── sams.py                    # M1
├── infovis.py                 # M1
├── investigate.py             # M1
├── src/
│   ├── __init__.py
│   ├── config.py              # M1 owns the file; each member adds a commented block
│   ├── models.py              # M1
│   ├── pipeline.py            # M1
│   ├── cli.py                 # M1 — shared helpers for the three programs
│   ├── stubs.py               # M1 — placeholder stages, deleted stage by stage
│   ├── utils/
│   │   ├── stage.py           # M1
│   │   ├── logging.py         # M1
│   │   └── timing.py          # M1
│   ├── io/
│   │   ├── image_loader.py    # M2
│   │   ├── xml_parser.py      # M7
│   │   └── db.py              # M7
│   ├── preprocess/
│   │   ├── deskew.py          # M2
│   │   ├── enhance.py         # M3
│   │   └── binarize.py        # M4
│   ├── table/
│   │   ├── line_detect.py     # M5
│   │   ├── grid_builder.py    # M5
│   │   └── cell_extract.py    # M5
│   ├── detect/
│   │   ├── cell_clean.py      # M6
│   │   ├── ink_mask.py        # M6
│   │   └── presence.py        # M7
│   ├── recognise/             # M8 (4 files)
│   └── viz/
│       ├── progress.py        # M1
│       ├── charts.py          # M9
│       └── style.py           # M9
├── tools/
│   ├── inspect_inputs.py      # M1
│   ├── make_fixtures.py       # M1
│   ├── make_m1_figures.py     # M1 — the three figures in §13
│   ├── seed_db.py             # M7
│   ├── run_all_sheets.py      # M9
│   └── make_report_assets.py  # M9
├── tests/
├── data/
│   ├── sheets/  info.xml  fixtures/  ground_truth.csv  attendance.db
├── outputs/
│   ├── steps/  cells/  charts/  figures/
└── docs/
    └── contrib_m1.md … contrib_m9.md
```

`.gitignore` must contain: `.venv/`, `__pycache__/`, `*.pyc`, `outputs/`, `data/attendance.db`, `data/fixtures/`, `.pytest_cache/`.

**`data/sheets/` and `data/info.xml` ARE committed** — the marker needs them to run the prototype.

---

## 6. Shared contracts

### 6.1 `src/models.py`

```python
from dataclasses import dataclass
from pathlib import Path
import numpy as np

@dataclass
class Student:
    index: str                              # "001" — always a string
    name: str
    row: int | None = None                  # sheet row, filled by M7

@dataclass
class SheetMeta:
    path: Path
    date: str                               # from the filename, e.g. "10.07.2019"
    subject_code: str = ""

@dataclass
class Cell:
    row: int                                # 0 = first DATA row, header excluded
    col: int                                # 0=No, 1=index, 2=title, 3=name, 4=signature
    bbox: tuple[int, int, int, int]         # x, y, w, h in the warped image
    image: np.ndarray | None = None         # BGR crop
    student_index: str | None = None

@dataclass
class InkResult:
    cell: Cell
    mask: np.ndarray | None = None          # uint8, ink = 255
    ink_ratio: float = 0.0
    components: int = 0
    stroke_bbox: tuple[int, int, int, int] | None = None
    aspect: float = 0.0
    stroke_length: int = 0
    crop_path: str | None = None
    mask_path: str | None = None

@dataclass
class AttendanceRecord:
    student_index: str
    sheet_date: str
    present: bool
    confidence: float
    ink_ratio: float = 0.0
```

### 6.2 `src/utils/stage.py`

```python
from abc import ABC, abstractmethod
import numpy as np

class Stage(ABC):
    """One step of the image pipeline."""
    name: str = "stage"

    @abstractmethod
    def run(self, ctx: dict) -> dict:
        """Read from ctx, write results back into ctx, return ctx."""

    def figures(self) -> dict[str, np.ndarray]:
        """Images this stage wants shown and saved. Default: none."""
        return {}
```

### 6.3 The context dictionary

Single object passed down the line. Keys are fixed.

| key | type | written by | read by |
|---|---|---|---|
| `sheet` | `SheetMeta` | M1 | all |
| `students` | `list[Student]` | M1 (via M7 parser) | M7 |
| `bgr` | BGR uint8 | M2 | M2 |
| `warped` | BGR uint8, flattened sheet | M2 | M3, M5 |
| `grey` | uint8, 1 channel | M3 | M4 |
| `binary` | uint8, ink=255 | M4 | M5 |
| `grid` | `Grid` | M5 | M5 |
| `cells` | `list[Cell]`, signature column, `.image` set from `warped` | M5 | M6 |
| `ink` | `list[InkResult]`, same order as `cells` | M6 | M7 |
| `records` | `list[AttendanceRecord]` | M7 | M1 |

**Stage order is fixed:**
`geometry → enhance → binarize → table → ink → decision`

### 6.4 `src/config.py`

M1 writes the header and the M1 block. Each member appends their own block under a comment banner. Nobody edits another member's block.

```python
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
SHEETS = DATA / "sheets"
FIXTURES = DATA / "fixtures"
OUTPUTS = ROOT / "outputs"
STEPS = OUTPUTS / "steps"
CELLS = OUTPUTS / "cells"
CHARTS = OUTPUTS / "charts"
FIGURES = OUTPUTS / "figures"
DB_PATH = DATA / "attendance.db"
INFO_XML = DATA / "info.xml"

SIGNATURE_COL = 4          # measured in T0: the sheet has a Title column
SAVE_STEPS = True
SHOW_PROGRESS = True
FIGURE_DPI = 150

def ensure_dirs() -> None:
    for p in (OUTPUTS, STEPS, CELLS, CHARTS, FIGURES, FIXTURES):
        p.mkdir(parents=True, exist_ok=True)

# --- M2 geometry ---
# --- M3 enhancement ---
# --- M4 binarisation ---
# --- M5 table detection ---
# --- M6 ink segmentation ---
# --- M7 decision ---
# --- M8 recognition ---
# --- M9 visualisation ---
```

### 6.5 Entry points the CLIs call

The three programs are thin wrappers. They must not know how anything works, only what to call. These are the functions M1's CLIs import; until a module lands, `src/cli.py` catches the `ImportError` and prints *module not ready yet*.

| Function | Owner | Returns |
|---|---|---|
| `src.io.xml_parser.parse_students(path: Path) -> list[Student]` | M7 | the roll, in sheet row order |
| `src.io.db.known_indices() -> list[str]` | M7 | every student index the database has a record for |
| `src.io.db.is_empty() -> bool` | M7 | `True` when no attendance has been stored yet |
| `src.viz.charts.show_student(index: str, save_only: bool) -> None` | M9 | draws one student's attendance |
| `src.viz.charts.show_all(save_only: bool) -> None` | M9 | draws the whole class |
| `src.recognise.matcher.investigate(index: str, save_only: bool) -> None` | M8 | compares that student's signatures and reports mismatches |

`save_only=True` means write to `outputs/` and open no window — needed so the whole prototype can be run over SSH or in a test.

### 6.6 `src/cli.py`

M1 owns a small shared helper module for the three programs: index validation, the *module not ready* message, and the friendly-error-then-`exit(2)` path. It exists so the same 20 lines are not written three times, and so all three commands fail in exactly the same way.

---

## 7. CLI specifications

### `sams.py`

```
usage: sams.py [-h] [--no-show] [--no-save] [--debug] image xml

positional:
  image          path to a signing sheet photo
  xml            path to info.xml

options:
  --no-show      do not open the montage window
  --no-save      do not write step images
  --debug        verbose logging
```

Behaviour:
1. `config.ensure_dirs()`
2. Validate both paths. Missing file → print a clear message, `sys.exit(2)`. No traceback.
3. Derive `sheet_date` from the image filename stem.
4. Parse `info.xml` → `ctx["students"]` (via M7's parser; stub returns an empty list).
5. Build the stage list in the fixed order and run the `Pipeline`.
6. Print the summary table.
7. `viewer.save_all()` then `viewer.show_montage()` unless suppressed.

Required final output:

```
─────────────────────────────────────────────────────────────
 Sheet     : 10.07.2019
 Students  : 42
 Present   : 38
 Absent    : 4
 Uncertain : 1
 Duration  : 6.24 s
 Steps     : outputs/steps/10.07.2019/  (8 images)
─────────────────────────────────────────────────────────────
```

### `infovis.py`

```
usage: infovis.py [-h] [--all] [--save-only] [index]
```
Unknown index → print a message plus up to 10 valid indices, `sys.exit(2)`. Empty database → tell the user to run `sams.py` first. Delegates to `src/viz/charts.py` (M9).

### `investigate.py`

```
usage: investigate.py [-h] [--save-only] index
```
Fewer than 2 signature samples → clear message, exit 0 (not an error). Delegates to `src/recognise/matcher.py` (M8).

A *signature sample* means a saved crop at `outputs/cells/<sheet_date>/<index>.png` (§5.4). Counting files needs no database and no other module, so `investigate.py` can give a straight answer before M7 or M8 exist.

---

## 8. Stub policy

M1 creates `src/stubs.py` containing a placeholder `Stage` subclass for **every** module not yet written, so `sams.py` runs end to end immediately.

Rules for stubs:
- Each stub logs `STUB <name>: returning placeholder data`.
- Each stub writes a **type-correct** value into `ctx` (an empty list, a grey copy, whatever the contract says) so downstream code does not crash.
- Stubs read from `data/fixtures/` where an image is needed. The one exception is `bgr`: `GeometryStub` loads the photo the user actually passed on the command line, because faking file loading would make `sams.py <any sheet>` show the same picture for all five sheets and hide real problems such as an unreadable file.
- `data/fixtures/` is not committed. A stub that needs a fixture and cannot find one falls back to something type-correct, logs a `WARNING` naming `tools/make_fixtures.py`, and keeps the run alive. A fresh clone must reach the summary table without running any tool first.
- Every stub carries `# STUB — owned by M<N>, delete when their module lands`.
- A stub is deleted the moment the real module is merged. Stubs must not survive to submission — grep for `STUB` before tagging the release.

| Stub | Writes to ctx |
|---|---|
| `GeometryStub` | `bgr` ← the real photo at `sheet.path`; `warped` ← `fixtures/warped.png` |
| `EnhanceStub` | `grey` ← `cvtColor(warped, BGR2GRAY)` |
| `BinarizeStub` | `binary` ← Otsu on `grey`, inverted |
| `TableStub` | `grid=None`, `cells=[]` |
| `InkStub` | `ink=[]` |
| `DecisionStub` | `records=[]` |

---

## 9. M1 task list

Work in this order. Each task: implement → verify → commit.

---

### T0 — Inspect the real input data
Write `tools/inspect_inputs.py`. It prints per sheet: filename, resolution, channel count, file size, EXIF orientation tag. Then it prints the first 40 lines of `info.xml` and the tag structure found. Run it and **fill in the §4 table in this file**.

**Verify:** `python tools/inspect_inputs.py` prints one block per sheet and the XML structure.
**Commits:**
- `chore(tools): add input inspection script for sheets and xml`
- `docs(spec): record measured input data facts in build spec`

---

### T1 — Repository skeleton  *(blocking — nobody else starts before this)*
Full folder tree from §5, all `__init__.py` files, `requirements.txt`, `.gitignore`, a placeholder `README.md`. Commit the sheet images and `info.xml` into `data/`.

**Verify:** `python -c "import src"` succeeds; `git status` is clean; `outputs/` is ignored.
**Commits:**
- `chore(repo): add project skeleton and package structure`
- `chore(repo): add requirements and gitignore`
- `chore(data): add signing sheet images and info.xml`

---

### T2 — Shared contracts  *(blocking)*
`src/models.py`, `src/utils/stage.py`, `src/config.py` exactly as §6. Push to `main` and tell the group immediately.

**Verify:** `python -c "from src.models import Student; print(Student('007','A').index)"` prints `007` as a string.
**Commits:**
- `feat(core): add shared dataclasses for students, cells and attendance`
- `feat(core): add abstract Stage base class for pipeline steps`
- `feat(core): add central config with paths and shared constants`

---

### T3 — Logging and timing
`src/utils/logging.py` → `get_logger(name)`, format `[HH:MM:SS] LEVEL  module | message`, level controlled by a `DEBUG` flag.
`src/utils/timing.py` → `@timed` decorator recording seconds into a module-level dict for later reporting, and logging `stage 'binarize' finished in 0.42 s`.

**Verify:** a throwaway script logs a line and a duration.
**Commits:**
- `feat(utils): add project logger with consistent formatting`
- `feat(utils): add timed decorator to measure stage duration`

---

### T4 — Bootstrap fixtures  *(blocking — unblocks M4, M5, M6, M7, M8)*
`tools/make_fixtures.py`. Deliberately crude one-liner OpenCV, **not** the real pipeline. Takes the first sheet and writes:

```
data/fixtures/warped.png        # manual crop, no perspective correction
data/fixtures/grey.png
data/fixtures/binary.png        # Otsu, inverted so ink is white
data/fixtures/cell_sample.png   # one hand-picked signature cell, BGR
```

Docstring must state clearly: *temporary scaffolding so downstream modules can start; delete once M2–M4 land.*

**Verify:** the four files exist and open correctly.
**Commit:** `chore(tools): generate bootstrap fixtures so downstream modules can start`

---

### T5 — Progress viewer
`src/viz/progress.py`:

```python
class ProgressViewer:
    def __init__(self, sheet_date: str, show: bool = True, save: bool = True): ...
    def add(self, name: str, image: np.ndarray, cmap: str | None = None) -> None: ...
    def save_all(self) -> None:          # outputs/steps/<date>/NN_name.png
    def show_montage(self) -> None:      # matplotlib grid, titled, tight_layout
```

Rules: preserve insertion order; auto-number from 01; convert BGR→RGB for Matplotlib; handle single-channel images with a grey colormap; log `[3/8] binarize … saved` as each is added; the montage grid shape adapts to the number of steps.

**Verify:** feed it 4 test images → `outputs/steps/test/01_*.png` … `04_*.png` exist and a montage window opens.
**Commits:**
- `feat(viz): add ProgressViewer to collect pipeline step images`
- `feat(viz): save numbered step images to outputs/steps`
- `feat(viz): add matplotlib montage of all processing steps`
- `fix(viz): convert bgr to rgb and handle single channel images`

---

### T6 — Stubs
`src/stubs.py` per §8.

**Verify:** each stub instantiates and `run({})` returns a dict with the right keys.
**Commit:** `feat(core): add placeholder stages so the pipeline runs end to end`

---

### T7 — Pipeline runner
`src/pipeline.py`:

```python
class Pipeline:
    def __init__(self, stages: list[Stage], viewer: ProgressViewer | None = None): ...
    def run(self, sheet: SheetMeta, students: list[Student]) -> dict: ...
```

Behaviour: build `ctx`; for each stage — log start, time it, call `run`, push `figures()` into the viewer, log finish. On exception: log `stage 'table' failed: <message>` and re-raise wrapped in a `PipelineError` carrying the stage name. Never continue past a failure.

**Verify:** a fake two-stage pipeline runs in order; a deliberately failing stage produces an error naming that stage.
**Commits:**
- `feat(pipeline): add Pipeline runner executing stages in fixed order`
- `feat(pipeline): forward stage figures to the progress viewer`
- `feat(pipeline): record per stage timings`
- `fix(pipeline): raise PipelineError naming the failing stage`

---

### T8 — `sams.py`
Per §7. Assemble the stage list from real modules where available, stubs otherwise, chosen by a single `STAGES` list at the top of the file so swapping one stage is a one-line change.

**Verify:** `python sams.py data/sheets/<first>.png data/info.xml` runs to the summary table using stubs, and `python sams.py missing.png data/info.xml` exits with code 2 and a friendly message.
**Commits:**
- `feat(cli): add sams.py entry point with argument parsing and validation`
- `feat(cli): wire stage list into the sams pipeline`
- `feat(cli): print attendance summary table after processing`
- `fix(cli): exit with a clear message when input files are missing`

---

### T9 — `infovis.py` and `investigate.py`
Thin wrappers only. Argument parsing, validation, friendly errors, then delegate. While M8 and M9 are unfinished, print `module not ready yet — this command will work once M9/M8 lands` and exit 0.

**Verify:** both commands run and produce the placeholder message; `--help` works on all three.
**Commits:**
- `feat(cli): add infovis.py entry point for attendance charts`
- `feat(cli): add investigate.py entry point for signature checking`
- `fix(cli): handle unknown student index with helpful output`

---

### T10 — Tests
`tests/test_pipeline.py` per §11.

**Verify:** `pytest -q` passes.
**Commit:** `test(pipeline): cover stage ordering, error reporting and viewer output`

---

### T11 — Integration (one commit per real module swapped in)
As each member merges, delete their stub from `src/stubs.py`, wire the real stage into `STAGES`, and run the full command on all sheets.

**Verify after each swap:** `python sams.py <sheet> data/info.xml` still reaches the summary table.
**Commit pattern:** `refactor(pipeline): replace <stage> stub with real implementation`

---

### T12 — Freeze and package
Fill `README.md`: what it is, install, the three commands, folder map, known limits. Pin versions in `requirements.txt` from `pip freeze`. Produce the three figures in §13 with `tools/make_m1_figures.py`. Confirm `grep -r "STUB" src/` returns nothing. Tag.

**The `v1.0` tag is the group's, not M1's.** `src/stubs.py` cannot be empty until T11 has swapped in all seven real modules, so the STUB check cannot pass while M1 is the only work on `main`. M1 finishing tags `v0.1-m1-core` — everything M1 owns is done, the three commands run, the stubs are still standing in. `v1.0` waits for the last swap.

**Verify:** a clean clone into a fresh venv runs all three commands.
**Commits:**
- `docs(readme): add setup, usage and folder guide`
- `chore(release): pin dependency versions`
- `chore(release): tag v1.0 prototype submission`

---

## 10. Error handling rules

- User mistakes (missing file, bad index, empty database) → friendly one-line message, `sys.exit(2)`, **no traceback**.
- Programming errors → full traceback, wrapped so the stage name is visible.
- Never use a bare `except:`. Never `except Exception: pass`.
- Warnings that do not stop the run (for example, row count ≠ student count) go through the logger at `WARNING`, and appear in the final summary.

---

## 11. Tests M1 must write

`tests/test_pipeline.py`, with `matplotlib.use("Agg")` at the top:

1. Two fake stages append to a list — `Pipeline` runs them in the given order.
2. A stage that raises → error message contains that stage's `name`.
3. `ProgressViewer.save_all()` into `tmp_path` writes exactly N files, numbered from 01.
4. `ProgressViewer.add()` accepts both a 3-channel and a 1-channel image.
5. `sams.py` with a missing image exits with code 2 (use `subprocess`).
6. `Student("007", "x").index == "007"` — leading zero survives.

---

## 12. Commit protocol

- Branch: `feat/m1-core`. Merge into `main` via PR with a **merge commit or rebase — never squash**.
- Message format: `type(scope): short lowercase summary`, types `feat | fix | refactor | test | docs | chore`.
- One logical change per commit. Minimum 20 commits for M1 across the tasks above.
- Author identity must be your own:
  ```fish
  git config user.name "T.R.D.T. Dulshan"
  git config user.email "<your NSBM address>"
  ```
- Never force-push. Never rewrite shared history. `git log --author` is the evidence of individual contribution, which is 15% of the marks.

---

## 13. Definition of done for M1

- [ ] §4 input facts table filled in from real measurements
- [ ] `python -c "import src"` works from a clean clone
- [ ] All three commands run, with `--help`, and fail gracefully on bad input
- [ ] `sams.py` produces the summary table and saves numbered step images
- [ ] Montage window displays every processing step
- [ ] All stubs deleted; `grep -r "STUB" src/` returns nothing
- [ ] `pytest -q` passes
- [ ] `README.md` complete, dependencies pinned, release tagged
- [ ] `outputs/figures/m1_architecture.png`, `m1_montage_<date>.png`, `m1_timing.png` produced
- [ ] 20+ commits with clear messages
- [ ] `docs/contrib_m1.md` drafted

---

## 14. Open questions

1. Group size is 9, brief asks for 10 — confirm with Dr. Ranaweera. **Open.**
2. ~~Real `info.xml` tag structure~~ — **resolved in T0.** The file was never supplied. It is reconstructed as `nsbm/students/batches/batch/student` with `index`, `title`, `name`. If the real file later appears, re-run T0 and update §4 rather than patching the parser.
3. ~~Whether sheet row order matches XML student order~~ — **resolved in T0.** They match, because the XML was transcribed from the sheets in row order. Positional mapping is therefore safe for the prototype; M7 should still warn when the row count and the student count disagree (§10).
4. ~~Whether any sheet is greyscale~~ — **resolved in T0.** All five are 3 channel colour with real colour content. M6 keeps saturation as the primary path.
5. **New, open:** the two sheets where a signature spills into the neighbouring row (§4 deviation 6) may need M5 to pad cells vertically and M6 to attribute a stroke to the row that holds most of it. M5 and M6 to agree an approach.
6. **New, open:** `ab` written in a signature cell (§4 deviation 7) is ink that means absent. Decide with M7 whether the decision stage handles it by stroke shape or whether it is documented as a known limitation.
