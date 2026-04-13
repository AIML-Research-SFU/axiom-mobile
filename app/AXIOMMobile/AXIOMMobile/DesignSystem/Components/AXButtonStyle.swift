import SwiftUI

/// Primary call-to-action button style — gradient accent fill.
///
/// Usage:
/// ```swift
/// Button("Run Inference") { ... }
///     .buttonStyle(AXPrimaryButtonStyle())
/// ```
struct AXPrimaryButtonStyle: ButtonStyle {

    @Environment(\.isEnabled) private var isEnabled

    func makeBody(configuration: Configuration) -> some View {
        configuration.label
            .font(AXFont.button)
            .foregroundStyle(.white)
            .frame(maxWidth: .infinity)
            .padding(.vertical, 16)
            .background {
                RoundedRectangle(cornerRadius: AXRadius.lg)
                    .fill(
                        LinearGradient(
                            colors: isEnabled
                                ? [
                                    AXColor.accentPrimary,
                                    AXColor.accentSecondary,
                                ]
                                : [
                                    Color.gray.opacity(0.3),
                                    Color.gray.opacity(0.2),
                                ],
                            startPoint: .leading,
                            endPoint: .trailing
                        )
                    )
            }
            .opacity(configuration.isPressed ? 0.85 : 1.0)
            .scaleEffect(configuration.isPressed ? 0.98 : 1.0)
            .animation(AXMotion.quick, value: configuration.isPressed)
    }
}

/// Secondary action button — outlined with accent tint.
///
/// Usage:
/// ```swift
/// Button("Export CSV") { ... }
///     .buttonStyle(AXSecondaryButtonStyle())
/// ```
struct AXSecondaryButtonStyle: ButtonStyle {

    var tintColor: Color = AXColor.accentPrimary

    @Environment(\.isEnabled) private var isEnabled

    func makeBody(configuration: Configuration) -> some View {
        configuration.label
            .font(.subheadline.weight(.medium))
            .foregroundStyle(isEnabled ? tintColor : Color.gray)
            .padding(.horizontal, AXSpacing.lg)
            .padding(.vertical, AXSpacing.sm)
            .background {
                RoundedRectangle(cornerRadius: AXRadius.sm)
                    .fill(tintColor.opacity(isEnabled ? 0.12 : 0.05))
            }
            .overlay {
                RoundedRectangle(cornerRadius: AXRadius.sm)
                    .strokeBorder(
                        tintColor.opacity(isEnabled ? 0.25 : 0.10),
                        lineWidth: AXStroke.hairline
                    )
            }
            .opacity(configuration.isPressed ? 0.75 : 1.0)
    }
}

/// Compact inline action — for destructive or minor actions.
struct AXCompactButtonStyle: ButtonStyle {

    var role: ButtonRole?

    private var tint: Color {
        role == .destructive ? AXColor.statusCritical : AXColor.textSecondary
    }

    func makeBody(configuration: Configuration) -> some View {
        configuration.label
            .font(.caption.weight(.medium))
            .foregroundStyle(tint)
            .padding(.horizontal, AXSpacing.md)
            .padding(.vertical, AXSpacing.xs)
            .background {
                Capsule().fill(tint.opacity(0.10))
            }
            .opacity(configuration.isPressed ? 0.65 : 1.0)
    }
}
