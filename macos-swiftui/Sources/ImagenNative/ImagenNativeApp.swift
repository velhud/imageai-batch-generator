import SwiftUI

@main
struct ImagenNativeApp: App {
    var body: some Scene {
        WindowGroup {
            ContentView()
                .onAppear {
                    BackendLauncher.shared.ensureRunning()
                }
        }
        .commands {
            CommandGroup(replacing: .newItem) { }
        }
    }
}
