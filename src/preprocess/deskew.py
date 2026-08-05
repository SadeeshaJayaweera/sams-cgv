"""Geometry and perspective correction stage."""

from __future__ import annotations

import cv2
import numpy as np

from src.config import CANNY_LOW, CANNY_HIGH, MIN_SHEET_AREA_RATIO, MAX_SKEW_CORRECTION_DEG
from src.utils.stage import Stage


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


def estimate_skew_angle(grey: np.ndarray) -> float:
    """Small residual rotation in degrees, from Hough lines or minAreaRect."""
    edges = cv2.Canny(grey, CANNY_LOW, CANNY_HIGH)
    lines = cv2.HoughLinesP(edges, 1, np.pi / 180, 100, minLineLength=50, maxLineGap=10)
    
    if lines is None:
        return 0.0
        
    angles = []
    # OpenCV 4 returns (N, 1, 4) here and OpenCV 5 returns (N, 4). We pin
    # opencv-python 5, where indexing line[0] yields a single int and unpacking
    # it raises. Reshaping first works on both.
    for x1, y1, x2, y2 in lines.reshape(-1, 4):
        angle = np.degrees(np.arctan2(float(y2 - y1), float(x2 - x1)))
        
        # Normalize angle to [-90, 90] range
        if angle > 90:
            angle -= 180
        elif angle < -90:
            angle += 180
            
        # Filter for near-horizontal segments (+/- 30 degrees)
        if -30.0 <= angle <= 30.0:
            angles.append(angle)
            
    if not angles:
        return 0.0
        
    return float(np.median(angles))


class GeometryStage(Stage):
    """Initial fallback implementation of the geometry stage."""
    name = "geometry"

    def run(self, ctx: dict) -> dict:
        bgr = ctx.get("bgr")
        if bgr is None:
            return ctx
            
        corners = find_sheet_corners(bgr)
        
        if corners is not None:
            warped = four_point_warp(bgr, corners)
        else:
            # Fallback path: use full image and rotate by estimated skew angle
            gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
            angle = estimate_skew_angle(gray)
            
            # Clamp the result to +/- MAX_SKEW_CORRECTION_DEG
            angle = max(-MAX_SKEW_CORRECTION_DEG, min(MAX_SKEW_CORRECTION_DEG, angle))
            
            h, w = bgr.shape[:2]
            center = (w / 2, h / 2)
            
            # Get OpenCV rotation matrix
            M = cv2.getRotationMatrix2D(center, angle, 1.0)
            
            # Expand the canvas so nothing is cut off
            cos = np.abs(M[0, 0])
            sin = np.abs(M[0, 1])
            new_w = int((h * sin) + (w * cos))
            new_h = int((h * cos) + (w * sin))
            
            M[0, 2] += (new_w / 2) - center[0]
            M[1, 2] += (new_h / 2) - center[1]
            
            warped = cv2.warpAffine(bgr, M, (new_w, new_h))
            
        ctx["warped"] = warped
        return ctx
