import Foundation

final class BackendLauncher {
    static let shared = BackendLauncher()
    private var process: Process?
    private init() {}

    /// Ensure backend server is running; launches if unreachable.
    func ensureRunning() {
        Task.detached { [weak self] in
            guard let self else { return }
            if await self.isReachable() { return }
            self.launch()
        }
    }

    private func launch() {
        let process = Process()
        process.executableURL = URL(fileURLWithPath: "/usr/bin/env")
        process.arguments = ["python3", "-m", "app.backend_server"]
        // Assume the Swift package directory is macos-swiftui/; go one level up to repo root.
        let cwd = URL(fileURLWithPath: FileManager.default.currentDirectoryPath).deletingLastPathComponent()
        process.currentDirectoryURL = cwd
        do {
            try process.run()
            self.process = process
        } catch {
            print("Failed to start backend server: \(error)")
        }
    }

    private func isReachable() async -> Bool {
        guard let url = URL(string: "http://127.0.0.1:8765/rpc") else { return false }
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.httpBody = #"{"action":"state","data":{}}"#.data(using: .utf8)
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        do {
            let (_, response) = try await URLSession.shared.data(for: request)
            if let http = response as? HTTPURLResponse { return (200...299).contains(http.statusCode) }
        } catch { return false }
        return false
    }
}
