import PhotosUI
import SwiftUI

struct ScreenshotSection: View {
    @Binding var selectedItem: PhotosPickerItem?
    let image: UIImage?
    let onClear: () -> Void
    var onSaveAsBenchmarkInput: (() -> Void)?

    var body: some View {
        GlassCard(.hero) {
            VStack(alignment: .leading, spacing: AXSpacing.md) {
                SectionHeader("Screenshot", icon: "photo.on.rectangle.angled")

                if let image {
                    loadedImageView(image)
                } else {
                    emptyState
                }

                actionButtons
            }
        }
    }

    // MARK: - Loaded Image

    private func loadedImageView(_ image: UIImage) -> some View {
        Image(uiImage: image)
            .resizable()
            .scaledToFit()
            .frame(maxHeight: 220)
            .clipShape(RoundedRectangle(cornerRadius: AXRadius.md))
            .overlay {
                RoundedRectangle(cornerRadius: AXRadius.md)
                    .strokeBorder(
                        AXColor.glassStroke,
                        lineWidth: AXStroke.hairline
                    )
            }
            .overlay(alignment: .topTrailing) {
                Button("Remove", systemImage: "xmark.circle.fill") {
                    onClear()
                }
                .labelStyle(.iconOnly)
                .buttonStyle(.plain)
                .foregroundStyle(.white)
                .font(.title3)
                .axShadow(AXElevation.low)
                .padding(AXSpacing.sm)
            }
            .accessibilityLabel(
                "Selected screenshot, \(Int(image.size.width)) by \(Int(image.size.height)) pixels"
            )
    }

    // MARK: - Empty State

    private var emptyState: some View {
        RoundedRectangle(cornerRadius: AXRadius.md)
            .fill(AXColor.glassFill)
            .frame(height: 120)
            .overlay {
                VStack(spacing: AXSpacing.sm) {
                    Image(systemName: "photo.badge.plus")
                        .font(.system(size: 28, weight: .light))
                        .foregroundStyle(AXColor.textTertiary)
                    Text("No screenshot selected")
                        .font(AXFont.caption)
                        .foregroundStyle(AXColor.textTertiary)
                }
            }
            .overlay {
                RoundedRectangle(cornerRadius: AXRadius.md)
                    .strokeBorder(
                        AXColor.glassStroke,
                        style: StrokeStyle(
                            lineWidth: AXStroke.thin,
                            dash: [6, 4]
                        )
                    )
            }
    }

    // MARK: - Actions

    private var actionButtons: some View {
        HStack(spacing: AXSpacing.sm) {
            PhotosPicker(selection: $selectedItem, matching: .images) {
                Label(
                    image == nil ? "Select Screenshot" : "Change",
                    systemImage: "photo.badge.plus"
                )
            }
            .buttonStyle(AXSecondaryButtonStyle())

            if image != nil, let onSave = onSaveAsBenchmarkInput {
                Button {
                    onSave()
                } label: {
                    Label(
                        "Save for Benchmark",
                        systemImage: "square.and.arrow.down"
                    )
                }
                .buttonStyle(
                    AXSecondaryButtonStyle(tintColor: AXColor.statusWarning)
                )
                .accessibilityHint(
                    "Persists this screenshot for repeatable auto-benchmark profiling sessions"
                )
            }
        }
    }
}
