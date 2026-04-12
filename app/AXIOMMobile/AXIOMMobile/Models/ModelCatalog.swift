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
    static let all: [ModelInfo] = [
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
