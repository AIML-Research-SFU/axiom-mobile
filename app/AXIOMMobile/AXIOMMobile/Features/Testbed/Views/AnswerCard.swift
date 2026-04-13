import SwiftUI

struct AnswerCard: View {
    let result: InferenceResult

    @State private var appeared = false

    var body: some View {
        GlassCard(.hero) {
            VStack(alignment: .leading, spacing: AXSpacing.md) {
                headerRow

                if result.isLowConfidence {
                    lowConfidenceContent
                } else {
                    confidentContent
                }

                footerDisclaimer
            }
        }
        .axShadow(appeared ? AXElevation.medium : AXElevation.none)
        .scaleEffect(appeared ? 1.0 : 0.97)
        .onAppear {
            withAnimation(AXMotion.gentle) {
                appeared = true
            }
        }
        .accessibilityElement(children: .combine)
    }

    // MARK: - Header

    private var headerRow: some View {
        HStack {
            SectionHeader(
                "Answer",
                icon: result.isLowConfidence ? "questionmark.diamond" : "sparkles",
                tint: result.isLowConfidence ? AXColor.statusWarning : AXColor.accentSecondary
            )
            Spacer()
            latencyBadge
        }
    }

    // MARK: - Confident Result

    private var confidentContent: some View {
        VStack(alignment: .leading, spacing: AXSpacing.sm) {
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

            if let confidence = result.confidence {
                confidenceBadge(confidence)
            }
        }
    }

    // MARK: - Low Confidence Result

    private var lowConfidenceContent: some View {
        VStack(alignment: .leading, spacing: AXSpacing.sm) {
            HStack(spacing: AXSpacing.sm) {
                Image(systemName: "exclamationmark.triangle.fill")
                    .foregroundStyle(AXColor.statusWarning)
                    .font(.title3)
                Text("Unsupported question")
                    .font(.title3.weight(.medium))
                    .foregroundStyle(AXColor.textPrimary)
            }
            .frame(maxWidth: .infinity, alignment: .leading)
            .padding(AXSpacing.lg)
            .background {
                RoundedRectangle(cornerRadius: AXRadius.md)
                    .fill(AXColor.statusWarning.opacity(0.08))
            }
            .overlay {
                RoundedRectangle(cornerRadius: AXRadius.md)
                    .strokeBorder(
                        AXColor.statusWarning.opacity(0.20),
                        lineWidth: AXStroke.thin
                    )
            }

            Text(
                "This model's 24-class vocabulary does not cover the asked question. "
                + "Try questions like \u{201c}Is Bluetooth on or off?\u{201d} or "
                + "\u{201c}What battery percentage is shown?\u{201d}"
            )
            .font(AXFont.caption)
            .foregroundStyle(AXColor.textSecondary)
            .frame(maxWidth: .infinity, alignment: .leading)

            if let confidence = result.confidence {
                confidenceBadge(confidence)
            }
        }
        .accessibilityLabel(
            "Unsupported question. Model confidence is too low to provide a meaningful answer."
        )
    }

    // MARK: - Footer Disclaimer

    @ViewBuilder
    private var footerDisclaimer: some View {
        if result.isPlaceholder {
            StatusBadge(
                "Placeholder \u{2014} model not connected",
                variant: .warning,
                icon: "info.circle"
            )
        } else if result.modelID == "tiny_multimodal_v0", !result.isLowConfidence {
            Text(
                "This model classifies mobile app screenshots into a fixed set of 24 answer categories. Results on non-screenshot images or open-ended questions may not be meaningful."
            )
            .font(AXFont.caption)
            .foregroundStyle(AXColor.textTertiary)
            .frame(maxWidth: .infinity, alignment: .leading)
        }
    }

    // MARK: - Badges

    private var latencyBadge: some View {
        let ms = Int(result.latencySeconds * 1000)
        return StatusBadge(
            "\(ms) ms",
            variant: ms < 400 ? .success : .warning,
            icon: "bolt.fill"
        )
    }

    private func confidenceBadge(_ confidence: Double) -> some View {
        let percent = Int(confidence * 100)
        let variant: StatusBadge.Variant = result.isLowConfidence ? .warning : .info
        return StatusBadge(
            "\(percent)% confidence",
            variant: variant,
            icon: result.isLowConfidence ? "exclamationmark.triangle" : "chart.bar"
        )
    }
}
