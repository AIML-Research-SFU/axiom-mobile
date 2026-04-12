import SwiftUI

struct DebugMetricsCard: View {
    let selectedModel: ModelInfo
    let imageStatus: String
    let questionLength: Int
    let result: InferenceResult?

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            Label("Debug", systemImage: "ant")
                .font(.headline)

            Grid(alignment: .leading, horizontalSpacing: 12, verticalSpacing: 8) {
                MetricRow(label: "Model ID", value: selectedModel.id)
                MetricRow(label: "Status", value: selectedModel.statusLabel)
                MetricRow(label: "Image", value: imageStatus)
                MetricRow(label: "Question", value: "\(questionLength) characters")

                if let result {
                    let ms = Int(result.latencySeconds * 1000)
                    MetricRow(label: "Latency", value: "\(ms) ms")
                    MetricRow(label: "Result Type", value: result.isPlaceholder ? "Placeholder" : "Live")
                }
            }
        }
        .padding()
        .background(.regularMaterial, in: RoundedRectangle(cornerRadius: 16))
        .accessibilityElement(children: .combine)
    }
}

private struct MetricRow: View {
    let label: String
    let value: String

    var body: some View {
        GridRow {
            Text(label)
                .font(.caption)
                .foregroundStyle(.secondary)
                .gridColumnAlignment(.leading)
            Text(value)
                .font(.caption.monospaced())
                .gridColumnAlignment(.leading)
        }
    }
}
