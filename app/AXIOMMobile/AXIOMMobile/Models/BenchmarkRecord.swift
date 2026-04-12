import Foundation

struct BenchmarkRecord: Sendable {
    let timestamp: Date
    let modelID: String
    let imageLoaded: Bool
    let questionLength: Int
    let latencyMs: Int
    let isPlaceholder: Bool
    let runKind: RunKind
    let iterationIndex: Int

    enum RunKind: String, Sendable {
        case single
        case benchmark
    }
}

extension BenchmarkRecord {
    static let csvHeader = "timestamp,model_id,image_loaded,question_length,latency_ms,is_placeholder,run_kind,iteration_index"

    var csvRow: String {
        let ts = timestamp.formatted(.iso8601)
        return "\(ts),\(modelID),\(imageLoaded),\(questionLength),\(latencyMs),\(isPlaceholder),\(runKind.rawValue),\(iterationIndex)"
    }
}
