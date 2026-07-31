"""AXIOM-LoRA-Text -- pretrained TEXT-transformer + LoRA model (Phase 8 retry).

This is the approach the original project README specified most literally
("LoRA (PEFT) fine-tuning") and the one first attempted in Phase 8. It was
dropped there after `coremltools.convert` failed inside the embeddings
layer with `TypeError: only 0-dimensional arrays can be converted to
Python scalars`, reproduced identically with LoRA removed (so the break
was in the base transformer's traced graph, not LoRA-specific), and never
retried with a fix -- the project fell back to a pretrained *vision*
backbone (`axiom_lora.py`) instead.

Root cause, isolated by direct repro: BERT-family embeddings compute
`position_ids` dynamically at trace time via a length-dependent slice of
a registered buffer. coremltools 9.0's PyTorch frontend cannot lower the
resulting dynamic-int op regardless of `torch`/`transformers` version
(reproduced identically across three different pinned combinations,
including the combination coremltools itself recommends). The fix is
architectural, not a version pin: since every question in this project is
padded/truncated to the same fixed length, `position_ids` is passed to
the model explicitly as a static registered buffer instead of letting the
model derive it dynamically -- this is exact, not an approximation, given
the fixed-length input contract already used throughout this codebase.

Architecture:
    - Text encoder: pretrained sentence-transformers/all-MiniLM-L6-v2
      (BERT-family, frozen) with a LoRA adapter on the query/value
      attention projections, static position_ids, mean-pooled over the
      attention mask -> linear projection to TEXT_FEATURE_DIM.
    - Image encoder: the same from-scratch 3-layer CNN used by
      tiny_multimodal (kept unchanged so this model isolates the
      contribution of a pretrained *text* tower specifically, mirroring
      how axiom_lora.py isolates a pretrained *vision* tower).
    - Fusion: concatenation -> classifier head (unchanged pattern).

Scope note: this module covers Python-side train/export/accuracy-gate
only. On-device Swift integration (a WordPiece tokenizer in the app,
which the char-level models never needed) is a separate, larger piece of
work not undertaken in this pass -- consistent with how axiom_lora_v1 was
bundled locally without being made the default model before its
on-device evaluation was complete.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import torch
import torch.nn as nn
from torch import Tensor

from axiom.data.images import IMAGE_SIZE

from .tiny_multimodal import ImageEncoder, IMAGE_FEATURE_DIM as CNN_IMAGE_FEATURE_DIM, TinyMultimodalBaseline

TEXT_MODEL_ID = "sentence-transformers/all-MiniLM-L6-v2"
TEXT_MAX_TOKENS = 32
TEXT_FEATURE_DIM = 64

LORA_RANK = 8
LORA_ALPHA = 16.0

IMAGE_FEATURE_DIM = CNN_IMAGE_FEATURE_DIM  # 64, reusing tiny_multimodal's CNN
FUSION_DIM = IMAGE_FEATURE_DIM + TEXT_FEATURE_DIM


class StaticPositionIdsWrapper(nn.Module):
    """Wraps a HF encoder so position_ids is a static registered buffer,
    not computed dynamically at trace time. See module docstring."""

    def __init__(self, base_model: nn.Module, max_len: int) -> None:
        super().__init__()
        self.base_model = base_model
        position_ids = torch.arange(max_len, dtype=torch.long).unsqueeze(0)
        self.register_buffer("position_ids", position_ids)

    def forward(self, input_ids: Tensor, attention_mask: Tensor) -> Tensor:
        out = self.base_model(
            input_ids=input_ids,
            attention_mask=attention_mask,
            position_ids=self.position_ids.expand(input_ids.shape[0], -1),
        )
        # config.return_dict=False -> tuple; first element is last_hidden_state
        return out[0]


def _load_pretrained_text_tower() -> nn.Module:
    from peft import LoraConfig, get_peft_model
    from transformers import AutoModel

    base = AutoModel.from_pretrained(TEXT_MODEL_ID)
    base.config.return_dict = False

    lora_config = LoraConfig(
        r=LORA_RANK,
        lora_alpha=LORA_ALPHA,
        target_modules=["query", "value"],
        lora_dropout=0.0,
    )
    adapted = get_peft_model(base, lora_config)
    return StaticPositionIdsWrapper(adapted, TEXT_MAX_TOKENS)


class PretrainedTextEncoder(nn.Module):
    """Frozen pretrained MiniLM + LoRA adapter, mean-pooled -> projection."""

    def __init__(self) -> None:
        super().__init__()
        self.tower = _load_pretrained_text_tower()
        hidden_size = self.tower.base_model.config.hidden_size
        self.proj = nn.Linear(hidden_size, TEXT_FEATURE_DIM)

    def forward(self, input_ids: Tensor, attention_mask: Tensor) -> Tensor:
        hidden = self.tower(input_ids, attention_mask)  # (B, L, H)
        mask = attention_mask.unsqueeze(-1).float()
        lengths = mask.sum(dim=1).clamp(min=1)
        pooled = (hidden * mask).sum(dim=1) / lengths  # mean pool, masked
        return self.proj(pooled)


class AxiomLoraTextNet(nn.Module):
    """Pretrained-text-tower + LoRA, from-scratch image CNN (unchanged),
    concatenation fusion, classification head."""

    def __init__(self, num_classes: int) -> None:
        super().__init__()
        self.image_encoder = ImageEncoder()
        self.text_encoder = PretrainedTextEncoder()
        self.classifier = nn.Sequential(
            nn.Linear(FUSION_DIM, 64),
            nn.ReLU(),
            nn.Linear(64, num_classes),
        )

    def forward(self, images: Tensor, packed_text: Tensor) -> Tensor:
        # packed_text: (B, 2, TEXT_MAX_TOKENS) -- row 0 = input_ids, row 1 = attention_mask
        input_ids = packed_text[:, 0, :].long()
        attention_mask = packed_text[:, 1, :].long()
        img_feat = self.image_encoder(images)
        txt_feat = self.text_encoder(input_ids, attention_mask)
        fused = torch.cat([img_feat, txt_feat], dim=1)
        return self.classifier(fused)


_tokenizer = None


def _get_tokenizer():
    global _tokenizer
    if _tokenizer is None:
        from transformers import AutoTokenizer

        _tokenizer = AutoTokenizer.from_pretrained(TEXT_MODEL_ID)
    return _tokenizer


def encode_question_packed(question: str) -> list[list[int]]:
    """Tokenize a question to a fixed-length (2, TEXT_MAX_TOKENS) packed
    [input_ids, attention_mask] structure, matching AxiomLoraTextNet's
    unpacking convention."""
    tok = _get_tokenizer()
    encoded = tok(
        question,
        return_tensors="pt",
        padding="max_length",
        truncation=True,
        max_length=TEXT_MAX_TOKENS,
    )
    return [
        encoded["input_ids"][0].tolist(),
        encoded["attention_mask"][0].tolist(),
    ]


class AxiomLoraTextBaseline(TinyMultimodalBaseline):
    """Trainable baseline using AxiomLoraTextNet.

    Subclasses TinyMultimodalBaseline like AxiomLoraBaseline does, but
    overrides batch preparation and single-example prediction since text
    is packed WordPiece token ids + attention mask, not char-level ids.
    """

    def _build_net(self, num_classes: int) -> nn.Module:
        return AxiomLoraTextNet(num_classes)

    def _prepare_batch(self, rows):
        from axiom.eval import normalize_text

        loader = self._ensure_image_loader()

        images: list[Tensor] = []
        packed_text: list[list[list[int]]] = []
        labels: list[int] = []

        for row in rows:
            img = loader.load_and_preprocess(row["image_filename"])
            images.append(img)
            packed_text.append(encode_question_packed(row["question"]))
            answer = normalize_text(str(row["answer"]))
            labels.append(self._label_to_idx.get(answer, 0))

        return (
            torch.stack(images),
            torch.tensor(packed_text, dtype=torch.long),
            torch.tensor(labels, dtype=torch.long),
        )

    def predict_one(self, row: dict[str, Any]) -> str:
        if not self._is_trained or self._net is None:
            raise RuntimeError("AxiomLoraTextBaseline.predict_one() called before train().")

        loader = self._ensure_image_loader()
        img = loader.load_and_preprocess(row["image_filename"]).unsqueeze(0).to(self._device)
        packed = torch.tensor(
            [encode_question_packed(row["question"])], dtype=torch.long, device=self._device
        )

        with torch.no_grad():
            logits = self._net(img, packed)
            pred_idx = logits.argmax(dim=1).item()

        return self._idx_to_label.get(pred_idx, "")

    def save_checkpoint(self, output_dir: str | Path) -> dict[str, str]:
        paths = super().save_checkpoint(output_dir)
        meta_path = Path(paths["architecture"])
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        meta.update({
            "text_tower": f"{TEXT_MODEL_ID} (transformers, pretrained, frozen except LoRA)",
            "lora_adapter": "query/value attention projections",
            "lora_rank": LORA_RANK,
            "lora_alpha": LORA_ALPHA,
            "text_max_tokens": TEXT_MAX_TOKENS,
            "image_encoder": "from-scratch 3-layer CNN (unchanged from tiny_multimodal)",
            "position_ids": "static registered buffer (fixed-length input contract) -- "
                             "the fix that unblocks CoreML conversion; see module docstring",
        })
        meta_path.write_text(json.dumps(meta, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return paths

    def export_coreml(self, output_dir: str | Path) -> dict[str, Any]:
        """Export to Core ML. Input contract differs from tiny_multimodal/
        axiom_lora: image + packed (input_ids, attention_mask) tensors,
        not image + char_ids -- documented in architecture.json, consumed
        by this project's Python-side accuracy gate only in this pass
        (see module docstring re: Swift/on-device scope)."""
        if not self._is_trained or self._net is None:
            raise RuntimeError("Cannot export before training.")

        import coremltools as ct

        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        example_image = torch.rand(1, 3, IMAGE_SIZE, IMAGE_SIZE)
        example_packed = torch.zeros(1, 2, TEXT_MAX_TOKENS, dtype=torch.long)
        example_packed[0, 1, :4] = 1  # a plausible attention_mask prefix

        self._net = self._net.to("cpu")
        self._net.eval()
        with torch.no_grad():
            traced = torch.jit.trace(self._net, (example_image, example_packed), strict=False)
        self._net = self._net.to(self._device)

        mlmodel = ct.convert(
            traced,
            inputs=[
                ct.ImageType(
                    name="image",
                    shape=(1, 3, IMAGE_SIZE, IMAGE_SIZE),
                    scale=1.0 / 255.0,
                    color_layout=ct.colorlayout.RGB,
                ),
                ct.TensorType(name="packed_text", shape=(1, 2, TEXT_MAX_TOKENS), dtype=int),
            ],
            outputs=[ct.TensorType(name="logits")],
            minimum_deployment_target=ct.target.iOS16,
        )

        mlpackage_path = output_path / "AxiomLoraText.mlpackage"
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
            "text_max_tokens": TEXT_MAX_TOKENS,
        }
