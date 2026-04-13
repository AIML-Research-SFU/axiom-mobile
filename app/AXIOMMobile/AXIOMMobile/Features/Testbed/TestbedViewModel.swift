import PhotosUI
import SwiftUI
import TipKit
import UIKit

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
    private(set) var lastMetadataURL: URL?

    private let placeholderService: any InferenceServiceProtocol =
        PlaceholderInferenceService()
    private let coreMLService: any InferenceServiceProtocol =
        CoreMLInferenceService()

    /// Routes to the real Core ML service for models that have a bundled
    /// `.mlpackage`, and falls back to the placeholder for all others.
    private var inferenceService: any InferenceServiceProtocol {
        selectedModel.isCoreMLReady ? coreMLService : placeholderService
    }

    // MARK: - Computed properties

    var canRun: Bool {
        !question.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty
            && !isRunning
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
            let image = UIImage(data: data)
        else {
            screenshotImage = nil
            return
        }
        screenshotImage = image
    }

    func run() async {
        guard canRun else { return }
        isRunning = true
        defer { isRunning = false }

        guard
            let newResult = try? await inferenceService.run(
                model: selectedModel,
                image: screenshotImage,
                question: question
            )
        else { return }

        withAnimation(.smooth) {
            result = newResult
        }

        appendRecord(from: newResult, runKind: .single, iterationIndex: 0)

        // Increment tip counter for benchmark mode suggestion.
        BenchmarkModeTip.singleRunCount += 1
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

            guard
                let newResult = try? await inferenceService.run(
                    model: selectedModel,
                    image: screenshotImage,
                    question: question
                )
            else { continue }

            appendRecord(
                from: newResult,
                runKind: .benchmark,
                iterationIndex: i
            )
            benchmarkProgress = i + 1

            withAnimation(.smooth) {
                result = newResult
            }
        }
    }

    func exportCSV() {
        do {
            let stamp = BenchmarkExporter.sessionStamp()
            lastExportURL = try BenchmarkExporter.writeCSV(
                benchmarkRecords,
                stamp: stamp
            )

            let device = UIDevice.current
            let bundle = Bundle.main
            let metadata = SessionMetadata(
                sessionID: UUID().uuidString,
                exportTimestamp: Date.now.formatted(.iso8601),
                deviceName: device.name,
                deviceModel: device.model,
                systemName: device.systemName,
                systemVersion: device.systemVersion,
                appVersion: bundle.infoDictionary?["CFBundleShortVersionString"]
                    as? String ?? "unknown",
                appBuild: bundle.infoDictionary?["CFBundleVersion"] as? String
                    ?? "unknown",
                modelID: benchmarkModelID ?? "unknown",
                isPlaceholder: benchmarkRecords.last?.isPlaceholder ?? true,
                benchmarkIterations: benchmarkRecords.filter {
                    $0.runKind == .benchmark
                }.count,
                recordCount: benchmarkRecords.count
            )
            lastMetadataURL = try BenchmarkExporter.writeMetadata(
                metadata,
                stamp: stamp
            )
        } catch {
            lastExportURL = nil
            lastMetadataURL = nil
        }
    }

    func clearBenchmark() {
        benchmarkRecords.removeAll()
        lastExportURL = nil
        lastMetadataURL = nil
        benchmarkProgress = 0
    }

    func clearScreenshot() {
        selectedPhotoItem = nil
        screenshotImage = nil
    }

    // MARK: - Auto-Benchmark

    /// Whether the app was launched with `--auto-benchmark` for headless profiling.
    var isAutoBenchmarkRequested: Bool {
        ProcessInfo.processInfo.arguments.contains("--auto-benchmark")
    }

    /// Whether the app was launched with `--demo-mode` for presentation setup.
    var isDemoModeRequested: Bool {
        ProcessInfo.processInfo.arguments.contains("--demo-mode")
    }

    /// Runs a complete benchmark session automatically for profiling workflows.
    ///
    /// Uses `tiny_multimodal_v0` with a representative benchmark input:
    /// - If a `benchmark_screenshot.png` exists in Documents (placed by a
    ///   one-time manual import), it is loaded for real image preprocessing.
    /// - Otherwise, a deterministic synthetic test pattern is generated so
    ///   the full pixel-buffer pipeline is exercised (not a blank image).
    ///
    /// Exports CSV + `_meta.json` to the app's Documents directory on completion.
    func runAutoBenchmark() async {
        // Select the Core ML-ready model
        guard
            let coreMLModel = ModelCatalog.all.first(where: { $0.isCoreMLReady }
            )
        else {
            return
        }
        selectedModel = coreMLModel
        question = BenchmarkInputProvider.defaultQuestion
        benchmarkEnabled = true
        benchmarkIterations = BenchmarkInputProvider.publishableIterations

        // Load a representative benchmark image
        let (image, source) = BenchmarkInputProvider.loadScreenshot()
        screenshotImage = image
        autoBenchmarkImageSource = source

        // Run the benchmark
        await runBenchmark()

        // Auto-export results
        exportCSV()
    }

    /// Describes the image source used for the last auto-benchmark or demo run.
    /// Either `"persisted"` (real screenshot from Documents) or
    /// `"synthetic"` (deterministic test pattern).
    private(set) var autoBenchmarkImageSource: String?

    // MARK: - Demo Mode

    /// Runs a single-shot demo inference for presentation setup.
    ///
    /// Selects `tiny_multimodal_v0`, loads a representative image via
    /// `BenchmarkInputProvider`, sets a canonical question, and runs
    /// **one** inference. Leaves the UI in a predictable demo-ready state
    /// showing the result — unlike `runAutoBenchmark()` which runs 50
    /// iterations and auto-exports.
    func runDemoMode() async {
        guard
            let coreMLModel = ModelCatalog.all.first(where: { $0.isCoreMLReady }
            )
        else {
            return
        }
        selectedModel = coreMLModel
        question = BenchmarkInputProvider.defaultQuestion
        benchmarkEnabled = false

        let (image, source) = BenchmarkInputProvider.loadScreenshot()
        screenshotImage = image
        autoBenchmarkImageSource = source

        await run()
    }

    /// Saves the currently loaded screenshot as the persisted benchmark input.
    ///
    /// Call this once after importing a representative screenshot to enable
    /// repeatable profiling with real data across `--auto-benchmark` sessions.
    func saveBenchmarkScreenshot() {
        guard let image = screenshotImage else { return }
        try? BenchmarkInputProvider.persistScreenshot(image)
    }

    /// Whether a persisted benchmark screenshot is available.
    var hasBenchmarkScreenshot: Bool {
        BenchmarkInputProvider.hasPersistedScreenshot
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
            iterationIndex: iterationIndex,
            confidence: result.confidence
        )
        benchmarkRecords.append(record)
    }
}
