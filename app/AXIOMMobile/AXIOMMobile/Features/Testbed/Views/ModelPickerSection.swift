import SwiftUI

struct ModelPickerSection: View {
    @Binding var selectedModel: ModelInfo

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            Label("Model", systemImage: "cpu")
                .font(.headline)

            Picker("Model", selection: $selectedModel) {
                ForEach(ModelCatalog.all) { model in
                    Text(model.displayName)
                        .tag(model)
                }
            }
            .pickerStyle(.menu)

            Text("Stage: \(selectedModel.stage) · Backend: \(selectedModel.backend) · \(selectedModel.statusLabel)")
                .font(.caption)
                .foregroundStyle(.secondary)
        }
        .padding()
        .background(.regularMaterial, in: RoundedRectangle(cornerRadius: 16))
    }
}
