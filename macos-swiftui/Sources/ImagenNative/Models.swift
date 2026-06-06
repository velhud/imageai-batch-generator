import Foundation
import SwiftUI

struct ProviderInfo: Codable, Identifiable {
    let id: String
    let name: String
    let rate_limit_note: String?
    let models: [ModelInfo]
}

struct ModelInfo: Codable, Identifiable {
    let id: String
    let name: String
    let provider_id: String
}

struct GlobalSettingsDTO: Codable {
    var provider_id: String
    var model_id: String
    var size_preset: String
    var num_images: Int
    var style_preset: String
    var negative_prompt: String
    var seed: Int?
    var random_seed: Bool
    var quality: Int
    var safety: Int
    var export_folder: String?
    var naming_pattern: String
    var concurrency_limit: Int
    var theme: String
    var prompt_highlighting: Bool
    var generate_behavior: String
    var regen_use_same_seed: Bool
    var confirm_generate_threshold: Int
    var rate_limit_rpm: Int
}

struct RowSettingsDTO: Codable {
    var provider_id: String?
    var model_id: String?
    var size_preset: String?
    var num_images: Int?
    var style_preset: String?
    var negative_prompt: String?
    var seed: Int?
    var random_seed: Bool?
    var quality: Int?
    var safety: Int?
    var keep_images: Bool?
    var generate_behavior: String?
    var regen_use_same_seed: Bool?
}

struct ImageResultDTO: Codable, Identifiable {
    let id: String
    let row_id: String
    let file_path: String
}

struct RowDTO: Codable, Identifiable {
    let id: String
    var prompt: String
    var status: String
    var error_message: String
    var selected: Bool
    var settings: RowSettingsDTO
    var images: [ImageResultDTO]
    var tags: [String]?
}

struct SessionDTO: Codable {
    let id: String
    var global_settings: GlobalSettingsDTO
    var rows: [RowDTO]
}

struct StatsDTO: Codable {
    let total: Int
    let completed: Int
    let errors: Int
    let average_duration: Double
    let per_provider: [String: Int]?
    let per_model: [String: Int]?
}

struct BackendState: Codable {
    let session: SessionDTO
    let providers: [ProviderInfo]
    let stats: StatsDTO
}
