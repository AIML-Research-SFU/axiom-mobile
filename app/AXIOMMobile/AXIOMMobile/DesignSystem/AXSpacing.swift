import Foundation

/// Spacing scale for consistent layout rhythm.
///
/// Based on a 4-pt grid. Feature views should only use these
/// values — never ad-hoc numbers.
enum AXSpacing {

    /// 4 pt — tight inner padding (icon gaps, badge insets).
    static let xs: CGFloat = 4

    /// 8 pt — compact spacing (inline elements, small gaps).
    static let sm: CGFloat = 8

    /// 12 pt — default inner spacing within cards.
    static let md: CGFloat = 12

    /// 16 pt — standard card padding, section gaps.
    static let lg: CGFloat = 16

    /// 20 pt — generous card padding for hero surfaces.
    static let xl: CGFloat = 20

    /// 24 pt — between cards / major sections.
    static let xxl: CGFloat = 24

    /// Card internal padding.
    static let cardPadding: CGFloat = 16

    /// Hero card internal padding.
    static let heroPadding: CGFloat = 20

    /// Gap between section cards.
    static let sectionGap: CGFloat = 16

    /// Page-level horizontal margin.
    static let pageMargin: CGFloat = 20
}
