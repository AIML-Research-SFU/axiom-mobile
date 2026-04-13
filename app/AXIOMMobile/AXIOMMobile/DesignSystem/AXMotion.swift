import SwiftUI

/// Animation presets for consistent motion language.
///
/// Respects `accessibilityReduceMotion` — callers should check
/// the environment or use the `axAnimation(_:)` modifier.
enum AXMotion {

    /// Standard interactive transition — card appearances, toggles.
    static let standard: Animation = .smooth(duration: 0.3)

    /// Quick micro-interaction — button feedback, badge changes.
    static let quick: Animation = .smooth(duration: 0.2)

    /// Gentle entrance — results appearing, sections expanding.
    static let gentle: Animation = .smooth(duration: 0.45)

    /// Spring for interactive gestures.
    static let spring: Animation = .spring(duration: 0.4, bounce: 0.15)
}

// MARK: - Reduce-Motion-Aware Modifier

extension View {
    /// Applies animation only when Reduce Motion is off.
    func axAnimation(_ animation: Animation, value: some Equatable) -> some View
    {
        self.modifier(
            ReduceMotionAnimationModifier(animation: animation, value: value)
        )
    }
}

private struct ReduceMotionAnimationModifier<V: Equatable>: ViewModifier {
    let animation: Animation
    let value: V
    @Environment(\.accessibilityReduceMotion) private var reduceMotion

    func body(content: Content) -> some View {
        content.animation(reduceMotion ? nil : animation, value: value)
    }
}
