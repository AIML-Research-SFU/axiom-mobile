import SwiftUI

/// Shape tokens — corner radii and stroke widths.
///
/// Feature views use these instead of hardcoded `cornerRadius:` values.
enum AXRadius {

    /// 8 pt — small elements: badges, chips, inner controls.
    static let sm: CGFloat = 8

    /// 12 pt — medium elements: inner content areas, thumbnails.
    static let md: CGFloat = 12

    /// 16 pt — standard cards.
    static let lg: CGFloat = 16

    /// 20 pt — elevated or hero cards.
    static let xl: CGFloat = 20

    /// 24 pt — hero sections, modal sheets.
    static let xxl: CGFloat = 24
}

/// Stroke widths for borders and separators.
enum AXStroke {

    /// Hairline — glass card borders.
    static let hairline: CGFloat = 0.5

    /// Thin — focused input borders, active states.
    static let thin: CGFloat = 1.0

    /// Medium — emphasized borders.
    static let medium: CGFloat = 1.5
}
