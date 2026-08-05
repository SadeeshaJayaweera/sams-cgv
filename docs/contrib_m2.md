# M2 — Acquisition & Geometry

Individual contribution notes. Two pages minimum, per the coursework brief:
what you built, the techniques you used and why, the problems you hit, and
the figures in `outputs/` that back it up.

## What I built

_TBD_

## Techniques and libraries

_TBD_

## Problems and how I solved them

_TBD_

## Evidence

### Per-Sheet Geometry Results

| Sheet Date | Geometry Path Used | Quality Note |
|---|---|---|
| 31.05.2019 | Fallback rotation | Straight; both tables and 5 columns intact |
| 21.06.2019 | Fallback rotation | Straight; both tables and 5 columns intact |
| 28.06.2019 | Fallback rotation | Straight; both tables and 5 columns intact |
| 05.07.2019 | Fallback rotation | Straight; both tables and 5 columns intact |
| 12.07.2019 | Fallback rotation | Straight; both tables and 5 columns intact |

*Note: The primary perspective warp (Canny + contour detection) fails on all sheets due to the low contrast between the cream paper and pale desk. The pipeline reliably falls back to Hough-lines rotation which produces an upright image with all required tables and columns intact.*
