import SwiftUI

/// A compact status pill / chip for model state, environment labels, etc.
///
/// Usage:
/// ```swift
/// StatusBadge("Core ML Ready", variant: .success)
/// StatusBadge("Simulator", variant: .info)
/// StatusBadge("Blocked", variant: .critical)
/// ```
struct StatusBadge: View {

    let text: String
    let variant: Variant
    var icon: String?

    init(_ text: String, variant: Variant, icon: String? = nil) {
        self.text = text
        self.variant = variant
        self.icon = icon
    }

    var body: some View {
        HStack(spacing: AXSpacing.xs) {
            if let icon {
                Image(systemName: icon)
                    .font(.system(size: 9, weight: .bold))
            }

            Text(text)
        }
        .font(AXFont.badge)
        .foregroundStyle(variant.foreground)
        .padding(.horizontal, AXSpacing.sm)
        .padding(.vertical, AXSpacing.xs)
        .background(variant.background, in: Capsule())
        .accessibilityLabel("\(text) status")
    }
}

extension StatusBadge {

    enum Variant {
        case success
        case warning
        case critical
        case info
        case neutral

        var foreground: Color {
            switch self {
            case .success: AXColor.statusSuccess
            case .warning: AXColor.statusWarning
            case .critical: AXColor.statusCritical
            case .info: AXColor.statusInfo
            case .neutral: AXColor.textSecondary
            }
        }

        var background: Color {
            switch self {
            case .success: AXColor.statusSuccess.opacity(0.15)
            case .warning: AXColor.statusWarning.opacity(0.15)
            case .critical: AXColor.statusCritical.opacity(0.15)
            case .info: AXColor.statusInfo.opacity(0.15)
            case .neutral: AXColor.textTertiary.opacity(0.15)
            }
        }
    }
}
