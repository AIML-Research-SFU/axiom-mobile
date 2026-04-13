import SwiftUI

struct ModelPickerSection: View {
    @Binding var selectedModel: ModelInfo

    var body: some View {
        GlassCard {
            VStack(alignment: .leading, spacing: AXSpacing.md) {
                HStack {
                    SectionHeader("Model", icon: "cpu")
                    Spacer()
                    StatusBadge(
                        selectedModel.statusLabel,
                        variant: statusVariant,
                        icon: statusIcon
                    )
                }

                Picker("Model", selection: $selectedModel) {
                    ForEach(ModelCatalog.all) { model in
                        Text(model.displayName)
                            .tag(model)
                    }
                }
                .pickerStyle(.menu)
                .font(AXFont.modelName)
                .tint(AXColor.accentPrimary)

                HStack(spacing: AXSpacing.sm) {
                    metadataChip(selectedModel.stage)
                    metadataChip(selectedModel.backend)
                }
            }
        }
    }

    private var statusVariant: StatusBadge.Variant {
        if selectedModel.isCoreMLReady { return .success }
        if selectedModel.isExecutable { return .info }
        return .neutral
    }

    private var statusIcon: String {
        if selectedModel.isCoreMLReady { return "checkmark.circle.fill" }
        if selectedModel.isExecutable { return "play.circle" }
        return "circle.dashed"
    }

    private func metadataChip(_ text: String) -> some View {
        Text(text)
            .font(AXFont.badge)
            .foregroundStyle(AXColor.textTertiary)
            .padding(.horizontal, AXSpacing.sm)
            .padding(.vertical, AXSpacing.xs)
            .background {
                Capsule().fill(AXColor.textTertiary.opacity(0.12))
            }
    }
}
