import Foundation

struct ModelInfo: Identifiable, Hashable {
    let id: String
    let displayName: String
    let family: String
    let stage: String
    let backend: String
    let isExecutable: Bool
    let isCoreMLReady: Bool

    var statusLabel: String {
        if isCoreMLReady { return "Core ML Ready" }
        if isExecutable { return "Executable" }
        return "Config Only"
    }
}

enum ModelCatalog {
    /// The default model ID used when the app launches.
    /// v1 is preferred: 128 classes, dataset v2, 27.5% test EM vs v0's 10%.
    /// axiom_lora_v1 (Phase 8) is available in the picker (see `all` below)
    /// but not made default -- it's a wash on quality, not a clear win
    /// (see docs/MODEL_SELECTION.md).
    static let defaultModelID = "tiny_multimodal_v1"

    static let all: [ModelInfo] = [
        ModelInfo(
            id: "axiom_lora_v1",
            displayName: "AXIOM-LoRA v1",
            family: "custom",
            stage: "trainable_baseline",
            backend: "coreml",
            isExecutable: true,
            isCoreMLReady: true
        ),
        ModelInfo(
            id: "tiny_multimodal_v1",
            displayName: "Tiny Multimodal v1",
            family: "custom",
            stage: "trainable_baseline",
            backend: "coreml",
            isExecutable: true,
            isCoreMLReady: true
        ),
        ModelInfo(
            id: "tiny_multimodal_v0",
            displayName: "Tiny Multimodal v0",
            family: "custom",
            stage: "trainable_baseline",
            backend: "coreml",
            isExecutable: true,
            isCoreMLReady: true
        ),
        ModelInfo(
            id: "question_lookup_v0",
            displayName: "Question Lookup Baseline v0",
            family: "baseline",
            stage: "baseline",
            backend: "heuristic",
            isExecutable: true,
            isCoreMLReady: false
        ),
        ModelInfo(
            id: "florence_2_base",
            displayName: "Florence-2 Base",
            family: "vlm",
            stage: "candidate",
            backend: "transformers",
            isExecutable: false,
            isCoreMLReady: false
        ),
        ModelInfo(
            id: "llava_mobile",
            displayName: "LLaVA Mobile",
            family: "vlm",
            stage: "candidate",
            backend: "transformers",
            isExecutable: false,
            isCoreMLReady: false
        ),
        ModelInfo(
            id: "qwen_vl_chat_int4",
            displayName: "Qwen-VL Chat INT4",
            family: "vlm",
            stage: "candidate",
            backend: "transformers",
            isExecutable: false,
            isCoreMLReady: false
        ),
    ]
}
