import SwiftUI

struct BenchmarkConfigSection: View {
    @Binding var enabled: Bool
    @Binding var iterations: Int

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            Toggle(isOn: $enabled) {
                Label("Benchmark Mode", systemImage: "timer")
                    .font(.headline)
            }

            if enabled {
                Stepper(value: $iterations, in: 1...50) {
                    Text("Iterations: \(iterations)")
                        .font(.subheadline)
                }

                Text("Runs inference repeatedly and logs latency statistics for export.")
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }
        }
        .padding()
        .background(.regularMaterial, in: RoundedRectangle(cornerRadius: 16))
        .animation(.smooth, value: enabled)
    }
}
