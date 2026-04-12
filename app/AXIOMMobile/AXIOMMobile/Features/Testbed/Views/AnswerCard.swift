import SwiftUI

struct AnswerCard: View {
    let result: InferenceResult

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            Label("Answer", systemImage: "text.bubble")
                .font(.headline)

            Text(result.answer)
                .font(.body)
                .frame(maxWidth: .infinity, alignment: .leading)
                .padding()
                .background(.thinMaterial, in: RoundedRectangle(cornerRadius: 12))

            if result.isPlaceholder {
                Label("Placeholder \u{2014} model not connected", systemImage: "info.circle")
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }
        }
        .padding()
        .background(.regularMaterial, in: RoundedRectangle(cornerRadius: 16))
        .accessibilityElement(children: .combine)
    }
}
