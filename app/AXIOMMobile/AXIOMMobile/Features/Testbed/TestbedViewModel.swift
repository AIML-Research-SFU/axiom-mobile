import SwiftUI
import PhotosUI

@Observable
final class TestbedViewModel {
    var selectedPhotoItem: PhotosPickerItem?
    var screenshotImage: UIImage?
    var question = ""
    var selectedModel: ModelInfo = ModelCatalog.all[0]
    var result: InferenceResult?
    var isRunning = false

    private let inferenceService: any InferenceServiceProtocol = PlaceholderInferenceService()

    var canRun: Bool {
        !question.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty && !isRunning
    }

    var imageStatusText: String {
        if let image = screenshotImage {
            let w = Int(image.size.width)
            let h = Int(image.size.height)
            return "Loaded (\(w) \u{00d7} \(h))"
        }
        return "No image"
    }

    func loadImage() async {
        guard let item = selectedPhotoItem,
              let data = try? await item.loadTransferable(type: Data.self),
              let image = UIImage(data: data) else {
            screenshotImage = nil
            return
        }
        screenshotImage = image
    }

    func run() async {
        guard canRun else { return }
        isRunning = true
        defer { isRunning = false }

        guard let newResult = try? await inferenceService.run(
            model: selectedModel,
            image: screenshotImage,
            question: question
        ) else { return }

        withAnimation(.smooth) {
            result = newResult
        }
    }

    func clearScreenshot() {
        selectedPhotoItem = nil
        screenshotImage = nil
    }
}
