import SwiftUI
import TipKit

struct TestbedView: View {
    @State private var viewModel = TestbedViewModel()
    @State private var sectionsAppeared = false
    @FocusState private var isQuestionFocused: Bool

    private let researchContextTip = ResearchContextTip()

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(spacing: AXSpacing.sectionGap) {

                    // MARK: - Onboarding Tip

                    TipView(researchContextTip)
                        .tipBackground(AXColor.glassFill)

                    // MARK: - Input Zone (hero)

                    ScreenshotSection(
                        selectedItem: $viewModel.selectedPhotoItem,
                        image: viewModel.screenshotImage,
                        onClear: { viewModel.clearScreenshot() },
                        onSaveAsBenchmarkInput: {
                            viewModel.saveBenchmarkScreenshot()
                        }
                    )
                    .axStaggeredAppearance(index: 0, isVisible: sectionsAppeared)

                    QuestionInputSection(
                        question: $viewModel.question,
                        isFocused: $isQuestionFocused,
                        selectedModelID: viewModel.selectedModel.id
                    )
                    .axStaggeredAppearance(
                        index: 1, isVisible: sectionsAppeared)

                    // MARK: - Configuration

                    ModelPickerSection(selectedModel: $viewModel.selectedModel)
                        .axStaggeredAppearance(
                            index: 2, isVisible: sectionsAppeared)
                        .sensoryFeedback(
                            AXHaptics.modelChanged,
                            trigger: viewModel.selectedModel
                        )

                    BenchmarkConfigSection(
                        enabled: $viewModel.benchmarkEnabled,
                        iterations: $viewModel.benchmarkIterations
                    )
                    .axStaggeredAppearance(
                        index: 3, isVisible: sectionsAppeared)
                    .sensoryFeedback(
                        AXHaptics.toggleChanged,
                        trigger: viewModel.benchmarkEnabled
                    )

                    // MARK: - Primary Action

                    primaryActionButton
                        .axStaggeredAppearance(
                            index: 4, isVisible: sectionsAppeared)

                    // MARK: - Output Zone

                    if let result = viewModel.result {
                        AnswerCard(result: result)
                            .transition(AXTransition.resultAppearance)
                    }

                    // MARK: - Supporting Info

                    DebugMetricsCard(
                        selectedModel: viewModel.selectedModel,
                        imageStatus: viewModel.imageStatusText,
                        questionLength: viewModel.question.count,
                        result: viewModel.result
                    )
                    .axStaggeredAppearance(
                        index: 5, isVisible: sectionsAppeared)

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
                        .transition(AXTransition.cardEntrance)
                    }
                }
                .padding(.horizontal, AXSpacing.pageMargin)
                .padding(.bottom, AXSpacing.xxl)
                .axResponsiveContainer()
            }
            .scrollDismissesKeyboard(.interactively)
            .scrollIndicators(.hidden)
            .background { backgroundGradient }
            .navigationTitle("AXIOM")
            .toolbarTitleDisplayMode(.large)
            .toolbar {
                ToolbarItemGroup(placement: .keyboard) {
                    Spacer()
                    Button("Done") {
                        isQuestionFocused = false
                    }
                    .font(AXFont.button)
                    .tint(AXColor.accentPrimary)
                }
            }
            .onChange(of: viewModel.selectedPhotoItem) { _, _ in
                Task { await viewModel.loadImage() }
            }
            .sensoryFeedback(
                AXHaptics.imageLoaded,
                trigger: viewModel.screenshotImage != nil
            )
            .sensoryFeedback(
                AXHaptics.inferenceComplete,
                trigger: viewModel.isRunning
            ) { oldValue, newValue in
                oldValue && !newValue
            }
            .sensoryFeedback(
                AXHaptics.exportSuccess,
                trigger: viewModel.hasExported
            ) { oldValue, newValue in
                !oldValue && newValue
            }
            .task {
                if viewModel.isAutoBenchmarkRequested {
                    await viewModel.runAutoBenchmark()
                } else if viewModel.isDemoModeRequested {
                    await viewModel.runDemoMode()
                }
            }
            .onAppear {
                // Trigger staggered card entrance
                withAnimation {
                    sectionsAppeared = true
                }
            }
            .axAnimation(AXMotion.gentle, value: viewModel.result != nil)
        }
    }

    // MARK: - Primary Action Button

    private var primaryActionButton: some View {
        VStack(spacing: AXSpacing.sm) {
            Button {
                isQuestionFocused = false
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
