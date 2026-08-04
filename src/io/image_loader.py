"""Image loading utilities."""

from __future__ import annotations

import cv2
import numpy as np
from pathlib import Path


def load_image(path: str | Path) -> np.ndarray:
    """BGR uint8, EXIF rotation applied. FileNotFoundError if missing,
    ValueError if not a decodable image. Both with clear messages.

    Args:
        path: Path to the image file to load.

    Returns:
        The loaded image as a NumPy array.

    Raises:
        FileNotFoundError: If the image file does not exist.
        ValueError: If the file exists but cannot be decoded by OpenCV.
    """
    resolved_path = Path(path)

    if not resolved_path.is_file():
        raise FileNotFoundError(f"Image file not found: {resolved_path}")

    image = cv2.imread(str(resolved_path), cv2.IMREAD_COLOR)

    if image is None:
        raise ValueError(f"File exists but is not a decodable image: {resolved_path}")

    return image
