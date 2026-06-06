import Foundation

enum BackendError: Error {
    case invalidURL
    case server(String)
}

struct RPCRequest<Payload: Codable>: Codable {
    let action: String
    let data: Payload
}

struct RPCResponse<DataType: Codable>: Codable {
    let ok: Bool
    let data: DataType?
    let error: String?
}

final class BackendClient {
    private let baseURL: URL
    private let session: URLSession = .shared

    init(port: Int = 8765) {
        self.baseURL = URL(string: "http://127.0.0.1:\(port)/rpc")!
    }

    func fetchState() async throws -> BackendState {
        let resp: RPCResponse<BackendState> = try await send(action: "state", payload: Empty())
        if let data = resp.data, resp.ok { return data }
        throw BackendError.server(resp.error ?? "unknown")
    }

    func addRows(prompts: [String]) async throws -> [RowDTO] {
        let resp: RPCResponse<AddRowsResponse> = try await send(action: "add_rows", payload: ["prompts": prompts])
        guard resp.ok, let rows = resp.data?.rows else { throw BackendError.server(resp.error ?? "failed") }
        return rows
    }

    func updateRow(id: String, prompt: String? = nil, selected: Bool? = nil) async throws -> RowDTO {
        var payload: [String: AnyCodable] = ["row_id": AnyCodable(id)]
        if let prompt { payload["prompt"] = AnyCodable(prompt) }
        if let selected { payload["selected"] = AnyCodable(selected) }
        let resp: RPCResponse<RowDTO> = try await send(action: "update_row", payload: payload)
        guard resp.ok, let row = resp.data else { throw BackendError.server(resp.error ?? "failed") }
        return row
    }

    func deleteRows(ids: [String]) async throws {
        let _: RPCResponse<DeleteRowsResponse> = try await send(action: "delete_rows", payload: ["row_ids": ids])
    }

    func generate(ids: [String]) async throws {
        let _: RPCResponse<GenerateResponse> = try await send(action: "generate_rows", payload: ["row_ids": ids])
    }

    func stopAll() async throws {
        let _: RPCResponse<Empty> = try await send(action: "stop_all", payload: Empty())
    }

    func export(ids: [String], folder: String) async throws -> Int {
        let payload: [String: AnyCodable] = [
            "row_ids": AnyCodable(ids),
            "folder": AnyCodable(folder)
        ]
        let resp: RPCResponse<ExportResponse> = try await send(action: "export", payload: payload)
        guard resp.ok, let c = resp.data?.exported else { throw BackendError.server(resp.error ?? "export failed") }
        return c
    }

    func updateGlobal(settings: GlobalSettingsDTO) async throws -> GlobalSettingsDTO {
        let resp: RPCResponse<GlobalSettingsDTO> = try await send(action: "global_settings", payload: settings)
        guard resp.ok, let val = resp.data else { throw BackendError.server(resp.error ?? "failed") }
        return val
    }

    // MARK: - Transport

    private func send<Payload: Codable, Resp: Codable>(action: String, payload: Payload) async throws -> RPCResponse<Resp> {
        let req = RPCRequest(action: action, data: payload)
        var request = URLRequest(url: baseURL)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.httpBody = try JSONEncoder().encode(req)
        let (data, _) = try await session.data(for: request)
        return try JSONDecoder().decode(RPCResponse<Resp>.self, from: data)
    }
}

// MARK: - Helpers

struct Empty: Codable {}
struct AddRowsResponse: Codable { let rows: [RowDTO] }
struct DeleteRowsResponse: Codable { let rows: [RowDTO] }
struct GenerateResponse: Codable { let queued: [String] }
struct ExportResponse: Codable { let exported: Int }

/// Type-erased AnyCodable for dynamic payloads.
struct AnyCodable: Codable {
    let value: Any
    init(_ value: Any) { self.value = value }
    init(from decoder: Decoder) throws {
        let container = try decoder.singleValueContainer()
        if let i = try? container.decode(Int.self) { value = i }
        else if let b = try? container.decode(Bool.self) { value = b }
        else if let d = try? container.decode(Double.self) { value = d }
        else if let s = try? container.decode(String.self) { value = s }
        else if let a = try? container.decode([String].self) { value = a }
        else if container.decodeNil() { value = NSNull() }
        else { throw DecodingError.dataCorruptedError(in: container, debugDescription: "Unsupported") }
    }
    func encode(to encoder: Encoder) throws {
        var container = encoder.singleValueContainer()
        switch value {
        case let i as Int: try container.encode(i)
        case let b as Bool: try container.encode(b)
        case let d as Double: try container.encode(d)
        case let s as String: try container.encode(s)
        case let a as [String]: try container.encode(a)
        case is NSNull: try container.encodeNil()
        default:
            throw EncodingError.invalidValue(value, .init(codingPath: encoder.codingPath, debugDescription: "Unsupported"))
        }
    }
}
