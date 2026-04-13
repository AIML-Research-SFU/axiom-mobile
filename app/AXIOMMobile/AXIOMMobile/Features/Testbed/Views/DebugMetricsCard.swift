import SwiftUI

struct DebugMetricsCard: View {
    let selectedModel: ModelInfo
    let imageStatus: String
    let questionLength: Int
    let result: InferenceResult?

    @State private var isExpanded = false

    var body: some View {
        GlassCard(.subdued) {
            VStack(alignment: .leading, spacing: AXSpacing.sm) {
                Button {
                    withAnimation(AXMotion.standard) {
                        isExpanded.toggle()
                    }
                } label: {
                    HStack {
                        SectionHeader(
                            "Debug",
                            icon: "ant",
                            tint: AXColor.textTertiary
                        )
                        Spacer()
                        Image(systemName: "chevron.right")
                            .font(.caption2.weight(.semibold))
                            .foregroundStyle(AXColor.textTertiary)
                            .rotationEffect(.degrees(isExpanded ? 90 : 0))
                    }
                    .contentShape(Rectangle())
                }
                .buttonStyle(.plain)
                .accessibilityHint(
                    isExpanded
                        ? "Collapse debug details" : "Expand debug details"
                )

                if isExpanded {
                    metricsGrid
                        .transition(.opacity.combined(with: .move(edge: .top)))
                }
            }
        }
    }

    private var metricsGrid: some View {
        Grid(
            alignment: .leading,
            horizontalSpacing: AXSpacing.md,
            verticalSpacing: AXSpacing.sm
        ) {
            MetricRow(label: "Model ID", value: selectedModel.id)
            MetricRow(label: "Status", value: selectedModel.statusLabel)
            MetricRow(label: "Image", value: imageStatus)
            MetricRow(label: "Question", value: "\(questionLength) characters")

            if let result {
                let ms = Int(result.latencySeconds * 1000)
                MetricRow(label: "Latency", value: "\(ms) ms")
                MetricRow(
                    label: "Inference",
                    value: result.isPlaceholder ? "Placeholder" : "Live"
                )
                if let confidence = result.confidence {
                    MetricRow(
                        label: "Confidence",
                        value: String(format: "%.1f%%", confidence * 100)
                    )
                }
                if result.isLowConfidence {
                    MetricRow(label: "Status", value: "Low confidence")
                }
            }
        }
    }
}

// MARK: - Metric Row

private struct MetricRow: View {
    let label: String
    let value: String

    var body: some View {
        GridRow {
            Text(label)
                .font(AXFont.caption)
                .foregroundStyle(AXColor.textTertiary)
                .gridColumnAlignment(.leading)
            Text(value)
                .font(AXFont.mono)
                .foregroundStyle(AXColor.textSecondary)
                .gridColumnAlignment(.leading)
        }
    }
}
