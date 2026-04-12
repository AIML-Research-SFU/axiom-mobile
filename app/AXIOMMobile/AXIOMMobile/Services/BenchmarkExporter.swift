import Foundation

enum BenchmarkExporter {
    static func sessionStamp() -> String {
        Date.now.formatted(.iso8601)
            .replacingOccurrences(of: "-", with: "")
            .replacingOccurrences(of: ":", with: "")
    }

    static func writeCSV(_ records: [BenchmarkRecord], stamp: String) throws -> URL {
        var lines = [BenchmarkRecord.csvHeader]
        for record in records {
            lines.append(record.csvRow)
        }
        let csv = lines.joined(separator: "\n") + "\n"

        let filename = "axiom_benchmark_\(stamp).csv"
        let url = URL.documentsDirectory.appending(path: filename)
        try csv.write(to: url, atomically: true, encoding: .utf8)
        return url
    }

    static func writeMetadata(_ metadata: SessionMetadata, stamp: String) throws -> URL {
        let encoder = JSONEncoder()
        encoder.outputFormatting = [.prettyPrinted, .sortedKeys]
        let data = try encoder.encode(metadata)

        let filename = "axiom_benchmark_\(stamp)_meta.json"
        let url = URL.documentsDirectory.appending(path: filename)
        try data.write(to: url, options: .atomic)
        return url
    }
}
