"""Geometry and perspective correction stage."""

from __future__ import annotations

import cv2
import numpy as np

from src.config import CANNY_LOW, CANNY_HIGH


def _order_points(pts: np.ndarray) -> np.ndarray:
    """Order 4 arbitrary points into top-left, top-right, bottom-right, bottom-left."""
    rect = np.zeros((4, 2), dtype=np.float32)
    
    # top-left = smallest sum (x+y)
    # bottom-right = largest sum (x+y)
    s = pts.sum(axis=1)
    rect[0] = pts[np.argmin(s)]
    rect[2] = pts[np.argmax(s)]
    
    # diff computes (y-x) when axis=1 on an array of (x,y)
    # top-right = smallest difference (y-x)
    # bottom-left = largest difference (y-x)
    diff = np.diff(pts, axis=1)
    rect[1] = pts[np.argmin(diff)]
    rect[3] = pts[np.argmax(diff)]
    
    return rect


def find_sheet_corners(bgr: np.ndarray) -> np.ndarray | None:
    """(4, 2) float32, ordered top-left, top-right, bottom-right, bottom-left.
    None when not found — that is a normal outcome, not an error."""
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    edges = cv2.Canny(blurred, CANNY_LOW, CANNY_HIGH)
    
    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return None
        
    largest_contour = max(contours, key=cv2.contourArea)
    perimeter = cv2.arcLength(largest_contour, True)
    
    # Tolerance loop starting near 0.02 * perimeter to find exactly 4 points
    for factor in np.linspace(0.01, 0.1, 100):
        epsilon = factor * perimeter
        approx = cv2.approxPolyDP(largest_contour, epsilon, True)
        
        if len(approx) == 4:
            pts = approx.reshape((4, 2)).astype(np.float32)
            return _order_points(pts)
            
    return None
