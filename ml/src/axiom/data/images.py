"""Image loading and preprocessing for private screenshot datasets.

Screenshots live outside the git repo in a private shared folder.
This module resolves image_filename fields from manifests against
an explicit image root directory.

Usage:
    loader = ImageLoader(image_root="/path/to/screenshots_v1")
    img_tensor = loader.load_and_preprocess("img_001.png")
"""

from __future__ import annotations

import os
from pathlib import Path

try:
    from PIL import Image
    import torch
    from torch import Tensor
except ImportError as exc:
    raise ImportError(
        "Image loading requires Pillow and PyTorch. "
        "Install with: pip install -e 'ml[train]'"
    ) from exc


# Fixed input size — deliberately small for export-friendliness.
# 128x128 is sufficient for the current screenshot QA task and
# produces a model small enough for Core ML conversion.
IMAGE_SIZE = 128


def resolve_image_root(image_root: str | Path | None = None) -> Path:
    """Resolve the private screenshot directory.

    Priority:
    1. Explicit image_root argument
    2. AXIOM_SCREENSHOT_ROOT environment variable
    3. Error with a clear message
    """
    if image_root is not None:
        root = Path(image_root).resolve()
        if not root.is_dir():
            raise FileNotFoundError(
                f"Image root does not exist: {root}\n"
                f"Screenshots must be placed in a local directory. "
                f"See data/README.md for the private storage protocol."
            )
        return root

    env_root = os.environ.get("AXIOM_SCREENSHOT_ROOT")
    if env_root:
        root = Path(env_root).resolve()
        if not root.is_dir():
            raise FileNotFoundError(
                f"AXIOM_SCREENSHOT_ROOT={env_root} does not exist."
            )
        return root

    raise ValueError(
        "No image root specified. Provide --image-root or set "
        "AXIOM_SCREENSHOT_ROOT to the directory containing screenshots."
    )


class ImageLoader:
    """Loads and preprocesses screenshots from a private directory."""

    def __init__(self, image_root: str | Path) -> None:
        self.root = Path(image_root).resolve()
        if not self.root.is_dir():
            raise FileNotFoundError(f"Image root does not exist: {self.root}")

    def resolve_path(self, image_filename: str) -> Path:
        """Return the full path for an image filename, or raise."""
        path = self.root / image_filename
        if not path.exists():
            raise FileNotFoundError(
                f"Missing screenshot: {image_filename} "
                f"(expected at {path})"
            )
        return path

    def validate_manifest(self, rows: list[dict]) -> tuple[list[str], list[str]]:
        """Check which images from a manifest exist / are missing.

        Returns (found_filenames, missing_filenames).
        """
        found: list[str] = []
        missing: list[str] = []
        for row in rows:
            filename = row["image_filename"]
            if (self.root / filename).exists():
                found.append(filename)
            else:
                missing.append(filename)
        return found, missing

    def load_and_preprocess(self, image_filename: str) -> Tensor:
        """Load one screenshot, resize, and convert to a normalized tensor.

        Returns a float32 tensor of shape (3, IMAGE_SIZE, IMAGE_SIZE)
        with pixel values in [0, 1].

        Preprocessing is deliberately simple for export-friendliness:
        - Resize to IMAGE_SIZE x IMAGE_SIZE (bilinear)
        - Convert to RGB
        - Scale to [0, 1]
        - No augmentation (deterministic)
        """
        path = self.resolve_path(image_filename)
        img = Image.open(path).convert("RGB")
        img = img.resize((IMAGE_SIZE, IMAGE_SIZE), Image.BILINEAR)

        # Convert to tensor: HWC uint8 -> CHW float32 [0, 1]
        import numpy as np
        arr = np.array(img, dtype=np.float32) / 255.0
        tensor = torch.from_numpy(arr).permute(2, 0, 1)  # (3, H, W)
        return tensor

    def load_batch(self, image_filenames: list[str]) -> Tensor:
        """Load and stack multiple images into a batch tensor.

        Returns shape (N, 3, IMAGE_SIZE, IMAGE_SIZE).
        """
        tensors = [self.load_and_preprocess(f) for f in image_filenames]
        return torch.stack(tensors, dim=0)
