import Foundation
import SwiftUI

@MainActor
final class AppViewModel: ObservableObject {
    @Published var providers: [ProviderInfo] = []
    @Published var session: SessionDTO?
    @Published var stats: StatsDTO?
    @Published var errorMessage: String?
    @Published var isLoading = false

    let client = BackendClient()

    func load() async {
        isLoading = true
        defer { isLoading = false }
        do {
            let state = try await client.fetchState()
            providers = state.providers
            session = state.session
            stats = state.stats
        } catch {
            errorMessage = error.localizedDescription
        }
    }

    func addRows(prompts: [String]) async {
        do {
            _ = try await client.addRows(prompts: prompts)
            await load()
        } catch { errorMessage = error.localizedDescription }
    }

    func updateRowPrompt(id: String, prompt: String) async {
        do { _ = try await client.updateRow(id: id, prompt: prompt); await load() }
        catch { errorMessage = error.localizedDescription }
    }

    func setSelection(id: String, selected: Bool) async {
        do { _ = try await client.updateRow(id: id, selected: selected); await load() }
        catch { errorMessage = error.localizedDescription }
    }

    func deleteRows(ids: [String]) async {
        do { try await client.deleteRows(ids: ids); await load() }
        catch { errorMessage = error.localizedDescription }
    }

    func generate(ids: [String]) async {
        do { try await client.generate(ids: ids); await load() }
        catch { errorMessage = error.localizedDescription }
    }

    func export(ids: [String], folder: String) async {
        do { _ = try await client.export(ids: ids, folder: folder) }
        catch { errorMessage = error.localizedDescription }
    }

    func updateGlobal(settings: GlobalSettingsDTO) async {
        do {
            _ = try await client.updateGlobal(settings: settings)
            await load()
        } catch { errorMessage = error.localizedDescription }
    }
}
