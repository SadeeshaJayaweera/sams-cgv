"""Geometry and perspective correction stage."""

from __future__ import annotations

import cv2
import numpy as np

from src.config import CANNY_LOW, CANNY_HIGH, MIN_SHEET_AREA_RATIO


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
        
    full_area = bgr.shape[0] * bgr.shape[1]
    
    # Sort contours by area descending so we try the largest ones first
    contours = sorted(contours, key=cv2.contourArea, reverse=True)
    
    for contour in contours:
        perimeter = cv2.arcLength(contour, True)
        
        # Tolerance loop starting near 0.02 * perimeter to find exactly 4 points
        for factor in np.linspace(0.01, 0.1, 100):
            epsilon = factor * perimeter
            approx = cv2.approxPolyDP(contour, epsilon, True)
            
            if len(approx) == 4:
                area = cv2.contourArea(approx)
                # If the area is >= MIN_SHEET_AREA_RATIO, we've found our sheet
                if (area / full_area) >= MIN_SHEET_AREA_RATIO:
                    pts = approx.reshape((4, 2)).astype(np.float32)
                    return _order_points(pts)
                
                # If this 4-point approximation is too small, stop trying epsilons
                # for this particular contour and move to the next largest contour candidate.
                break
                
    return None


def four_point_warp(bgr: np.ndarray, corners: np.ndarray) -> np.ndarray:
    """Perspective transform to a straight top-down view."""
    tl, tr, br, bl = corners

    # Calculate output width as max of top or bottom edge lengths
    width_top = np.linalg.norm(tr - tl)
    width_bottom = np.linalg.norm(br - bl)
    max_width = int(max(width_top, width_bottom))

    # Calculate output height as max of left or right edge lengths
    height_left = np.linalg.norm(bl - tl)
    height_right = np.linalg.norm(br - tr)
    max_height = int(max(height_left, height_right))

    # Construct the destination points to map to
    dst = np.array([
        [0, 0],
        [max_width - 1, 0],
        [max_width - 1, max_height - 1],
        [0, max_height - 1]
    ], dtype=np.float32)

    M = cv2.getPerspectiveTransform(corners, dst)
    return cv2.warpPerspective(bgr, M, (max_width, max_height))
