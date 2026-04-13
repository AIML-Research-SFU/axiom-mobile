import SwiftUI

struct TestbedView: View {
    @State private var viewModel = TestbedViewModel()

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(spacing: AXSpacing.sectionGap) {

                    // MARK: - Input Zone (hero)

                    ScreenshotSection(
                        selectedItem: $viewModel.selectedPhotoItem,
                        image: viewModel.screenshotImage,
                        onClear: { viewModel.clearScreenshot() },
                        onSaveAsBenchmarkInput: {
                            viewModel.saveBenchmarkScreenshot()
                        }
                    )

                    QuestionInputSection(question: $viewModel.question)

                    // MARK: - Configuration

                    ModelPickerSection(selectedModel: $viewModel.selectedModel)

                    BenchmarkConfigSection(
                        enabled: $viewModel.benchmarkEnabled,
                        iterations: $viewModel.benchmarkIterations
                    )

                    // MARK: - Primary Action

                    primaryActionButton

                    // MARK: - Output Zone

                    if let result = viewModel.result {
                        AnswerCard(result: result)
                            .transition(
                                .asymmetric(
                                    insertion: .opacity.combined(
                                        with: .scale(scale: 0.97)
                                    ),
                                    removal: .opacity
                                )
                            )
                    }

                    // MARK: - Supporting Info

                    DebugMetricsCard(
                        selectedModel: viewModel.selectedModel,
                        imageStatus: viewModel.imageStatusText,
                        questionLength: viewModel.question.count,
                        result: viewModel.result
                    )

                    if !viewModel.benchmarkRecords.isEmpty {
                        BenchmarkSummaryCard(
                            recordCount: viewModel.benchmarkRecordCount,
                            averageLatencyMs: viewModel
                                .benchmarkAverageLatencyMs,
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
                .padding(.horizontal, AXSpacing.pageMargin)
                .padding(.bottom, AXSpacing.xxl)
            }
            .scrollIndicators(.hidden)
            .background { backgroundGradient }
            .navigationTitle("AXIOM")
            .toolbarTitleDisplayMode(.large)
            .onChange(of: viewModel.selectedPhotoItem) { _, _ in
                Task { await viewModel.loadImage() }
            }
            .task {
                if viewModel.isAutoBenchmarkRequested {
                    await viewModel.runAutoBenchmark()
                } else if viewModel.isDemoModeRequested {
                    await viewModel.runDemoMode()
                }
            }
            .axAnimation(AXMotion.gentle, value: viewModel.result != nil)
        }
    }

    // MARK: - Primary Action Button

    private var primaryActionButton: some View {
        VStack(spacing: AXSpacing.sm) {
            Button {
                Task {
                    if viewModel.benchmarkEnabled {
                        await viewModel.runBenchmark()
                    } else {
                        await viewModel.run()
                    }
                }
            } label: {
                HStack(spacing: AXSpacing.sm) {
                    if viewModel.isRunning {
                        ProgressView()
                            .tint(.white)
                    } else {
                        Image(
                            systemName: viewModel.benchmarkEnabled
                                ? "timer"
                                : "play.fill"
                        )
                    }

                    if viewModel.isBenchmarking {
                        Text(
                            "Running \(viewModel.benchmarkProgress) of \(viewModel.benchmarkIterations)"
                        )
                    } else if viewModel.benchmarkEnabled {
                        Text("Run Benchmark (\(viewModel.benchmarkIterations))")
                    } else {
                        Text("Run Inference")
                    }
                }
            }
            .buttonStyle(AXPrimaryButtonStyle())
            .disabled(!viewModel.canRun)
            .sensoryFeedback(.success, trigger: viewModel.isRunning) {
                oldValue,
                newValue in
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
                .tint(AXColor.accentPrimary)
                .padding(.horizontal, AXSpacing.sm)
            }
        }
    }

    // MARK: - Background

    private var backgroundGradient: some View {
        LinearGradient(
            colors: [
                AXColor.backgroundGradientTop,
                AXColor.backgroundBase,
                AXColor.backgroundGradientBottom,
            ],
            startPoint: .top,
            endPoint: .bottom
        )
        .ignoresSafeArea()
    }
}

#Preview {
    TestbedView()
}
