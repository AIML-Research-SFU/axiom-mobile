import Foundation

struct InferenceResult {
    let answer: String
    let modelID: String
    let latencySeconds: Double
    let timestamp: Date
    let isPlaceholder: Bool

    /// Softmax probability of the top-1 predicted class (0.0–1.0).
    ///
    /// For `tiny_multimodal_v0` (24-class classifier), this is computed
    /// from the logits via softmax. A uniform guess would be ~4.2% (1/24).
    /// `nil` for placeholder results where no real inference occurred.
    let confidence: Double?

    /// The number of classes in the model's output vocabulary.
    /// Used to contextualize confidence (e.g. 1/numClasses = random baseline).
    let numClasses: Int?

    init(
        answer: String,
        modelID: String,
        latencySeconds: Double,
        timestamp: Date,
        isPlaceholder: Bool,
        confidence: Double? = nil,
        numClasses: Int? = nil
    ) {
        self.answer = answer
        self.modelID = modelID
        self.latencySeconds = latencySeconds
        self.timestamp = timestamp
        self.isPlaceholder = isPlaceholder
        self.confidence = confidence
        self.numClasses = numClasses
    }

    // MARK: - Confidence Assessment

    /// Minimum confidence threshold for displaying a result as trustworthy.
    ///
    /// **Rationale:** For a 24-class classifier, random guessing yields ~4.2%.
    /// A threshold of 40% requires the model to be ~10× more confident than
    /// chance — a conservative bar that filters out collapse-to-frequent-class
    /// behavior while permitting genuinely confident predictions. This was
    /// chosen because:
    /// - Out-of-domain inputs (wrong question type) typically produce
    ///   near-uniform or weakly-peaked distributions (< 20% top-1).
    /// - In-domain inputs where the model has learned the pattern produce
    ///   top-1 probabilities well above 50%.
    /// - 40% sits safely between these regimes with margin for calibration drift.
    static let confidenceThreshold: Double = 0.40

    /// Whether this result's confidence is too low to present as a valid answer.
    var isLowConfidence: Bool {
        guard let confidence, !isPlaceholder else { return false }
        return confidence < Self.confidenceThreshold
    }
}
