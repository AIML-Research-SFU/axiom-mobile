import SwiftUI

struct TestbedView: View {
    @State private var viewModel = TestbedViewModel()

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(spacing: 20) {
                    ScreenshotSection(
                        selectedItem: $viewModel.selectedPhotoItem,
                        image: viewModel.screenshotImage,
                        onClear: { viewModel.clearScreenshot() }
                    )

                    QuestionInputSection(question: $viewModel.question)

                    ModelPickerSection(selectedModel: $viewModel.selectedModel)

                    BenchmarkConfigSection(
                        enabled: $viewModel.benchmarkEnabled,
                        iterations: $viewModel.benchmarkIterations
                    )

                    runButton

                    if let result = viewModel.result {
                        AnswerCard(result: result)
                    }

                    DebugMetricsCard(
                        selectedModel: viewModel.selectedModel,
                        imageStatus: viewModel.imageStatusText,
                        questionLength: viewModel.question.count,
                        result: viewModel.result
                    )

                    if !viewModel.benchmarkRecords.isEmpty {
                        BenchmarkSummaryCard(
                            recordCount: viewModel.benchmarkRecordCount,
                            averageLatencyMs: viewModel.benchmarkAverageLatencyMs,
                            minLatencyMs: viewModel.benchmarkMinLatencyMs,
                            maxLatencyMs: viewModel.benchmarkMaxLatencyMs,
                            modelID: viewModel.benchmarkModelID,
                            hasExported: viewModel.hasExported,
                            exportURL: viewModel.lastExportURL,
                            metadataURL: viewModel.lastMetadataURL,
                            onExport: { viewModel.exportCSV() },
                            onClear: { viewModel.clearBenchmark() }
                        )
                    }
                }
                .padding()
            }
            .scrollIndicators(.hidden)
            .navigationTitle("AXIOM Testbed")
            .onChange(of: viewModel.selectedPhotoItem) { _, _ in
                Task { await viewModel.loadImage() }
            }
        }
    }

    private var runButton: some View {
        VStack(spacing: 8) {
            Button {
                Task {
                    if viewModel.benchmarkEnabled {
                        await viewModel.runBenchmark()
                    } else {
                        await viewModel.run()
                    }
                }
            } label: {
                HStack(spacing: 8) {
                    if viewModel.isRunning {
                        ProgressView()
                            .tint(.white)
                    } else {
                        Image(systemName: viewModel.benchmarkEnabled
                              ? "timer"
                              : "play.fill")
                    }

                    if viewModel.isBenchmarking {
                        Text("Running \(viewModel.benchmarkProgress) of \(viewModel.benchmarkIterations)")
                            .fontWeight(.semibold)
                    } else if viewModel.benchmarkEnabled {
                        Text("Run Benchmark (\(viewModel.benchmarkIterations) runs)")
                            .fontWeight(.semibold)
                    } else {
                        Text("Run Inference")
                            .fontWeight(.semibold)
                    }
                }
                .frame(maxWidth: .infinity)
                .padding(.vertical, 14)
            }
            .buttonStyle(.borderedProminent)
            .controlSize(.large)
            .disabled(!viewModel.canRun)
            .sensoryFeedback(.success, trigger: viewModel.isRunning) { oldValue, newValue in
                oldValue && !newValue
            }
            .accessibilityLabel(
                viewModel.benchmarkEnabled
                    ? "Run benchmark with \(viewModel.selectedModel.displayName)"
                    : "Run inference with \(viewModel.selectedModel.displayName)"
            )

            if viewModel.isBenchmarking {
                ProgressView(
                    value: Double(viewModel.benchmarkProgress),
                    total: Double(viewModel.benchmarkIterations)
                )
                .tint(.accentColor)
            }
        }
    }
}

#Preview {
    TestbedView()
}
