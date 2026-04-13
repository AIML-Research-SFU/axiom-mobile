import SwiftUI

/// Consistent section header with icon and title.
///
/// Usage:
/// ```swift
/// SectionHeader("Screenshot", icon: "photo.on.rectangle.angled")
/// ```
struct SectionHeader: View {

    let title: String
    let icon: String
    var tint: Color = AXColor.accentPrimary

    init(_ title: String, icon: String, tint: Color = AXColor.accentPrimary) {
        self.title = title
        self.icon = icon
        self.tint = tint
    }

    var body: some View {
        Label {
            Text(title)
                .font(AXFont.sectionTitle)
                .foregroundStyle(AXColor.textPrimary)
        } icon: {
            Image(systemName: icon)
                .font(.system(size: 13, weight: .semibold))
                .foregroundStyle(tint)
        }
    }
}
