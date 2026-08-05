# M2 — Acquisition & Geometry

Individual contribution notes. Two pages minimum, per the coursework brief: what you built, the techniques you used and why, the problems you hit, and the figures in `outputs/` that back it up.

## What I built

I implemented the initial acquisition and geometry correction pipeline (`GeometryStage` in `src/preprocess/deskew.py` and loaders in `src/io/image_loader.py`). The purpose of this stage is to standardize the raw photos taken by users before any downstream table extraction or signature analysis takes place. Phone photos often suffer from perspective distortion—because the camera is rarely held perfectly parallel to the paper—meaning rectangular pages appear as arbitrary quadrilaterals. By applying a four-point perspective transform (or a robust fallback rotation), we algorithmically pull the paper back into a flat, top-down rectangular view.

Crucially, my implementation ensures we preserve the full context of the document. The final cropped and deskewed image intentionally retains BOTH the lecture header table and the main student table, along with all 5 columns (including the right-hand `Signature` column). Rather than tightly cropping the student table right away, I leave that structural semantic decision to the M5 (Table Detection) stage. M2’s responsibility is purely geometric normalization, not structural parsing.

## Techniques and libraries

I utilized **OpenCV (`cv2`)** and **NumPy** for all core operations, alongside standard Python libraries. 

- **Perspective Warp and Homographies:** The primary deskew mechanism attempts to map the four corners of the detected page onto a perfect rectangle. Mathematically, this is done using a homography—a transformation matrix that maps points in one plane to another. `cv2.getPerspectiveTransform` calculates this $3 \times 3$ matrix based on our 4 source corners and 4 destination corners, and `cv2.warpPerspective` applies the matrix to every pixel, stretching and squeezing the image so the paper lies flat.
  
- **Edge Detection with Blurring:** To locate the paper, I applied a `cv2.Canny` edge detector. However, raw images contain high-frequency noise (like paper texture or camera grain) which creates false edges. Therefore, I first apply a Gaussian blur (`cv2.GaussianBlur`) to smooth out the noise, ensuring Canny only fires on the strong, structural boundaries of the page.

- **Skew Angle Clamping:** In our rotation fallback path (for when perspective warp fails), the Hough lines algorithm estimates a global skew angle. Instead of blindly trusting this angle, I aggressively clamp it using `MAX_SKEW_CORRECTION_DEG`. This safeguard prevents catastrophic misrotations (e.g., turning the page 90 degrees sideways because it latched onto a vertical line) in cases of extreme noise.

## Problems and how I solved them

The most significant hurdle was the physical acquisition environment of this dataset. The paper is photographed on a pale cream desk in every shot. This creates a severe low-contrast boundary between the edge of the paper and the background surface. In practice, the Canny edge detector—paired with the largest-contour heuristic—consistently fails to reliably isolate the true sheet perimeter because the edge gradients are simply too weak. 

This meant the primary four-point perspective warp failed to trigger on our real-world dataset. I solved this by treating the rotation fallback path not as an optional garnish, but as a critical, robust primary pathway. By leveraging `cv2.HoughLinesP` to find strong text/table lines and taking the median near-horizontal angle, the pipeline reliably rotates the image upright and preserves all necessary data for downstream tasks, even when the paper's literal edges are camouflaged.

## Evidence

The success and resilience of this geometry stage are demonstrated by our test coverage and visual output. As shown in the generated figures, the fallback accurately uprights the page:
- `outputs/figures/m2_original_vs_warped.png`: Shows a side-by-side comparison of the raw angled input against the corrected, upright warped output.
- `outputs/figures/m2_corner_detection.png`: Shows the internal Canny edge map layer and highlights why contour-finding struggles with the low-contrast desk edges.

### Per-Sheet Geometry Results

| Sheet Date | Geometry Path Used | Quality Note |
|---|---|---|
| 31.05.2019 | Fallback rotation | Straight; both tables and 5 columns intact |
| 21.06.2019 | Fallback rotation | Straight; both tables and 5 columns intact |
| 28.06.2019 | Fallback rotation | Straight; both tables and 5 columns intact |
| 05.07.2019 | Fallback rotation | Straight; both tables and 5 columns intact |
| 12.07.2019 | Fallback rotation | Straight; both tables and 5 columns intact |

*Note: The primary perspective warp (Canny + contour detection) fails on all sheets due to the low contrast between the cream paper and pale desk. The pipeline reliably falls back to Hough-lines rotation which produces an upright image with all required tables and columns intact.*
