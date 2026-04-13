import SwiftUI

struct QuestionInputSection: View {
    @Binding var question: String
    var isFocused: FocusState<Bool>.Binding

    var body: some View {
        GlassCard {
            VStack(alignment: .leading, spacing: AXSpacing.md) {
                SectionHeader("Question", icon: "text.bubble")

                TextField(
                    "What app is shown in this screenshot?",
                    text: $question,
                    axis: .vertical
                )
                .focused(isFocused)
                .lineLimit(2...5)
                .font(AXFont.body)
                .padding(AXSpacing.md)
                .background {
                    RoundedRectangle(cornerRadius: AXRadius.sm)
                        .fill(AXColor.glassFill)
                }
                .overlay {
                    RoundedRectangle(cornerRadius: AXRadius.sm)
                        .strokeBorder(
                            isFocused.wrappedValue
                                ? AXColor.accentPrimary.opacity(0.4)
                                : AXColor.glassStroke,
                            lineWidth: isFocused.wrappedValue
                                ? AXStroke.thin : AXStroke.hairline
                        )
                }
                .axAnimation(AXMotion.quick, value: isFocused.wrappedValue)
            }
        }
    }
}
