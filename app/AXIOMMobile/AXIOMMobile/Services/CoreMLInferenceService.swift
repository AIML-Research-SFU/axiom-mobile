import CoreML
import UIKit

/// Real Core ML inference service for `tiny_multimodal_v0`.
///
/// Loads the bundled `TinyMultimodal.mlpackage` and label vocabulary,
/// preprocesses the screenshot and question, runs prediction, and
/// returns the top answer class.
///
/// This replaces `PlaceholderInferenceService` for models where
/// `isCoreMLReady` is `true`.
struct CoreMLInferenceService: InferenceServiceProtocol {

    // MARK: - Constants

    /// Expected input image size (matches Python training pipeline).
    private static let imageSize = 128

    /// Maximum character length for question encoding (matches Python `MAX_CHAR_LEN`).
    private static let maxCharLength = 128

    /// ASCII vocab size for character-level encoding (matches Python `VOCAB_SIZE`).
    private static let vocabSize = 128

    // MARK: - InferenceServiceProtocol

    func run(model: ModelInfo, image: UIImage?, question: String) async throws -> InferenceResult {
        let start = ContinuousClock.now

        let coreMLModel = try loadModel()
        let labelVocab = try loadLabelVocab()

        // Prepare image input
        let imageFeature = try prepareImage(image)

        // Prepare text input
        let charIdsArray = try prepareText(question)

        // Build prediction input
        let input = try MLDictionaryFeatureProvider(dictionary: [
            "image": imageFeature,
            "char_ids": charIdsArray
        ])

        // Run inference
        let output = try await coreMLModel.prediction(from: input)

        // Decode output logits → answer label + confidence
        let prediction = decodeOutput(output, labelVocab: labelVocab)

        let elapsed = ContinuousClock.now - start
        let seconds = Double(elapsed.components.seconds)
            + Double(elapsed.components.attoseconds) / 1_000_000_000_000_000_000

        return InferenceResult(
            answer: prediction.label,
            modelID: model.id,
            latencySeconds: seconds,
            timestamp: .now,
            isPlaceholder: false,
            confidence: prediction.confidence,
            numClasses: prediction.numClasses
        )
    }

    // MARK: - Model Loading

    private func loadModel() throws -> MLModel {
        guard let modelURL = Bundle.main.url(forResource: "TinyMultimodal", withExtension: "mlmodelc")
                ?? Bundle.main.url(forResource: "TinyMultimodal", withExtension: "mlpackage") else {
            throw CoreMLServiceError.modelNotFound
        }
        let config = MLModelConfiguration()
        config.computeUnits = .all
        return try MLModel(contentsOf: modelURL, configuration: config)
    }

    private func loadLabelVocab() throws -> [Int: String] {
        guard let vocabURL = Bundle.main.url(
            forResource: "tiny_multimodal_v0_labels",
            withExtension: "json"
        ) else {
            throw CoreMLServiceError.labelVocabNotFound
        }

        let data = try Data(contentsOf: vocabURL)
        let labelToIdx = try JSONDecoder().decode([String: Int].self, from: data)

        // Invert: idx → label
        var idxToLabel: [Int: String] = [:]
        for (label, idx) in labelToIdx {
            idxToLabel[idx] = label
        }
        return idxToLabel
    }

    // MARK: - Input Preparation

    private func prepareImage(_ image: UIImage?) throws -> MLFeatureValue {
        // If no image provided, use a blank image (model still needs valid input)
        let sourceImage = image ?? createBlankImage()

        guard let cgImage = sourceImage.cgImage else {
            throw CoreMLServiceError.imageConversionFailed
        }

        // Create a CVPixelBuffer at the expected 128×128 RGB size
        let pixelBuffer = try createPixelBuffer(from: cgImage)
        return MLFeatureValue(pixelBuffer: pixelBuffer)
    }

    private func createPixelBuffer(from cgImage: CGImage) throws -> CVPixelBuffer {
        var pixelBuffer: CVPixelBuffer?
        let attrs: [CFString: Any] = [
            kCVPixelBufferCGImageCompatibilityKey: true,
            kCVPixelBufferCGBitmapContextCompatibilityKey: true
        ]
        let status = CVPixelBufferCreate(
            kCFAllocatorDefault,
            Self.imageSize,
            Self.imageSize,
            kCVPixelFormatType_32BGRA,
            attrs as CFDictionary,
            &pixelBuffer
        )

        guard status == kCVReturnSuccess, let buffer = pixelBuffer else {
            throw CoreMLServiceError.imageConversionFailed
        }

        CVPixelBufferLockBaseAddress(buffer, [])
        defer { CVPixelBufferUnlockBaseAddress(buffer, []) }

        guard let context = CGContext(
            data: CVPixelBufferGetBaseAddress(buffer),
            width: Self.imageSize,
            height: Self.imageSize,
            bitsPerComponent: 8,
            bytesPerRow: CVPixelBufferGetBytesPerRow(buffer),
            space: CGColorSpaceCreateDeviceRGB(),
            bitmapInfo: CGImageAlphaInfo.premultipliedFirst.rawValue | CGBitmapInfo.byteOrder32Little.rawValue
        ) else {
            throw CoreMLServiceError.imageConversionFailed
        }

        context.draw(cgImage, in: CGRect(x: 0, y: 0, width: Self.imageSize, height: Self.imageSize))
        return buffer
    }

    private func prepareText(_ question: String) throws -> MLFeatureValue {
        let charIds = encodeQuestion(question)

        // Shape: [1, 128] — matches the exported model's expected input
        let shape: [NSNumber] = [1, NSNumber(value: Self.maxCharLength)]
        let multiArray = try MLMultiArray(shape: shape, dataType: .int32)

        for i in 0..<Self.maxCharLength {
            multiArray[[0, NSNumber(value: i)] as [NSNumber]] = NSNumber(value: charIds[i])
        }

        return MLFeatureValue(multiArray: multiArray)
    }

    /// Encodes a question string to fixed-length ASCII character IDs.
    /// Matches the Python `encode_question()` function exactly.
    private func encodeQuestion(_ question: String) -> [Int32] {
        var ids = [Int32]()
        ids.reserveCapacity(Self.maxCharLength)

        for (index, character) in question.unicodeScalars.enumerated() {
            guard index < Self.maxCharLength else { break }
            let code = min(Int32(character.value), Int32(Self.vocabSize - 1))
            ids.append(code)
        }

        // Pad to fixed length with zeros
        while ids.count < Self.maxCharLength {
            ids.append(0)
        }

        return ids
    }

    // MARK: - Output Decoding

    /// Decoded prediction with confidence signal.
    private struct Prediction {
        let label: String
        let confidence: Double
        let numClasses: Int
    }

    /// Decodes logits into a label, softmax confidence, and class count.
    ///
    /// Softmax is computed in a numerically stable way (subtract max before exp)
    /// to produce a proper probability distribution over the 24-class vocabulary.
    private func decodeOutput(_ output: MLFeatureProvider, labelVocab: [Int: String]) -> Prediction {
        guard let logitsValue = output.featureValue(for: "logits"),
              let logits = logitsValue.multiArrayValue else {
            return Prediction(label: "Error: no logits output", confidence: 0, numClasses: 0)
        }

        // Shape is [1, num_classes]
        let numClasses = logits.shape.last?.intValue ?? 0
        guard numClasses > 0 else {
            return Prediction(label: "Error: empty logits", confidence: 0, numClasses: 0)
        }

        // Extract raw logits and find argmax
        var rawLogits = [Float](repeating: 0, count: numClasses)
        var maxIdx = 0
        var maxVal = Float(-Float.greatestFiniteMagnitude)

        for i in 0..<numClasses {
            let val = logits[[0, NSNumber(value: i)] as [NSNumber]].floatValue
            rawLogits[i] = val
            if val > maxVal {
                maxVal = val
                maxIdx = i
            }
        }

        // Numerically stable softmax: subtract max, then exp and normalize
        var expValues = [Float](repeating: 0, count: numClasses)
        var expSum: Float = 0
        for i in 0..<numClasses {
            let e = exp(rawLogits[i] - maxVal)
            expValues[i] = e
            expSum += e
        }

        let topConfidence = Double(expValues[maxIdx] / expSum)
        let label = labelVocab[maxIdx] ?? "class_\(maxIdx)"

        return Prediction(
            label: label,
            confidence: topConfidence,
            numClasses: numClasses
        )
    }

    // MARK: - Helpers

    private func createBlankImage() -> UIImage {
        let size = CGSize(width: Self.imageSize, height: Self.imageSize)
        let renderer = UIGraphicsImageRenderer(size: size)
        return renderer.image { context in
            UIColor.black.setFill()
            context.fill(CGRect(origin: .zero, size: size))
        }
    }
}

// MARK: - Errors

enum CoreMLServiceError: LocalizedError {
    case modelNotFound
    case labelVocabNotFound
    case imageConversionFailed

    var errorDescription: String? {
        switch self {
        case .modelNotFound:
            "TinyMultimodal.mlpackage not found in app bundle. Re-export from Python and add to Xcode project."
        case .labelVocabNotFound:
            "tiny_multimodal_v0_labels.json not found in app bundle."
        case .imageConversionFailed:
            "Failed to convert UIImage to CGImage for Core ML input."
        }
    }
}
