import UIKit

protocol InferenceServiceProtocol {
    func run(model: ModelInfo, image: UIImage?, question: String) async throws -> InferenceResult
}

struct PlaceholderInferenceService: InferenceServiceProtocol {
    func run(model: ModelInfo, image: UIImage?, question: String) async throws -> InferenceResult {
        let start = ContinuousClock.now
        let delay: Duration = model.family == "baseline" ? .milliseconds(150) : .milliseconds(600)
        try await Task.sleep(for: delay)
        let elapsed = ContinuousClock.now - start
        let seconds = Double(elapsed.components.seconds)
            + Double(elapsed.components.attoseconds) / 1_000_000_000_000_000_000

        return InferenceResult(
            answer: "Demo answer: \(model.displayName) not connected yet",
            modelID: model.id,
            latencySeconds: seconds,
            timestamp: .now,
            isPlaceholder: true
        )
    }
}
