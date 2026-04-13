import XCTest

/// XCUITest-based screenshot capture for AXIOM-Mobile dataset generation.
///
/// These tests launch system apps on the iOS Simulator, navigate to
/// specific screens, and capture pixel-perfect screenshots for the
/// research dataset. Each test method represents one capture scenario.
///
/// ## Running
///
/// From Xcode: Select the `AXIOMMobileUITests` scheme, pick a simulator,
/// and run the test plan.
///
/// From CLI:
/// ```bash
/// xcodebuild test \
///   -project app/AXIOMMobile/AXIOMMobile.xcodeproj \
///   -scheme AXIOMMobileUITests \
///   -destination 'platform=iOS Simulator,name=iPhone 17 Pro' \
///   -only-testing:AXIOMMobileUITests/ScreenshotCaptureTests
/// ```
///
/// ## Output
///
/// Screenshots are saved to `~/Datasets/axiom-mobile/xctest_captures/`
/// with a JSONL index for downstream processing.
final class ScreenshotCaptureTests: XCTestCase {

    // MARK: - Configuration

    /// Output directory for captured screenshots.
    /// Reads from `AXIOM_CAPTURE_DIR` environment variable,
    /// or defaults to ~/Datasets/axiom-mobile/xctest_captures/
    private var outputDir: URL {
        if let envPath = ProcessInfo.processInfo.environment["AXIOM_CAPTURE_DIR"] {
            return URL(filePath: envPath)
        }
        return URL.homeDirectory
            .appending(path: "Datasets/axiom-mobile/xctest_captures")
    }

    private var indexFileURL: URL {
        outputDir.appending(path: "capture_index.jsonl")
    }

    override func setUp() {
        super.setUp()
        continueAfterFailure = true

        // Create output directory
        try? FileManager.default.createDirectory(
            at: outputDir,
            withIntermediateDirectories: true
        )
    }

    // MARK: - Settings App Scenarios

    func testSettingsMainScreen() {
        let settings = XCUIApplication(bundleIdentifier: "com.apple.Preferences")
        settings.launch()
        sleep(2)

        captureScreen(
            scenarioID: "xctest_settings_main",
            screenFamily: "settings",
            description: "Settings app main screen",
            qaTemplates: [
                QATemplate(question: "Is Airplane Mode on or off?", answerHint: "Check toggle", difficulty: 1),
                QATemplate(question: "Is Wi-Fi on or off?", answerHint: "Check subtitle", difficulty: 1),
                QATemplate(question: "Is Bluetooth on or off?", answerHint: "Check subtitle", difficulty: 1),
            ],
            notes: "iOS Settings main screen"
        )
    }

    func testSettingsWiFi() {
        let settings = XCUIApplication(bundleIdentifier: "com.apple.Preferences")
        settings.launch()
        sleep(1)

        // Navigate to Wi-Fi
        let wifiCell = settings.cells.containing(.staticText, identifier: "Wi-Fi").firstMatch
        if wifiCell.waitForExistence(timeout: 5) {
            wifiCell.tap()
            sleep(2)

            captureScreen(
                scenarioID: "xctest_settings_wifi",
                screenFamily: "settings_wifi",
                description: "Settings > Wi-Fi screen",
                qaTemplates: [
                    QATemplate(question: "Is Wi-Fi on or off?", answerHint: "Check toggle", difficulty: 1),
                    QATemplate(question: "What is the Wi-Fi network name shown?", answerHint: "Read network name", difficulty: 1),
                ],
                notes: "iOS Settings → Wi-Fi"
            )
        }
    }

    func testSettingsBluetooth() {
        let settings = XCUIApplication(bundleIdentifier: "com.apple.Preferences")
        settings.launch()
        sleep(1)

        let btCell = settings.cells.containing(.staticText, identifier: "Bluetooth").firstMatch
        if btCell.waitForExistence(timeout: 5) {
            btCell.tap()
            sleep(2)

            captureScreen(
                scenarioID: "xctest_settings_bluetooth",
                screenFamily: "settings_bluetooth",
                description: "Settings > Bluetooth screen",
                qaTemplates: [
                    QATemplate(question: "Is Bluetooth on or off?", answerHint: "Check toggle", difficulty: 1),
                ],
                notes: "iOS Bluetooth settings"
            )
        }
    }

    func testSettingsBattery() {
        let settings = XCUIApplication(bundleIdentifier: "com.apple.Preferences")
        settings.launch()
        sleep(1)

        // Scroll down to find Battery
        let batteryCell = settings.cells.containing(.staticText, identifier: "Battery").firstMatch
        if batteryCell.waitForExistence(timeout: 3) {
            batteryCell.tap()
        } else {
            settings.swipeUp()
            sleep(1)
            if batteryCell.waitForExistence(timeout: 3) {
                batteryCell.tap()
            } else {
                return // Battery cell not found
            }
        }
        sleep(2)

        captureScreen(
            scenarioID: "xctest_settings_battery",
            screenFamily: "settings_battery",
            description: "Settings > Battery screen",
            qaTemplates: [
                QATemplate(question: "Is Low Power Mode on or off?", answerHint: "Check toggle", difficulty: 2),
                QATemplate(question: "What battery percentage is shown?", answerHint: "Read battery level", difficulty: 1),
            ],
            notes: "iOS Settings → Battery"
        )
    }

    func testSettingsCellular() {
        let settings = XCUIApplication(bundleIdentifier: "com.apple.Preferences")
        settings.launch()
        sleep(1)

        let cellularCell = settings.cells.containing(.staticText, identifier: "Cellular").firstMatch
        if cellularCell.waitForExistence(timeout: 5) {
            cellularCell.tap()
            sleep(2)

            captureScreen(
                scenarioID: "xctest_settings_cellular",
                screenFamily: "settings_cellular",
                description: "Settings > Cellular screen",
                qaTemplates: [
                    QATemplate(question: "Is Cellular Data on or off?", answerHint: "Check toggle", difficulty: 1),
                ],
                notes: "iOS Settings → Cellular"
            )
        }
    }

    // MARK: - System App Scenarios

    func testCalculator() {
        let calculator = XCUIApplication(bundleIdentifier: "com.apple.calculator")
        calculator.launch()
        sleep(2)

        captureScreen(
            scenarioID: "xctest_calculator_basic",
            screenFamily: "calculator",
            description: "Calculator app in basic mode",
            qaTemplates: [
                QATemplate(question: "What mode is the calculator in?", answerHint: "Basic", difficulty: 1),
            ],
            notes: "iOS Calculator app"
        )
    }

    func testClock() {
        let clock = XCUIApplication(bundleIdentifier: "com.apple.mobiletimer")
        clock.launch()
        sleep(2)

        captureScreen(
            scenarioID: "xctest_clock_default",
            screenFamily: "clock",
            description: "Clock app default tab",
            qaTemplates: [
                QATemplate(question: "What time is shown?", answerHint: "Read time display", difficulty: 1),
            ],
            notes: "iOS Clock app"
        )
    }

    func testMaps() {
        let maps = XCUIApplication(bundleIdentifier: "com.apple.Maps")
        maps.launch()
        sleep(3)

        captureScreen(
            scenarioID: "xctest_maps_default",
            screenFamily: "maps",
            description: "Maps app default view",
            qaTemplates: [
                QATemplate(question: "What visual mode is the map using?", answerHint: "Check map style", difficulty: 1),
            ],
            notes: "iOS Apple Maps app"
        )
    }

    func testWeather() {
        let weather = XCUIApplication(bundleIdentifier: "com.apple.weather")
        weather.launch()
        sleep(3)

        captureScreen(
            scenarioID: "xctest_weather_default",
            screenFamily: "weather",
            description: "Weather app default view",
            qaTemplates: [
                QATemplate(question: "What weather condition is shown?", answerHint: "Read condition", difficulty: 1),
                QATemplate(question: "What temperature is shown?", answerHint: "Read temperature", difficulty: 1),
            ],
            notes: "iOS Weather app"
        )
    }

    // MARK: - Capture Infrastructure

    private struct QATemplate {
        let question: String
        let answerHint: String
        let difficulty: Int
    }

    private func captureScreen(
        scenarioID: String,
        screenFamily: String,
        description: String,
        qaTemplates: [QATemplate],
        notes: String
    ) {
        let screenshot = XCUIScreen.main.screenshot()
        let filename = "\(scenarioID).png"
        let fileURL = outputDir.appending(path: filename)

        // Write PNG
        let pngData = screenshot.pngRepresentation
        do {
            try pngData.write(to: fileURL)
        } catch {
            XCTFail("Failed to write screenshot: \(error)")
            return
        }

        // Build Q&A templates JSON array
        let qaJSON = qaTemplates.map { qa -> [String: Any] in
            [
                "question": qa.question,
                "answer_hint": qa.answerHint,
                "difficulty": qa.difficulty,
            ]
        }

        // Write index entry
        let entry: [String: Any] = [
            "id": scenarioID,
            "image_filename": filename,
            "scenario_id": scenarioID,
            "screen_family": screenFamily,
            "description": description,
            "notes": notes,
            "source": "xctest_generated",
            "timestamp": ISO8601DateFormatter().string(from: Date()),
            "generator_version": "0.1.0",
            "qa_templates": qaJSON,
            "file_size_bytes": pngData.count,
        ]

        if let jsonData = try? JSONSerialization.data(withJSONObject: entry),
           let jsonString = String(data: jsonData, encoding: .utf8)
        {
            let indexURL = indexFileURL
            if let handle = try? FileHandle(forWritingTo: indexURL) {
                handle.seekToEndOfFile()
                handle.write(Data((jsonString + "\n").utf8))
                handle.closeFile()
            } else {
                try? (jsonString + "\n").write(to: indexURL, atomically: true, encoding: .utf8)
            }
        }

        // Attach to Xcode test results for visual review
        let attachment = XCTAttachment(screenshot: screenshot)
        attachment.name = scenarioID
        attachment.lifetime = .keepAlways
        add(attachment)
    }
}
