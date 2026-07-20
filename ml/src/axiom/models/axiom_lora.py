"""AXIOM-LoRA — pretrained-backbone model with a real LoRA adapter (Phase 8).

Architecture:
    - Image encoder: pretrained MobileNetV3-Small (ImageNet weights) backbone,
      entirely frozen, with a LoRA low-rank adapter on the final 1x1 conv
      (96 -> 576 channels) -> pooled -> linear projection to a feature vector.
    - Text encoder: the same character-level embedding + linear projection
      used by tiny_multimodal_v0/v1 — unchanged.
    - Fusion: concatenation -> classifier head (unchanged pattern).

Why this design (see docs/MODEL_SELECTION.md for the full writeup):
    - tiny_multimodal_v0/v1 train a ~40-50K-param CNN from scratch on <1K
      examples with no pretrained weights. This model replaces the image
      tower with a real pretrained backbone (2.5M params, ImageNet-trained)
      to give it actual visual priors to build on.
    - The original plan was a pretrained *text* tower fine-tuned via LoRA
      (matching the README's original "LoRA (PEFT)" promise). That path was
      attempted first and is NOT used here: tracing a LoRA-adapted
      HuggingFace transformer (bert-tiny, then all-MiniLM-L6-v2) through
      coremltools 9.0 failed at the embeddings/position-id conversion step
      with `TypeError: only 0-dimensional arrays can be converted to Python
      scalars`, reproduced with LoRA removed too (i.e. the failure is in the
      base pretrained transformer's traced graph, not LoRA-specific) --
      likely a version mismatch between a very new `transformers` release's
      internal masking/position-id codegen and what coremltools' PyTorch
      frontend can lower. Falling back to the char-level text encoder was a
      pre-registered decision in the roadmap for exactly this situation, not
      an afterthought.
    - LoRA is instead applied honestly to the one component that's actually
      pretrained: the vision backbone's final conv layer. The rest of the
      backbone stays frozen and untouched.

Design choices for Core ML export friendliness (same discipline as v0/v1):
    - Fixed input sizes (reuses IMAGE_SIZE=128, MAX_CHAR_LEN=128 from the
      existing pipeline -- no changes needed on the app/CoreML preprocessing
      side)
    - Only conv2d, batchnorm (frozen, eval-mode), relu/hardswish, linear,
      embedding, adaptive avg pool -- every op already proven to convert
      cleanly via the spikes in this phase and the v0/v1 export history
    - No attention, no variable-length sequences
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import torch
import torch.nn as nn
from torch import Tensor

from axiom.data.images import IMAGE_SIZE

from .tiny_multimodal import (
    MAX_CHAR_LEN,
    TEXT_FEATURE_DIM,
    VOCAB_SIZE,
    TextEncoder,
    TinyMultimodalBaseline,
)

# ImageNet normalization stats -- applied inside the model (not in
# ImageLoader) so the app-side / CoreML preprocessing contract (raw
# [0, 1] RGB) stays identical to v0/v1 and nothing outside ml/ needs to
# change for this phase.
_IMAGENET_MEAN = (0.485, 0.456, 0.406)
_IMAGENET_STD = (0.229, 0.224, 0.225)

# Pretrained MobileNetV3-Small backbone output channels (features[-1]),
# verified directly against torchvision, not assumed.
_BACKBONE_OUT_CHANNELS = 576
_BACKBONE_LORA_IN_CHANNELS = 96  # input channels into features[-1]'s conv

IMAGE_FEATURE_DIM = 96
FUSION_DIM = IMAGE_FEATURE_DIM + TEXT_FEATURE_DIM

LORA_RANK = 8
LORA_ALPHA = 16.0


class LoRAConv1x1(nn.Module):
    """Frozen pretrained 1x1 conv + a trainable low-rank adapter (LoRA for Conv2d).

    output = base_conv(x) + scale * up(down(x))

    `down` uses standard Kaiming init, `up` is zero-initialized -- the usual
    LoRA convention so the adapter starts as a true no-op (output identical
    to the frozen pretrained conv) and only diverges as training proceeds.
    """

    def __init__(self, base_conv: nn.Conv2d, rank: int = LORA_RANK, alpha: float = LORA_ALPHA) -> None:
        super().__init__()
        self.base_conv = base_conv
        for p in self.base_conv.parameters():
            p.requires_grad_(False)

        in_ch = base_conv.in_channels
        out_ch = base_conv.out_channels
        self.lora_down = nn.Conv2d(in_ch, rank, kernel_size=1, bias=False)
        self.lora_up = nn.Conv2d(rank, out_ch, kernel_size=1, bias=False)
        nn.init.kaiming_uniform_(self.lora_down.weight, a=5**0.5)
        nn.init.zeros_(self.lora_up.weight)
        self.scale = alpha / rank

    def forward(self, x: Tensor) -> Tensor:
        return self.base_conv(x) + self.lora_up(self.lora_down(x)) * self.scale


class PretrainedImageEncoder(nn.Module):
    """MobileNetV3-Small (ImageNet-pretrained), frozen, with a LoRA adapter
    on the final conv, projected down to IMAGE_FEATURE_DIM."""

    def __init__(self) -> None:
        super().__init__()
        import torchvision

        backbone = torchvision.models.mobilenet_v3_small(
            weights=torchvision.models.MobileNet_V3_Small_Weights.IMAGENET1K_V1
        )
        self.features = backbone.features
        for p in self.features.parameters():
            p.requires_grad_(False)

        final_block = self.features[-1]  # Conv2dNormActivation(Conv2d, BN, Hardswish)
        assert final_block[0].in_channels == _BACKBONE_LORA_IN_CHANNELS
        assert final_block[0].out_channels == _BACKBONE_OUT_CHANNELS
        final_block[0] = LoRAConv1x1(final_block[0])

        self.pool = nn.AdaptiveAvgPool2d(1)
        self.proj = nn.Linear(_BACKBONE_OUT_CHANNELS, IMAGE_FEATURE_DIM)

        mean = torch.tensor(_IMAGENET_MEAN).view(1, 3, 1, 1)
        std = torch.tensor(_IMAGENET_STD).view(1, 3, 1, 1)
        self.register_buffer("_norm_mean", mean)
        self.register_buffer("_norm_std", std)

    def train(self, mode: bool = True) -> "PretrainedImageEncoder":
        super().train(mode)
        # Keep the frozen backbone (including the BatchNorm inside the
        # LoRA-adapted final block) in eval mode always, so BatchNorm
        # running stats stay at their ImageNet-pretrained values instead
        # of drifting from tiny (~16-example) fine-tuning batches. Only
        # the LoRA adapter convs and the new projection head should behave
        # differently between train/eval, and neither has train-mode-
        # sensitive layers (no dropout/BN of their own), so freezing the
        # whole `features` submodule in eval mode is safe and correct.
        self.features.eval()
        return self

    def forward(self, x: Tensor) -> Tensor:
        # x: (B, 3, IMAGE_SIZE, IMAGE_SIZE), values in [0, 1]
        x = (x - self._norm_mean) / self._norm_std
        feat = self.features(x)              # (B, 576, H, W)
        pooled = self.pool(feat).flatten(1)   # (B, 576)
        return self.proj(pooled)              # (B, IMAGE_FEATURE_DIM)


class AxiomLoraNet(nn.Module):
    """Pretrained-backbone + LoRA image encoder, char-level text encoder,
    concatenation fusion, classification head -- same overall shape as
    TinyMultimodalNet so the rest of the pipeline (training loop, export,
    app integration contract) stays consistent."""

    def __init__(self, num_classes: int) -> None:
        super().__init__()
        self.image_encoder = PretrainedImageEncoder()
        self.text_encoder = TextEncoder()
        self.classifier = nn.Sequential(
            nn.Linear(FUSION_DIM, 64),
            nn.ReLU(),
            nn.Linear(64, num_classes),
        )

    def forward(self, images: Tensor, char_ids: Tensor) -> Tensor:
        img_feat = self.image_encoder(images)
        txt_feat = self.text_encoder(char_ids)
        fused = torch.cat([img_feat, txt_feat], dim=1)
        return self.classifier(fused)


class AxiomLoraBaseline(TinyMultimodalBaseline):
    """Trainable baseline using AxiomLoraNet.

    Subclasses TinyMultimodalBaseline to reuse its training loop, answer
    vocabulary building, batch preparation, checkpointing, and predict_one()
    unchanged -- only the network architecture (_build_net) and the Core ML
    export filename/metadata differ.
    """

    def _build_net(self, num_classes: int) -> nn.Module:
        return AxiomLoraNet(num_classes)

    def save_checkpoint(self, output_dir: str | Path) -> dict[str, str]:
        paths = super().save_checkpoint(output_dir)

        # Overwrite architecture.json with LoRA-specific provenance fields
        # in addition to the base fields (keeps the same file, same
        # consumers -- export_coreml.py only reads num_classes from it).
        meta_path = Path(paths["architecture"])
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        meta.update({
            "backbone": "mobilenet_v3_small (torchvision, ImageNet-pretrained)",
            "backbone_frozen": True,
            "lora_adapter": "final 1x1 conv (96->576 channels)",
            "lora_rank": LORA_RANK,
            "lora_alpha": LORA_ALPHA,
            "image_feature_dim": IMAGE_FEATURE_DIM,
            "text_tower": "char-level embedding + linear (unchanged from tiny_multimodal_v0/v1; pretrained-transformer+LoRA attempted and blocked on CoreML export, see module docstring)",
        })
        meta_path.write_text(json.dumps(meta, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return paths

    def export_coreml(self, output_dir: str | Path) -> dict[str, Any]:
        """Export the trained model to Core ML (.mlpackage) format."""
        if not self._is_trained or self._net is None:
            raise RuntimeError("Cannot export before training.")

        import coremltools as ct

        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        example_image = torch.rand(1, 3, IMAGE_SIZE, IMAGE_SIZE)
        example_text = torch.randint(0, VOCAB_SIZE, (1, MAX_CHAR_LEN))

        self._net.eval()
        with torch.no_grad():
            traced = torch.jit.trace(self._net, (example_image, example_text))

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

        mlpackage_path = output_path / "AxiomLora.mlpackage"
        mlmodel.save(str(mlpackage_path))

        traced_path = output_path / "traced_model.pt"
        traced.save(str(traced_path))

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
