import SwiftUI
import PhotosUI

@Observable
final class TestbedViewModel {
    // MARK: - Testbed state

    var selectedPhotoItem: PhotosPickerItem?
    var screenshotImage: UIImage?
    var question = ""
    var selectedModel: ModelInfo = ModelCatalog.all[0]
    var result: InferenceResult?
    var isRunning = false

    // MARK: - Benchmark state

    var benchmarkEnabled = false
    var benchmarkIterations = 10
    var benchmarkProgress = 0
    var isBenchmarking = false
    private(set) var benchmarkRecords: [BenchmarkRecord] = []
    private(set) var lastExportURL: URL?

    private let inferenceService: any InferenceServiceProtocol = PlaceholderInferenceService()

    // MARK: - Computed properties

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

    var benchmarkRecordCount: Int { benchmarkRecords.count }

    var benchmarkAverageLatencyMs: Double {
        guard !benchmarkRecords.isEmpty else { return 0 }
        let total = benchmarkRecords.reduce(0) { $0 + $1.latencyMs }
        return Double(total) / Double(benchmarkRecords.count)
    }

    var benchmarkMinLatencyMs: Int {
        benchmarkRecords.map(\.latencyMs).min() ?? 0
    }

    var benchmarkMaxLatencyMs: Int {
        benchmarkRecords.map(\.latencyMs).max() ?? 0
    }

    var benchmarkModelID: String? {
        benchmarkRecords.last?.modelID
    }

    var hasExported: Bool { lastExportURL != nil }

    // MARK: - Actions

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

        appendRecord(from: newResult, runKind: .single, iterationIndex: 0)
    }

    func runBenchmark() async {
        guard canRun else { return }
        isRunning = true
        isBenchmarking = true
        benchmarkProgress = 0
        defer {
            isRunning = false
            isBenchmarking = false
        }

        for i in 0..<benchmarkIterations {
            if Task.isCancelled { break }

            guard let newResult = try? await inferenceService.run(
                model: selectedModel,
                image: screenshotImage,
                question: question
            ) else { continue }

            appendRecord(from: newResult, runKind: .benchmark, iterationIndex: i)
            benchmarkProgress = i + 1

            withAnimation(.smooth) {
                result = newResult
            }
        }
    }

    func exportCSV() {
        do {
            lastExportURL = try BenchmarkExporter.writeCSV(benchmarkRecords)
        } catch {
            lastExportURL = nil
        }
    }

    func clearBenchmark() {
        benchmarkRecords.removeAll()
        lastExportURL = nil
        benchmarkProgress = 0
    }

    func clearScreenshot() {
        selectedPhotoItem = nil
        screenshotImage = nil
    }

    // MARK: - Private

    private func appendRecord(
        from result: InferenceResult,
        runKind: BenchmarkRecord.RunKind,
        iterationIndex: Int
    ) {
        let record = BenchmarkRecord(
            timestamp: result.timestamp,
            modelID: result.modelID,
            imageLoaded: screenshotImage != nil,
            questionLength: question.count,
            latencyMs: Int(result.latencySeconds * 1000),
            isPlaceholder: result.isPlaceholder,
            runKind: runKind,
            iterationIndex: iterationIndex
        )
        benchmarkRecords.append(record)
    }
}
