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
        Button {
            Task { await viewModel.run() }
        } label: {
            HStack(spacing: 8) {
                if viewModel.isRunning {
                    ProgressView()
                        .tint(.white)
                } else {
                    Image(systemName: "play.fill")
                }
                Text("Run Inference")
                    .fontWeight(.semibold)
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
        .accessibilityLabel("Run inference with \(viewModel.selectedModel.displayName)")
    }
}

#Preview {
    TestbedView()
}
