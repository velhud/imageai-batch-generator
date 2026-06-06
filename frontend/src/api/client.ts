import { BackendState, GlobalSettingsDTO, InputAttachmentDTO, RowDTO, RowSettingsDTO, RPCResponse, PromptTemplateDTO } from './types';

export const RPC_BASE_URL = 'http://127.0.0.1:8765';
const RPC_ENDPOINT = `${RPC_BASE_URL}/rpc`;
export const imageUrl = (path: string) => `${RPC_BASE_URL}/images?path=${encodeURIComponent(path)}`;

async function rpcCall<T>(action: string, data: Record<string, any> = {}): Promise<T> {
  const response = await fetch(RPC_ENDPOINT, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ action, data }),
  });

  if (!response.ok) {
    throw new Error(`HTTP Error: ${response.status}`);
  }

  const json: RPCResponse<T> = await response.json();
  if (!json.ok) {
    throw new Error(json.error || 'Unknown RPC error');
  }

  if (!('data' in json)) {
    throw new Error('Malformed RPC response');
  }

  return json.data as T;
}

export const api = {
  fetchState: () => rpcCall<BackendState>('state'),

  // Session
  newSession: () => rpcCall<BackendState>('new_session'),
  saveSession: (path?: string) => rpcCall<{ saved: boolean }>('save_session', { path }),
  loadSession: (path: string) => rpcCall<BackendState>('load_session', { path }),
  undo: () => rpcCall<BackendState>('undo'),
  redo: () => rpcCall<BackendState>('redo'),
  
  addRows: (prompts: string[]) => rpcCall<{ rows: RowDTO[] }>('add_rows', { prompts }),
  
  updateRow: (row_id: string, updates: { 
    prompt?: string; 
    selected?: boolean;
    tags?: string[];
    settings?: Partial<RowSettingsDTO>;
    attachments?: InputAttachmentDTO[];
  }) => rpcCall<RowDTO>('update_row', { row_id, ...updates }),
    
  deleteRows: (row_ids: string[]) => rpcCall<{ rows: RowDTO[] }>('delete_rows', { row_ids }),
  duplicateRow: (row_id: string) => rpcCall<BackendState>('duplicate_row', { row_id }),
  
  generateRows: (row_ids: string[]) => rpcCall<{ queued: string[] }>('generate_rows', { row_ids }),
  
  stopAll: () => rpcCall<{ stopped: boolean }>('stop_all'),
  
  updateGlobalSettings: (settings: Partial<GlobalSettingsDTO>) => 
    rpcCall<GlobalSettingsDTO>('global_settings', settings),

  selectFolder: () => rpcCall<{ path: string }>('select_folder'),
  selectImageFile: () => rpcCall<{ path: string; mime: string } | null>('select_image_file'),
  export: (row_ids: string[], folder: string) => 
    rpcCall<{ exported: number }>('export', { row_ids, folder }),

  openPath: (path: string) => rpcCall<{ opened: boolean }>('open_path', { path }),
  copyImage: (path: string) => rpcCall<{ copied: boolean }>('copy_image_to_clipboard', { path }),

  saveTemplate: (template: PromptTemplateDTO) => rpcCall<{ templates: PromptTemplateDTO[] }>('save_template', template),
  expandTemplate: (template: PromptTemplateDTO) => rpcCall<{ prompts: string[] }>('expand_template', template),
};
