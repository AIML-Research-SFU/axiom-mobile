import SwiftUI

/// Semantic typography roles.
///
/// These map to Dynamic Type styles and never use fixed point sizes.
/// Feature views use `AXFont.sectionTitle` instead of `.font(.headline)`.
enum AXFont {

    /// Page title — "AXIOM Testbed".
    static let pageTitle: Font = .largeTitle.weight(.bold)

    /// Section header inside a card — "Screenshot", "Question".
    static let sectionTitle: Font = .subheadline.weight(.semibold)

    /// Body text — answer content, descriptions.
    static let body: Font = .body

    /// Supporting caption — metadata, hints.
    static let caption: Font = .caption

    /// Monospaced caption — metrics, model IDs, latency values.
    static let mono: Font = .caption.monospaced()

    /// Button label.
    static let button: Font = .body.weight(.semibold)

    /// Small label — badge text, status chips.
    static let badge: Font = .caption2.weight(.medium)

    /// Model name in picker.
    static let modelName: Font = .subheadline.weight(.medium)
}
