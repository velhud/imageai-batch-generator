import SwiftUI

struct SettingsSheet: View {
    @Environment(\.dismiss) private var dismiss
    @ObservedObject var appModel: AppViewModel
    @State private var concurrency: Int = 2
    @State private var exportFolder: String = ""
    @State private var rpm: Int = 60
    @State private var threshold: Int = 300

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            Stepper("Concurrency: \(concurrency)", value: $concurrency, in: 1...8)
            TextField("Export folder", text: $exportFolder)
            Stepper("Requests per minute: \(rpm)", value: $rpm, in: 1...500)
            Stepper("Confirm threshold: \(threshold)", value: $threshold, in: 10...10000)
            HStack {
                Spacer()
                Button("Save") {
                    Task {
                        if var gs = appModel.session?.global_settings {
                            gs.concurrency_limit = concurrency
                            gs.export_folder = exportFolder
                            gs.rate_limit_rpm = rpm
                            gs.confirm_generate_threshold = threshold
                            await appModel.updateGlobal(settings: gs)
                        }
                        dismiss()
                    }
                }
                Button("Cancel", role: .cancel) { dismiss() }
            }
        }
        .padding()
        .onAppear {
            if let gs = appModel.session?.global_settings {
                concurrency = gs.concurrency_limit
                exportFolder = gs.export_folder ?? ""
                rpm = gs.rate_limit_rpm
                threshold = gs.confirm_generate_threshold
            }
        }
        .frame(minWidth: 400)
    }
}
