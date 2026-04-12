import SwiftUI

struct BenchmarkSummaryCard: View {
    let recordCount: Int
    let averageLatencyMs: Double
    let minLatencyMs: Int
    let maxLatencyMs: Int
    let modelID: String?
    let hasExported: Bool
    let exportURL: URL?
    let metadataURL: URL?
    let onExport: () -> Void
    let onClear: () -> Void

    private var shareItems: [URL] {
        [exportURL, metadataURL].compactMap { $0 }
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            Label("Benchmark Summary", systemImage: "chart.bar")
                .font(.headline)

            Grid(alignment: .leading, horizontalSpacing: 12, verticalSpacing: 8) {
                SummaryRow(label: "Runs", value: "\(recordCount)")
                SummaryRow(label: "Avg Latency", value: "\(Int(averageLatencyMs)) ms")
                SummaryRow(label: "Min Latency", value: "\(minLatencyMs) ms")
                SummaryRow(label: "Max Latency", value: "\(maxLatencyMs) ms")
                if let modelID {
                    SummaryRow(label: "Model", value: modelID)
                }
                SummaryRow(label: "Exported", value: hasExported ? "Yes" : "No")
            }

            HStack(spacing: 12) {
                Button {
                    onExport()
                } label: {
                    Label("Export CSV", systemImage: "square.and.arrow.up")
                }
                .buttonStyle(.bordered)

                if !shareItems.isEmpty {
                    ShareLink(items: shareItems) {
                        Label("Share", systemImage: "paperplane")
                    }
                    .buttonStyle(.bordered)
                }

                Spacer()

                Button(role: .destructive) {
                    onClear()
                } label: {
                    Label("Clear", systemImage: "trash")
                }
                .buttonStyle(.bordered)
            }
        }
        .padding()
        .background(.regularMaterial, in: RoundedRectangle(cornerRadius: 16))
        .accessibilityElement(children: .combine)
    }
}

private struct SummaryRow: View {
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
