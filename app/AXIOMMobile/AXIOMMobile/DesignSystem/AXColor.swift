import SwiftUI

// MARK: - Semantic Color Tokens

/// Centralized color vocabulary for the AXIOM design system.
///
/// Every feature view consumes these tokens — never raw RGB values.
/// All colors adapt to Light / Dark / High-Contrast automatically
/// via `Color(light:dark:)` or system-provided roles.
enum AXColor {

    // MARK: Accent

    /// Primary interactive accent — buttons, links, active controls.
    static let accentPrimary = Color(
        light: .init(red: 0.20, green: 0.40, blue: 0.95),
        dark: .init(red: 0.35, green: 0.55, blue: 1.0)
    )

    /// Secondary accent for supporting indicators and highlights.
    static let accentSecondary = Color(
        light: .init(red: 0.45, green: 0.30, blue: 0.90),
        dark: .init(red: 0.55, green: 0.45, blue: 1.0)
    )

    /// Subtle glow / emphasis tint for elevated surfaces.
    static let accentGlow = Color(
        light: .init(red: 0.30, green: 0.50, blue: 1.0).opacity(0.15),
        dark: .init(red: 0.35, green: 0.55, blue: 1.0).opacity(0.10)
    )

    // MARK: Background

    /// Canvas / root background.
    static let backgroundBase = Color(
        light: .init(red: 0.95, green: 0.95, blue: 0.97),
        dark: .init(red: 0.04, green: 0.04, blue: 0.06)
    )

    /// Gradient top in dark mode, near-white in light mode.
    static let backgroundGradientTop = Color(
        light: .init(red: 0.96, green: 0.96, blue: 0.98),
        dark: .init(red: 0.06, green: 0.06, blue: 0.10)
    )

    /// Gradient bottom in dark mode, neutral in light mode.
    static let backgroundGradientBottom = Color(
        light: .init(red: 0.93, green: 0.93, blue: 0.95),
        dark: .init(red: 0.02, green: 0.02, blue: 0.04)
    )

    // MARK: Glass

    /// Fill tint for glass cards (additive in dark, subtractive in light).
    static let glassFill = Color(
        light: .init(white: 1.0).opacity(0.70),
        dark: .init(white: 1.0).opacity(0.05)
    )

    /// Stroke for glass card borders.
    static let glassStroke = Color(
        light: .init(white: 0.0).opacity(0.06),
        dark: .init(white: 1.0).opacity(0.08)
    )

    /// Highlight edge on glass cards (top or leading).
    static let glassHighlight = Color(
        light: .init(white: 1.0).opacity(0.90),
        dark: .init(white: 1.0).opacity(0.12)
    )

    // MARK: Text

    /// Primary text — headings, body, values.
    static let textPrimary = Color.primary

    /// Secondary text — captions, subtitles, supporting copy.
    static let textSecondary = Color.secondary

    /// Tertiary text — least-important metadata.
    static let textTertiary = Color(
        light: .init(white: 0.0).opacity(0.30),
        dark: .init(white: 1.0).opacity(0.35)
    )

    // MARK: Status

    /// Success — thresholds met, ready states.
    static let statusSuccess = Color(
        light: .init(red: 0.20, green: 0.70, blue: 0.40),
        dark: .init(red: 0.30, green: 0.85, blue: 0.50)
    )

    /// Warning — partial, attention needed.
    static let statusWarning = Color(
        light: .init(red: 0.90, green: 0.65, blue: 0.15),
        dark: .init(red: 1.0, green: 0.75, blue: 0.25)
    )

    /// Critical — failure, blocked.
    static let statusCritical = Color(
        light: .init(red: 0.90, green: 0.25, blue: 0.20),
        dark: .init(red: 1.0, green: 0.35, blue: 0.30)
    )

    /// Informational — neutral callouts.
    static let statusInfo = Color(
        light: .init(red: 0.30, green: 0.55, blue: 0.85),
        dark: .init(red: 0.45, green: 0.70, blue: 1.0)
    )
}

// MARK: - Adaptive Color Initializer

extension Color {
    /// Creates an adaptive color that resolves to `light` or `dark` variants.
    init(light: Color, dark: Color) {
        self.init(
            uiColor: UIColor { traits in
                traits.userInterfaceStyle == .dark
                    ? UIColor(dark)
                    : UIColor(light)
            }
        )
    }
}
