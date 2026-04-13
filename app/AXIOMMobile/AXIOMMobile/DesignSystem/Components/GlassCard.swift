import SwiftUI

/// A glass-material card container with semantic hierarchy levels.
///
/// Usage:
/// ```swift
/// GlassCard(.primary) {
///     Text("Content")
/// }
/// ```
///
/// Respects Reduce Transparency by falling back to opaque fills.
struct GlassCard<Content: View>: View {

    let level: Level
    @ViewBuilder let content: () -> Content

    @Environment(\.accessibilityReduceTransparency) private
        var reduceTransparency
    @Environment(\.colorScheme) private var colorScheme

    init(
        _ level: Level = .standard,
        @ViewBuilder content: @escaping () -> Content
    ) {
        self.level = level
        self.content = content
    }

    var body: some View {
        content()
            .padding(level.padding)
            .background {
                if reduceTransparency {
                    RoundedRectangle(cornerRadius: level.radius)
                        .fill(opaqueFill)
                } else {
                    RoundedRectangle(cornerRadius: level.radius)
                        .fill(level.material)
                        .overlay {
                            RoundedRectangle(cornerRadius: level.radius)
                                .fill(AXColor.glassFill)
                        }
                }
            }
            .overlay {
                RoundedRectangle(cornerRadius: level.radius)
                    .strokeBorder(
                        LinearGradient(
                            colors: [
                                AXColor.glassHighlight,
                                AXColor.glassStroke,
                            ],
                            startPoint: .topLeading,
                            endPoint: .bottomTrailing
                        ),
                        lineWidth: AXStroke.hairline
                    )
            }
            .clipShape(RoundedRectangle(cornerRadius: level.radius))
    }

    private var opaqueFill: Color {
        colorScheme == .dark
            ? Color(white: 0.12)
            : Color(white: 0.94)
    }
}

// MARK: - Hierarchy Levels

extension GlassCard {

    /// Visual hierarchy level for card containers.
    enum Level {
        /// Hero / primary content (screenshot, answer).
        case hero
        /// Standard section card.
        case standard
        /// Compact or subordinate card (debug, metadata).
        case subdued

        var material: Material {
            switch self {
            case .hero: .ultraThinMaterial
            case .standard: .ultraThinMaterial
            case .subdued: .ultraThinMaterial
            }
        }

        var radius: CGFloat {
            switch self {
            case .hero: AXRadius.xl
            case .standard: AXRadius.lg
            case .subdued: AXRadius.md
            }
        }

        var padding: CGFloat {
            switch self {
            case .hero: AXSpacing.heroPadding
            case .standard: AXSpacing.cardPadding
            case .subdued: AXSpacing.md
            }
        }
    }
}
