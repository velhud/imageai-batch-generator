import SwiftUI

struct ContentView: View {
    @StateObject private var model = AppViewModel()
    @State private var batchSheet = false
    @State private var addMany = false
    @State private var newRowsCount = 10
    @State private var selectedRowIDs: Set<String> = []
    @State private var showSettings = false
    @State private var showError = false

    var body: some View {
        NavigationStack {
            VStack(spacing: 0) {
                toolbar
                Divider()
                rowsList
                Divider()
                bottomBar
            }
            .sheet(isPresented: $batchSheet) { BatchInputSheet(appModel: model) }
            .sheet(isPresented: $showSettings) { SettingsSheet(appModel: model) }
            .alert("Error", isPresented: Binding(get: { model.errorMessage != nil }, set: { _ in model.errorMessage = nil })) {
                Button("OK", role: .cancel) {}
            } message: {
                Text(model.errorMessage ?? "")
            }
            .task { await model.load() }
        }
    }

    private var toolbar: some View {
        HStack {
            Picker("Provider", selection: Binding(
                get: { model.session?.global_settings.provider_id ?? "" },
                set: { _ in }
            )) {
                ForEach(model.providers) { provider in
                    Text(provider.name).tag(provider.id)
                }
            }
            Picker("Model", selection: Binding.constant("")) {
                Text("Model").tag("")
            }
            Button("Batch Input…") { batchSheet = true }
            Button("Settings…") { showSettings = true }
            Spacer()
            statsView
        }
        .padding(8)
    }

    private var statsView: some View {
        if let stats = model.stats {
            return AnyView(
                HStack {
                    Text("Rows \(stats.total)")
                    Text("✓ \(stats.completed)")
                    Text("⚠︎ \(stats.errors)")
                }
            )
        }
        return AnyView(EmptyView())
    }

    private var rowsList: some View {
        ScrollView {
            LazyVStack(alignment: .leading, spacing: 12) {
                ForEach(model.session?.rows ?? []) { row in
                    RowCard(row: row, selected: selectedRowIDs.contains(row.id)) { selection in
                        Task { await model.setSelection(id: row.id, selected: selection) }
                        if selection { selectedRowIDs.insert(row.id) } else { selectedRowIDs.remove(row.id) }
                    } onPromptChange: { newPrompt in
                        Task { await model.updateRowPrompt(id: row.id, prompt: newPrompt) }
                    } generate: {
                        Task { await model.generate(ids: [row.id]) }
                    } delete: {
                        Task { await model.deleteRows(ids: [row.id]) }
                    }
                    Divider()
                }
            }
            .padding()
        }
    }

    private var bottomBar: some View {
        HStack {
            Button {
                addMany = true
            } label: {
                Label("Add Rows", systemImage: "plus.square.on.square")
            }
            .popover(isPresented: $addMany) {
                VStack {
                    Stepper("Rows: \(newRowsCount)", value: $newRowsCount, in: 1...500)
                    Button("Add") {
                        Task { await model.addRows(prompts: Array(repeating: "", count: newRowsCount)) }
                        addMany = false
                    }
                }.padding()
            }
            Spacer()
            Button {
                Task { await model.generate(ids: Array(selectedRowIDs)) }
            } label: { Label("Generate Selected", systemImage: "play.fill") }
            Button {
                Task { await model.generate(ids: model.session?.rows.map { $0.id } ?? []) }
            } label: { Label("Generate All", systemImage: "play.circle") }
            Button(role: .destructive) {
                Task { await model.deleteRows(ids: Array(selectedRowIDs)) }
            } label: { Label("Delete Selected", systemImage: "trash") }
        }
        .padding(8)
    }
}

struct RowCard: View {
    let row: RowDTO
    let selected: Bool
    var onSelection: (Bool) -> Void
    var onPromptChange: (String) -> Void
    var generate: () -> Void
    var delete: () -> Void

    @State private var prompt: String = ""

    var body: some View {
        VStack(alignment: .leading, spacing: 6) {
            HStack {
                Toggle("", isOn: Binding(get: { selected }, set: { onSelection($0) }))
                    .toggleStyle(.checkbox)
                Text("#\(row.id)")
                Spacer()
                statusLabel
            }
            TextEditor(text: Binding(
                get: { prompt.isEmpty ? row.prompt : prompt },
                set: { new in prompt = new; onPromptChange(new) }
            ))
            .frame(minHeight: 80)
            .overlay(alignment: .bottomTrailing) { Text("\((prompt.isEmpty ? row.prompt : prompt).count) chars").font(.caption2).padding(4) }
            HStack {
                Button("Generate") { generate() }
                Button("Delete", role: .destructive) { delete() }
                Spacer()
                if let img = row.images.last {
                    Text(URL(fileURLWithPath: img.file_path).lastPathComponent)
                        .font(.caption)
                } else {
                    Text("No image").font(.caption)
                }
            }
        }
        .onAppear { prompt = row.prompt }
    }

    private var statusLabel: some View {
        Text(row.status)
            .font(.caption)
            .padding(4)
            .background(statusColor.opacity(0.2))
            .cornerRadius(4)
    }

    private var statusColor: Color {
        switch row.status.lowercased() {
        case "completed": return .green
        case "error": return .red
        case "generating": return .orange
        case "queued": return .yellow
        default: return .gray
        }
    }
}
