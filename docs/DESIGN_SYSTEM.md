# AXIOM-Mobile Design System v0

Last updated: 2026-04-13

## Design Pillars

1. **Quiet confidence.** The UI communicates credibility through restraint, not ornament. Glass surfaces and subtle gradients provide depth without distraction.
2. **Clear hierarchy.** Hero surfaces (screenshot, answer) are visually elevated. Configuration (model, benchmark) is compact. Debug is collapsible and subordinate.
3. **Accessible by default.** Dynamic Type, VoiceOver labels, Reduce Motion, Reduce Transparency, and High Contrast are supported as first-class citizens, not afterthoughts.
4. **Platform harmony.** The design aligns with Apple Human Interface Guidelines: standard navigation patterns, semantic colors, system materials, and familiar control idioms.

## Token Categories

### Colors (`AXColor`)

Semantic color roles that adapt to Light/Dark/High-Contrast automatically.

| Role | Purpose |
|------|---------|
| `accentPrimary` | Buttons, links, active controls |
| `accentSecondary` | Supporting highlights, gradient endpoints |
| `accentGlow` | Subtle glow tint for elevated surfaces |
| `backgroundBase` | Canvas / root background |
| `backgroundGradientTop/Bottom` | Page gradient endpoints |
| `glassFill` | Glass card fill tint |
| `glassStroke` | Glass card border |
| `glassHighlight` | Top-edge highlight on glass |
| `textPrimary/Secondary/Tertiary` | Three-level text hierarchy |
| `statusSuccess/Warning/Critical/Info` | Semantic status colors |

**Rule:** Feature views never use raw `Color(red:green:blue:)` — always `AXColor.*`.

### Spacing (`AXSpacing`)

4-pt grid scale from `xs` (4pt) to `xxl` (24pt) plus named roles:

| Token | Value | Usage |
|-------|-------|-------|
| `xs` | 4 pt | Icon gaps, badge insets |
| `sm` | 8 pt | Inline elements, compact gaps |
| `md` | 12 pt | Default inner spacing |
| `lg` | 16 pt | Card padding, section gaps |
| `xl` | 20 pt | Hero card padding |
| `xxl` | 24 pt | Between major sections |
| `cardPadding` | 16 pt | Standard card internal padding |
| `heroPadding` | 20 pt | Hero card internal padding |
| `sectionGap` | 16 pt | Between section cards |
| `pageMargin` | 20 pt | Horizontal page margin |

### Shapes (`AXRadius`, `AXStroke`)

| Radius | Value | Usage |
|--------|-------|-------|
| `sm` | 8 pt | Badges, chips, inner controls |
| `md` | 12 pt | Thumbnails, inner content |
| `lg` | 16 pt | Standard cards |
| `xl` | 20 pt | Hero and elevated cards |
| `xxl` | 24 pt | Modals, hero sections |

| Stroke | Value | Usage |
|--------|-------|-------|
| `hairline` | 0.5 pt | Glass card borders |
| `thin` | 1.0 pt | Focused inputs |
| `medium` | 1.5 pt | Emphasized borders |

### Typography (`AXFont`)

Maps to Dynamic Type styles — never fixed point sizes:

| Role | Style | Usage |
|------|-------|-------|
| `pageTitle` | `.largeTitle.bold` | Screen title |
| `sectionTitle` | `.subheadline.semibold` | Card headers |
| `body` | `.body` | Content text |
| `caption` | `.caption` | Metadata, hints |
| `mono` | `.caption.monospaced` | Model IDs, metrics |
| `button` | `.body.semibold` | CTA labels |
| `badge` | `.caption2.medium` | Status chips |
| `modelName` | `.subheadline.medium` | Model picker |

### Motion (`AXMotion`)

Respects `accessibilityReduceMotion` via the `axAnimation(_:value:)` modifier:

| Preset | Duration | Usage |
|--------|----------|-------|
| `standard` | 0.3s | Card transitions, toggles |
| `quick` | 0.2s | Button feedback |
| `gentle` | 0.45s | Results appearing |
| `spring` | 0.4s, bounce 0.15 | Interactive gestures |

### Elevation (`AXElevation`)

Shadow presets applied via `.axShadow()`:

| Level | Usage |
|-------|-------|
| `none` | Flat surfaces |
| `low` | Standard cards |
| `medium` | Elevated cards, answer |
| `high` | Modals, hero CTA |
| `glow` | Accent-tinted glow for active states |

## Reusable Components

### `GlassCard`

The primary container. Three hierarchy levels:

| Level | Material | Radius | Padding | Usage |
|-------|----------|--------|---------|-------|
| `.hero` | ultraThin | 20 pt | 20 pt | Screenshot, answer |
| `.standard` | ultraThin | 16 pt | 16 pt | Question, model, benchmark results |
| `.subdued` | ultraThin | 12 pt | 12 pt | Debug, benchmark config |

Features:
- Gradient stroke border (highlight at top-leading, subtle at bottom-trailing)
- Adaptive fill (glass in normal mode, opaque in Reduce Transparency)
- Consistent corner radius per level

### `AXPrimaryButtonStyle`

Gradient-filled CTA with accent colors. Disabled state shows gray gradient. Press effect: scale to 98% + opacity 85%.

### `AXSecondaryButtonStyle`

Outlined button with tinted fill. Configurable `tintColor` for contextual actions (export, save).

### `AXCompactButtonStyle`

Capsule-shaped inline button for minor/destructive actions. Minimal visual weight.

### `StatusBadge`

Pill-shaped status indicator with 5 variants (success, warning, critical, info, neutral). Optional icon. Used for model status, latency values, run counts.

### `SectionHeader`

Consistent icon + title label for card headers. Configurable tint color.

## Accessibility Behavior

| Feature | Approach |
|---------|----------|
| Dynamic Type | All typography uses system text styles; no fixed sizes |
| VoiceOver | All interactive elements have labels; cards use `.accessibilityElement(children: .combine)` where appropriate |
| Reduce Motion | `axAnimation(_:value:)` suppresses animation when enabled |
| Reduce Transparency | `GlassCard` falls back to opaque fills when enabled |
| High Contrast | Colors use `Color(light:dark:)` which UIKit auto-adjusts for accessibility contrast |
| Touch targets | All buttons have at least 44pt touch area via padding |

## How Feature Views Consume the Design System

### Do

```swift
// Use semantic tokens
Text(title).font(AXFont.sectionTitle)
    .foregroundStyle(AXColor.textPrimary)

// Use GlassCard for containers
GlassCard(.standard) {
    SectionHeader("Title", icon: "star")
    // content
}

// Use design-system button styles
Button("Action") { }
    .buttonStyle(AXPrimaryButtonStyle())

// Use spacing tokens
VStack(spacing: AXSpacing.md) { }
```

### Don't

```swift
// Don't use magic numbers
.padding(16)                    // Use AXSpacing.lg
.cornerRadius(12)               // Use AXRadius.md

// Don't use raw colors
.foregroundColor(.gray)          // Use AXColor.textSecondary
Color(red: 0.3, green: 0.5, blue: 1.0)  // Use AXColor.accentPrimary

// Don't use raw materials directly
.background(.regularMaterial, in: RoundedRectangle(cornerRadius: 16))
// Use GlassCard(.standard) { }
```

## Extension Points

- **New card types:** Create a new `GlassCard.Level` if the existing three don't fit.
- **New status variants:** Add to `StatusBadge.Variant`.
- **New color roles:** Add to `AXColor` — never inline raw colors.
- **New motion presets:** Add to `AXMotion`.
- **Theming:** The `Color(light:dark:)` initializer can be extended to support custom themes if needed later.
