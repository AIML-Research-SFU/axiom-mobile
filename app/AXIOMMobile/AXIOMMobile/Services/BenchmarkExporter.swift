import Foundation

enum BenchmarkExporter {
    static func writeCSV(_ records: [BenchmarkRecord]) throws -> URL {
        var lines = [BenchmarkRecord.csvHeader]
        for record in records {
            lines.append(record.csvRow)
        }
        let csv = lines.joined(separator: "\n") + "\n"

        let stamp = Date.now.formatted(.iso8601)
            .replacingOccurrences(of: "-", with: "")
            .replacingOccurrences(of: ":", with: "")
        let filename = "axiom_benchmark_\(stamp).csv"
        let url = URL.documentsDirectory.appending(path: filename)
        try csv.write(to: url, atomically: true, encoding: .utf8)
        return url
    }
}
