"""Tiny multimodal classifier — first real trainable model for Phase 4 unblock.

Architecture:
    - Image encoder: 3-layer CNN on 128x128 RGB input -> 64-dim feature
    - Text encoder: character-level embedding + mean pool -> 64-dim feature
    - Fusion: concatenation -> 128-dim
    - Head: linear -> answer classes

Design choices for Core ML export friendliness:
    - Fixed input sizes (128x128 image, 128-char text)
    - Only conv2d, relu, linear, embedding — all have clean Core ML mappings
    - No attention, no variable-length sequences, no exotic ops
    - Small parameter count (~50K) — well under 100MB target
    - Deterministic inference path
"""

from __future__ import annotations

import json
from collections import Counter
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import torch
import torch.nn as nn
from torch import Tensor

from axiom.data.images import IMAGE_SIZE, ImageLoader
from axiom.eval import normalize_text

from .base import ReasoningModel

# Text encoding constants
MAX_CHAR_LEN = 128
VOCAB_SIZE = 128  # ASCII range — sufficient for English questions
CHAR_EMBED_DIM = 32
TEXT_FEATURE_DIM = 64

# Image encoding constants
IMAGE_FEATURE_DIM = 64

# Fusion
FUSION_DIM = IMAGE_FEATURE_DIM + TEXT_FEATURE_DIM  # 128


class ImageEncoder(nn.Module):
    """3-layer CNN reducing 128x128x3 -> 64-dim vector."""

    def __init__(self) -> None:
        super().__init__()
        self.features = nn.Sequential(
            nn.Conv2d(3, 16, kernel_size=5, stride=2, padding=2),   # -> 16x64x64
            nn.ReLU(),
            nn.Conv2d(16, 32, kernel_size=3, stride=2, padding=1),  # -> 32x32x32
            nn.ReLU(),
            nn.Conv2d(32, 64, kernel_size=3, stride=2, padding=1),  # -> 64x16x16
            nn.ReLU(),
            nn.AdaptiveAvgPool2d(1),                                 # -> 64x1x1
        )

    def forward(self, x: Tensor) -> Tensor:
        # x: (B, 3, 128, 128)
        return self.features(x).squeeze(-1).squeeze(-1)  # (B, 64)


class TextEncoder(nn.Module):
    """Character-level embedding + mean pool -> 64-dim vector."""

    def __init__(self) -> None:
        super().__init__()
        self.embedding = nn.Embedding(VOCAB_SIZE, CHAR_EMBED_DIM, padding_idx=0)
        self.proj = nn.Linear(CHAR_EMBED_DIM, TEXT_FEATURE_DIM)

    def forward(self, char_ids: Tensor) -> Tensor:
        # char_ids: (B, MAX_CHAR_LEN) — long tensor of ASCII codes
        embedded = self.embedding(char_ids)        # (B, L, CHAR_EMBED_DIM)
        mask = (char_ids != 0).unsqueeze(-1).float()  # (B, L, 1)
        # Mean pool over non-padding positions
        lengths = mask.sum(dim=1).clamp(min=1)     # (B, 1)
        pooled = (embedded * mask).sum(dim=1) / lengths  # (B, CHAR_EMBED_DIM)
        return self.proj(pooled)                   # (B, TEXT_FEATURE_DIM)


class TinyMultimodalNet(nn.Module):
    """Complete tiny multimodal classifier."""

    def __init__(self, num_classes: int) -> None:
        super().__init__()
        self.image_encoder = ImageEncoder()
        self.text_encoder = TextEncoder()
        self.classifier = nn.Sequential(
            nn.Linear(FUSION_DIM, 64),
            nn.ReLU(),
            nn.Linear(64, num_classes),
        )

    def forward(self, images: Tensor, char_ids: Tensor) -> Tensor:
        img_feat = self.image_encoder(images)     # (B, 64)
        txt_feat = self.text_encoder(char_ids)    # (B, 64)
        fused = torch.cat([img_feat, txt_feat], dim=1)  # (B, 128)
        return self.classifier(fused)             # (B, num_classes)


def encode_question(question: str) -> list[int]:
    """Encode a question string to fixed-length ASCII character IDs."""
    chars = question[:MAX_CHAR_LEN]
    ids = [min(ord(c), VOCAB_SIZE - 1) for c in chars]
    # Pad to fixed length
    ids += [0] * (MAX_CHAR_LEN - len(ids))
    return ids


class TinyMultimodalBaseline(ReasoningModel):
    """Trainable multimodal baseline using TinyMultimodalNet.

    This is the first real trainable model in the repo. It uses both
    image and text inputs and produces a real PyTorch checkpoint.

    It is intentionally small and simple — designed to unblock Phase 4
    (Core ML conversion), not to be the final research model.
    """

    def __init__(self, spec, *, image_root: str | Path | None = None) -> None:
        super().__init__(spec)
        self._image_loader: ImageLoader | None = None
        self._net: TinyMultimodalNet | None = None
        self._label_to_idx: dict[str, int] = {}
        self._idx_to_label: dict[int, str] = {}
        self._is_trained = False
        self._image_root = image_root

    def _ensure_image_loader(self) -> ImageLoader:
        if self._image_loader is None:
            if self._image_root is None:
                raise ValueError(
                    "TinyMultimodalBaseline requires an image root. "
                    "Pass image_root= or set AXIOM_SCREENSHOT_ROOT."
                )
            self._image_loader = ImageLoader(self._image_root)
        return self._image_loader

    def _build_vocab(self, rows: Sequence[dict[str, Any]]) -> None:
        """Build answer label vocabulary from training data."""
        answer_counts: Counter[str] = Counter()
        for row in rows:
            answer = normalize_text(str(row["answer"]))
            answer_counts[answer] += 1

        # Deterministic ordering: frequency descending, then alphabetical
        sorted_answers = sorted(
            answer_counts.keys(),
            key=lambda a: (-answer_counts[a], a),
        )
        self._label_to_idx = {a: i for i, a in enumerate(sorted_answers)}
        self._idx_to_label = {i: a for a, i in self._label_to_idx.items()}

    def _prepare_batch(
        self, rows: Sequence[dict[str, Any]]
    ) -> tuple[Tensor, Tensor, Tensor]:
        """Prepare a batch of (images, char_ids, labels) from manifest rows."""
        loader = self._ensure_image_loader()

        images: list[Tensor] = []
        char_ids: list[list[int]] = []
        labels: list[int] = []

        for row in rows:
            img = loader.load_and_preprocess(row["image_filename"])
            images.append(img)
            char_ids.append(encode_question(row["question"]))
            answer = normalize_text(str(row["answer"]))
            labels.append(self._label_to_idx.get(answer, 0))

        return (
            torch.stack(images),
            torch.tensor(char_ids, dtype=torch.long),
            torch.tensor(labels, dtype=torch.long),
        )

    def train(
        self,
        train_rows: Sequence[dict[str, Any]],
        *,
        val_rows: Sequence[dict[str, Any]] | None = None,
        seed: int = 0,
    ) -> dict[str, Any]:
        """Train the tiny multimodal model on labeled screenshot-QA data."""
        torch.manual_seed(seed)

        # Build label vocabulary from training data
        self._build_vocab(train_rows)
        num_classes = len(self._label_to_idx)

        if num_classes < 2:
            raise ValueError(
                f"Need at least 2 distinct answers for classification, got {num_classes}."
            )

        # Initialize network
        self._net = TinyMultimodalNet(num_classes)

        # Prepare training data
        images, char_ids, labels = self._prepare_batch(train_rows)

        # Simple training loop — SGD, cross-entropy, fixed epochs
        optimizer = torch.optim.SGD(self._net.parameters(), lr=0.01, momentum=0.9)
        criterion = nn.CrossEntropyLoss()

        num_epochs = 20
        batch_size = min(16, len(train_rows))
        n = len(train_rows)

        self._net.train()
        epoch_losses: list[float] = []

        for epoch in range(num_epochs):
            # Deterministic shuffle
            gen = torch.Generator().manual_seed(seed + epoch)
            perm = torch.randperm(n, generator=gen)

            epoch_loss = 0.0
            num_batches = 0

            for start in range(0, n, batch_size):
                idx = perm[start : start + batch_size]
                batch_img = images[idx]
                batch_txt = char_ids[idx]
                batch_lbl = labels[idx]

                optimizer.zero_grad()
                logits = self._net(batch_img, batch_txt)
                loss = criterion(logits, batch_lbl)
                loss.backward()
                optimizer.step()

                epoch_loss += loss.item()
                num_batches += 1

            avg_loss = epoch_loss / max(num_batches, 1)
            epoch_losses.append(round(avg_loss, 4))

        self._net.eval()
        self._is_trained = True

        # Compute training accuracy
        with torch.no_grad():
            train_logits = self._net(images, char_ids)
            train_preds = train_logits.argmax(dim=1)
            train_acc = (train_preds == labels).float().mean().item()

        param_count = sum(p.numel() for p in self._net.parameters())

        return {
            "train_examples": len(train_rows),
            "num_classes": num_classes,
            "num_epochs": num_epochs,
            "batch_size": batch_size,
            "learning_rate": 0.01,
            "final_loss": epoch_losses[-1] if epoch_losses else 0.0,
            "train_accuracy": round(train_acc, 4),
            "parameter_count": param_count,
            "image_size": IMAGE_SIZE,
            "max_char_len": MAX_CHAR_LEN,
            "epoch_losses": epoch_losses,
        }

    def predict_one(self, row: dict[str, Any]) -> str:
        if not self._is_trained or self._net is None:
            raise RuntimeError("TinyMultimodalBaseline.predict_one() called before train().")

        loader = self._ensure_image_loader()
        img = loader.load_and_preprocess(row["image_filename"]).unsqueeze(0)
        char_id = torch.tensor([encode_question(row["question"])], dtype=torch.long)

        with torch.no_grad():
            logits = self._net(img, char_id)
            pred_idx = logits.argmax(dim=1).item()

        return self._idx_to_label.get(pred_idx, "")

    def save_checkpoint(self, output_dir: str | Path) -> dict[str, str]:
        """Save model checkpoint, label vocab, and architecture metadata."""
        if not self._is_trained or self._net is None:
            raise RuntimeError("Cannot save checkpoint before training.")

        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        # Save model weights
        weights_path = output_path / "model.pt"
        torch.save(self._net.state_dict(), weights_path)

        # Save label vocabulary
        vocab_path = output_path / "label_vocab.json"
        vocab_path.write_text(
            json.dumps(self._label_to_idx, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

        # Save architecture metadata (needed for reconstruction before export)
        meta = {
            "model_id": self.spec.model_id,
            "num_classes": len(self._label_to_idx),
            "image_size": IMAGE_SIZE,
            "max_char_len": MAX_CHAR_LEN,
            "vocab_size": VOCAB_SIZE,
            "char_embed_dim": CHAR_EMBED_DIM,
            "text_feature_dim": TEXT_FEATURE_DIM,
            "image_feature_dim": IMAGE_FEATURE_DIM,
            "parameter_count": sum(p.numel() for p in self._net.parameters()),
        }
        meta_path = output_path / "architecture.json"
        meta_path.write_text(
            json.dumps(meta, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

        return {
            "weights": str(weights_path),
            "label_vocab": str(vocab_path),
            "architecture": str(meta_path),
        }

    def export_coreml(self, output_dir: str | Path) -> dict[str, Any]:
        """Export the trained model to Core ML (.mlpackage) format.

        Uses torch.jit.trace → coremltools.convert pipeline.
        Returns a dict of artifact paths and conversion metadata.
        """
        if not self._is_trained or self._net is None:
            raise RuntimeError("Cannot export before training.")

        import coremltools as ct

        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        # Create example inputs for tracing
        example_image = torch.randn(1, 3, IMAGE_SIZE, IMAGE_SIZE)
        example_text = torch.randint(0, VOCAB_SIZE, (1, MAX_CHAR_LEN))

        # Trace the model
        self._net.eval()
        with torch.no_grad():
            traced = torch.jit.trace(self._net, (example_image, example_text))

        # Convert to Core ML
        mlmodel = ct.convert(
            traced,
            inputs=[
                ct.ImageType(
                    name="image",
                    shape=(1, 3, IMAGE_SIZE, IMAGE_SIZE),
                    scale=1.0 / 255.0,
                    color_layout=ct.colorlayout.RGB,
                ),
                ct.TensorType(
                    name="char_ids",
                    shape=(1, MAX_CHAR_LEN),
                    dtype=int,
                ),
            ],
            outputs=[ct.TensorType(name="logits")],
            minimum_deployment_target=ct.target.iOS16,
        )

        # Save .mlpackage
        mlpackage_path = output_path / "TinyMultimodal.mlpackage"
        mlmodel.save(str(mlpackage_path))

        # Also save the traced TorchScript for reproducibility
        traced_path = output_path / "traced_model.pt"
        traced.save(str(traced_path))

        # Save label vocab alongside the mlpackage for app-side decoding
        vocab_path = output_path / "label_vocab.json"
        vocab_path.write_text(
            json.dumps(self._label_to_idx, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

        return {
            "mlpackage": str(mlpackage_path),
            "traced_model": str(traced_path),
            "label_vocab": str(vocab_path),
            "num_classes": len(self._label_to_idx),
            "image_size": IMAGE_SIZE,
            "max_char_len": MAX_CHAR_LEN,
        }

    @classmethod
    def load_checkpoint(
        cls,
        checkpoint_dir: str | Path,
        spec,
        *,
        image_root: str | Path | None = None,
    ) -> "TinyMultimodalBaseline":
        """Reconstruct a trained model from a saved checkpoint."""
        checkpoint_path = Path(checkpoint_dir)

        # Load architecture metadata
        meta = json.loads(
            (checkpoint_path / "architecture.json").read_text(encoding="utf-8")
        )
        # Load label vocab
        label_to_idx = json.loads(
            (checkpoint_path / "label_vocab.json").read_text(encoding="utf-8")
        )

        model = cls(spec, image_root=image_root)
        model._label_to_idx = label_to_idx
        model._idx_to_label = {int(i): a for a, i in label_to_idx.items()}
        model._net = TinyMultimodalNet(num_classes=meta["num_classes"])
        model._net.load_state_dict(
            torch.load(checkpoint_path / "model.pt", weights_only=True)
        )
        model._net.eval()
        model._is_trained = True

        return model
