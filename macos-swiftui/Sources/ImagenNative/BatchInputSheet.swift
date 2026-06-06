import SwiftUI

struct BatchInputSheet: View {
    @Environment(\.dismiss) private var dismiss
    @ObservedObject var appModel: AppViewModel
    @State private var rawText = ""
    @State private var mode: BatchMode = .lines
    @State private var preview: [String] = []
    @State private var error: String?
    @State private var applyMode: ApplyMode = .append
    @State private var promptField = "prompt"
    @State private var csvColumn = "prompt"

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            Picker("Mode", selection: $mode) {
                ForEach(BatchMode.allCases, id: \.self) { Text($0.title).tag($0) }
            }.pickerStyle(.segmented)
            TextField("Prompt field (JSON)", text: $promptField)
            TextField("CSV column (name or index)", text: $csvColumn)
            TextEditor(text: $rawText).frame(minHeight: 150)
            HStack {
                Button("Preview") { parse() }
                Spacer()
                Text(error ?? " ")
                    .foregroundColor(.red)
            }
            List(preview, id: \.self) { Text($0) }
            Picker("Apply", selection: $applyMode) {
                ForEach(ApplyMode.allCases, id: \.self) { Text($0.rawValue).tag($0) }
            }
            HStack {
                Spacer()
                Button("Apply") {
                    Task {
                        if preview.isEmpty { parse() }
                        await appModel.addRows(prompts: preview)
                        dismiss()
                    }
                }.disabled(preview.isEmpty)
                Button("Cancel", role: .cancel) { dismiss() }
            }
        }
        .padding()
        .frame(minWidth: 500, minHeight: 400)
    }

    private func parse() {
        let parser = BatchParser()
        let result = parser.parse(text: rawText, mode: mode, promptField: promptField, csvColumn: csvColumn)
        preview = result.prompts
        error = result.errors.first
    }
}

enum BatchMode: String, CaseIterable {
    case lines, numbered, json_array, json_lines, csv
    var title: String {
        switch self {
        case .lines: return "Lines"
        case .numbered: return "Numbered"
        case .json_array: return "JSON Array"
        case .json_lines: return "JSON Lines"
        case .csv: return "CSV"
        }
    }
}

enum ApplyMode: String, CaseIterable {
    case append = "Append new rows"
    case replace = "Replace all rows"
    case fill = "Fill empty then append"
}

struct BatchParseResult {
    let prompts: [String]
    let errors: [String]
}

final class BatchParser {
    func parse(text: String, mode: BatchMode, promptField: String, csvColumn: String) -> BatchParseResult {
        let lines = text.split(separator: "\n").map { String($0) }
        switch mode {
        case .lines:
            return BatchParseResult(prompts: lines.filter { !$0.isEmpty }, errors: [])
        case .numbered:
            var prompts: [String] = []
            var errors: [String] = []
            for line in lines {
                if let idx = line.firstIndex(where: { $0 == ")" || $0 == "." || $0 == "-" }) {
                    let prompt = line[line.index(after: idx)...].trimmingCharacters(in: .whitespaces)
                    prompts.append(prompt)
                } else {
                    errors.append("Could not parse \(line)")
                }
            }
            return BatchParseResult(prompts: prompts, errors: errors)
        case .json_array:
            if let data = text.data(using: .utf8),
               let arr = try? JSONSerialization.jsonObject(with: data) as? [Any] {
                let prompts = arr.compactMap { item -> String? in
                    if let s = item as? String { return s }
                    if let dict = item as? [String: Any], let p = dict[promptField] { return "\(p)" }
                    return nil
                }
                return BatchParseResult(prompts: prompts, errors: [])
            }
            return BatchParseResult(prompts: [], errors: ["JSON parse error"])
        case .json_lines:
            var prompts: [String] = []
            var errors: [String] = []
            for line in lines where !line.isEmpty {
                if let data = line.data(using: .utf8),
                   let obj = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
                   let p = obj[promptField] {
                    prompts.append("\(p)")
                } else {
                    errors.append("Bad JSON line")
                }
            }
            return BatchParseResult(prompts: prompts, errors: errors)
        case .csv:
            var prompts: [String] = []
            var errors: [String] = []
            let rows = lines.map { $0.split(separator: ",").map { String($0) } }
            guard !rows.isEmpty else { return BatchParseResult(prompts: [], errors: ["Empty CSV"]) }
            let hasHeader = Int(csvColumn) == nil
            let body = hasHeader ? Array(rows.dropFirst()) : rows
            let headers = hasHeader ? rows.first ?? [] : []
            let idx: Int
            if let n = Int(csvColumn) { idx = n } else { idx = headers.firstIndex(of: csvColumn) ?? 0 }
            for (i, row) in body.enumerated() {
                if idx < row.count { prompts.append(row[idx]) }
                else { errors.append("Missing column at line \(i)") }
            }
            return BatchParseResult(prompts: prompts, errors: errors)
        }
    }
}
