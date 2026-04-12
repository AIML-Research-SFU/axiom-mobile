import Foundation

struct InferenceResult {
    let answer: String
    let modelID: String
    let latencySeconds: Double
    let timestamp: Date
    let isPlaceholder: Bool
}
