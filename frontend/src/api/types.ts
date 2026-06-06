export type RowStatus = "Idle" | "Queued" | "Generating" | "Completed" | "Error" | "Cancelled";

export interface ProviderInfo {
  id: string;
  name: string;
  rate_limit_note?: string;
  models: ModelInfo[];
}

export interface ModelInfo {
  id: string;
  name: string;
  provider_id: string;
}

export interface SizePresetDTO {
  width: number;
  height: number;
}

export interface InputAttachmentDTO {
  id: string;
  file_path: string;
  mime_type: string;
}

export interface GlobalSettingsDTO {
  provider_id: string;
  model_id: string;
  size_preset: string;
  custom_size?: SizePresetDTO | null;
  num_images: number;
  style_preset: string;
  negative_prompt: string;
  seed?: number;
  random_seed: boolean;
  quality: number;
  safety: number;
  export_folder?: string;
  naming_pattern: string;
  concurrency_limit: number;
  theme: string;
  prompt_highlighting: boolean;
  generate_behavior: string;
  regen_use_same_seed: boolean;
  confirm_generate_threshold: number;
  rate_limit_rpm: number;
  thinking_budget: number;
  thinking_level: string;
}

export interface ImageResultDTO {
  id: string;
  row_id: string;
  file_path: string;
}

export interface RowSettingsDTO {
  provider_id?: string | null;
  model_id?: string | null;
  size_preset?: string | null;
  custom_size?: SizePresetDTO | null;
  num_images?: number | null;
  style_preset?: string | null;
  negative_prompt?: string | null;
  seed?: number | null;
  random_seed?: boolean | null;
  quality?: number | null;
  safety?: number | null;
  keep_images?: boolean | null;
  generate_behavior?: string | null;
  regen_use_same_seed?: boolean | null;
  thinking_budget?: number | null;
  thinking_level?: string | null;
}

export interface RowDTO {
  id: string;
  prompt: string;
  status: RowStatus;
  error_message: string;
  selected: boolean;
  settings: RowSettingsDTO;
  attachments: InputAttachmentDTO[];
  images: ImageResultDTO[];
  tags: string[];
}

export interface PromptTemplateDTO {
  name: string;
  template: string;
  variables: Record<string, string[]>;
}

export interface SessionDTO {
  id: string;
  global_settings: GlobalSettingsDTO;
  rows: RowDTO[];
  templates: PromptTemplateDTO[];
}

export interface StatsDTO {
  total: number;
  completed: number;
  errors: number;
  average_duration: number;
  per_provider?: Record<string, number>;
}

export interface BackendState {
  session: SessionDTO;
  providers: ProviderInfo[];
  stats: StatsDTO;
}

// RPC Response Wrappers
export interface RPCResponse<T> {
  ok: boolean;
  data?: T;
  error?: string;
}
