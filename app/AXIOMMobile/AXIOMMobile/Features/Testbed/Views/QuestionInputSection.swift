import SwiftUI

struct QuestionInputSection: View {
    @Binding var question: String

    var body: some View {
        GlassCard {
            VStack(alignment: .leading, spacing: AXSpacing.md) {
                SectionHeader("Question", icon: "text.bubble")

                TextField(
                    "What app is shown in this screenshot?",
                    text: $question,
                    axis: .vertical
                )
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
                            AXColor.glassStroke,
                            lineWidth: AXStroke.hairline
                        )
                }
            }
        }
    }
}
