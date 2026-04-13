import SwiftUI

struct AnswerCard: View {
    let result: InferenceResult

    var body: some View {
        GlassCard(.hero) {
            VStack(alignment: .leading, spacing: AXSpacing.md) {
                HStack {
                    SectionHeader(
                        "Answer",
                        icon: "sparkles",
                        tint: AXColor.accentSecondary
                    )
                    Spacer()
                    latencyBadge
                }

                Text(result.answer)
                    .font(.title3.weight(.medium))
                    .foregroundStyle(AXColor.textPrimary)
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .padding(AXSpacing.lg)
                    .background {
                        RoundedRectangle(cornerRadius: AXRadius.md)
                            .fill(
                                LinearGradient(
                                    colors: [
                                        AXColor.accentPrimary.opacity(0.08),
                                        AXColor.accentSecondary.opacity(0.04),
                                    ],
                                    startPoint: .topLeading,
                                    endPoint: .bottomTrailing
                                )
                            )
                    }
                    .overlay {
                        RoundedRectangle(cornerRadius: AXRadius.md)
                            .strokeBorder(
                                AXColor.accentPrimary.opacity(0.15),
                                lineWidth: AXStroke.hairline
                            )
                    }

                if result.isPlaceholder {
                    StatusBadge(
                        "Placeholder \u{2014} model not connected",
                        variant: .warning,
                        icon: "info.circle"
                    )
                }
            }
        }
        .axShadow(AXElevation.medium)
        .accessibilityElement(children: .combine)
    }

    private var latencyBadge: some View {
        let ms = Int(result.latencySeconds * 1000)
        return StatusBadge(
            "\(ms) ms",
            variant: ms < 400 ? .success : .warning,
            icon: "bolt.fill"
        )
    }
}
