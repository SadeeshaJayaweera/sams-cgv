# SAMS — Student Attendance Management System

CS402.3 Computer Graphics and Visualization, NSBM Green University.

Reads a phone photo of a paper signing sheet, works out who signed and who did
not, stores the result in a local SQLite database and visualises it.

```bash
python sams.py data/sheets/12.07.2019.png data/info.xml
python infovis.py 10000409
python investigate.py 10000409
```

Full setup, usage and folder guide land in task T12. See `BUILD_SPEC.md` for the
contracts every module builds against.
