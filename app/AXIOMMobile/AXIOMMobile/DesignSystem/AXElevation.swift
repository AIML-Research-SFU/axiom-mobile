import SwiftUI

/// Elevation tokens for shadow and depth layering.
///
/// In dark mode, shadows are subtle (near-black on black).
/// In light mode, shadows provide depth cues.
enum AXElevation {

    /// No elevation — flat surfaces.
    static let none: AXShadow = .init(color: .clear, radius: 0, y: 0)

    /// Low — standard cards resting on the canvas.
    static let low: AXShadow = .init(
        color: Color.black.opacity(0.15),
        radius: 8,
        y: 2
    )

    /// Medium — elevated cards, active states.
    static let medium: AXShadow = .init(
        color: Color.black.opacity(0.20),
        radius: 16,
        y: 4
    )

    /// High — modals, hero sections, primary CTA.
    static let high: AXShadow = .init(
        color: Color.black.opacity(0.30),
        radius: 24,
        y: 8
    )

    /// Glow — accent-tinted upward glow for CTA / active states.
    static let glow: AXShadow = .init(
        color: AXColor.accentPrimary.opacity(0.30),
        radius: 20,
        y: 0
    )
}

/// A shadow specification that can be applied via `.axShadow()`.
struct AXShadow {
    let color: Color
    let radius: CGFloat
    let y: CGFloat
}

extension View {
    /// Applies a design-system shadow.
    func axShadow(_ shadow: AXShadow) -> some View {
        self.shadow(color: shadow.color, radius: shadow.radius, y: shadow.y)
    }
}
