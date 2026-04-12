import Foundation

struct SessionMetadata: Codable, Sendable {
    let sessionID: String
    let exportTimestamp: String
    let deviceName: String
    let deviceModel: String
    let systemName: String
    let systemVersion: String
    let appVersion: String
    let appBuild: String
    let modelID: String
    let isPlaceholder: Bool
    let benchmarkIterations: Int
    let recordCount: Int

    enum CodingKeys: String, CodingKey {
        case sessionID = "session_id"
        case exportTimestamp = "export_timestamp"
        case deviceName = "device_name"
        case deviceModel = "device_model"
        case systemName = "system_name"
        case systemVersion = "system_version"
        case appVersion = "app_version"
        case appBuild = "app_build"
        case modelID = "model_id"
        case isPlaceholder = "is_placeholder"
        case benchmarkIterations = "benchmark_iterations"
        case recordCount = "record_count"
    }
}
