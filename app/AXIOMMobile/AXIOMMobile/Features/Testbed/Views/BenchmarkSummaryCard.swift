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
        GlassCard {
            VStack(alignment: .leading, spacing: AXSpacing.md) {
                HStack {
                    SectionHeader(
                        "Benchmark Results",
                        icon: "chart.bar",
                        tint: AXColor.statusInfo
                    )
                    Spacer()
                    StatusBadge(
                        "\(recordCount) runs",
                        variant: .info,
                        icon: "number"
                    )
                }

                metricsGrid

                actionRow
            }
        }
        .accessibilityElement(children: .combine)
    }

    // MARK: - Metrics

    private var metricsGrid: some View {
        HStack(spacing: AXSpacing.md) {
            metricTile(
                label: "Avg",
                value: "\(Int(averageLatencyMs))",
                unit: "ms"
            )
            metricTile(label: "Min", value: "\(minLatencyMs)", unit: "ms")
            metricTile(label: "Max", value: "\(maxLatencyMs)", unit: "ms")
        }
    }

    private func metricTile(label: String, value: String, unit: String)
        -> some View
    {
        VStack(spacing: AXSpacing.xs) {
            Text(label)
                .font(AXFont.badge)
                .foregroundStyle(AXColor.textTertiary)
            HStack(alignment: .firstTextBaseline, spacing: 2) {
                Text(value)
                    .font(.title3.weight(.semibold).monospacedDigit())
                    .foregroundStyle(AXColor.textPrimary)
                Text(unit)
                    .font(AXFont.badge)
                    .foregroundStyle(AXColor.textTertiary)
            }
        }
        .frame(maxWidth: .infinity)
        .padding(.vertical, AXSpacing.sm)
        .background {
            RoundedRectangle(cornerRadius: AXRadius.sm)
                .fill(AXColor.glassFill)
        }
    }

    // MARK: - Actions

    private var actionRow: some View {
        HStack(spacing: AXSpacing.sm) {
            Button {
                onExport()
            } label: {
                Label("Export", systemImage: "square.and.arrow.up")
            }
            .buttonStyle(AXSecondaryButtonStyle(tintColor: AXColor.statusInfo))

            if !shareItems.isEmpty {
                ShareLink(items: shareItems) {
                    Label("Share", systemImage: "paperplane")
                }
                .buttonStyle(AXSecondaryButtonStyle())
            }

            Spacer()

            Button(role: .destructive) {
                onClear()
            } label: {
                Label("Clear", systemImage: "trash")
            }
            .buttonStyle(AXCompactButtonStyle(role: .destructive))
        }
    }
}
