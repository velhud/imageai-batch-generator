import { BackendState } from '@/api/types';
import { api } from '@/api/client';
import { useQueryClient } from '@tanstack/react-query';
import { Button } from '@/components/common/Button';

export function GenerationSettingsPanel({ state }: { state: BackendState }) {
  const queryClient = useQueryClient();
  const gs = state.session.global_settings;

  const update = async (patch: Record<string, unknown>) => {
    await api.updateGlobalSettings(patch);
    queryClient.invalidateQueries({ queryKey: ['state'] });
  };

  const applyToSelected = async () => {
    const selectedIds = state.session.rows.filter((r) => r.selected).map((r) => r.id);
    const resetPatch = {
      provider_id: null,
      model_id: null,
      size_preset: null,
      custom_size: null,
      num_images: null,
      style_preset: null,
      negative_prompt: null,
      seed: null,
      random_seed: null,
      quality: null,
      safety: null,
      keep_images: null,
      generate_behavior: null,
      regen_use_same_seed: null,
    };
    await Promise.all(selectedIds.map((id) => api.updateRow(id, { settings: resetPatch })));
    queryClient.invalidateQueries({ queryKey: ['state'] });
  };

  return (
    <div className="space-y-5 text-sm pb-10">
      <div className="space-y-2">
        <label className="text-text-muted text-xs uppercase font-semibold">Image Dimensions</label>
        <select 
            value={gs.size_preset}
            onChange={(e) => update({ size_preset: e.target.value })}
            className="w-full bg-black/20 border border-white/10 rounded p-2 text-xs focus:border-primary outline-none"
        >
            <option value="Square 1024">Square 1024 (1024x1024)</option>
            <option value="Portrait">Portrait (1024x1536)</option>
            <option value="Landscape">Landscape (1536x1024)</option>
            <option value="Custom">Custom</option>
        </select>
      </div>

      <div className="grid grid-cols-2 gap-3">
        <div className="space-y-2">
            <label className="text-text-muted text-xs uppercase font-semibold">Batch Size</label>
            <input 
                type="number" min="1" max="8"
                value={gs.num_images}
                onChange={(e) => update({ num_images: parseInt(e.target.value, 10) })}
                className="w-full bg-black/20 border border-white/10 rounded p-2 text-xs"
            />
        </div>
        <div className="space-y-2">
            <label className="text-text-muted text-xs uppercase font-semibold">Style Preset</label>
            <select 
                value={gs.style_preset}
                onChange={(e) => update({ style_preset: e.target.value })}
                className="w-full bg-black/20 border border-white/10 rounded p-2 text-xs"
            >
                <option value="None">None</option>
                <option value="Photorealistic">Photorealistic</option>
                <option value="Illustration">Illustration</option>
                <option value="3D Render">3D Render</option>
            </select>
        </div>
      </div>

      <div className="space-y-2">
        <label className="text-text-muted text-xs uppercase font-semibold">Negative Prompt</label>
        <textarea 
            value={gs.negative_prompt || ""}
            onChange={(e) => update({ negative_prompt: e.target.value })}
            className="w-full h-20 bg-black/20 border border-white/10 rounded p-2 text-xs resize-none placeholder:text-white/10"
            placeholder="Low quality, blurry, distorted..."
        />
      </div>

      <div className="space-y-2 pt-2 border-t border-white/5">
        <div className="flex items-center justify-between">
            <label className="text-text-muted text-xs uppercase font-semibold">Seed</label>
            <label className="flex items-center gap-2 cursor-pointer">
                <input 
                    type="checkbox" 
                    checked={gs.random_seed}
                    onChange={(e) => update({ random_seed: e.target.checked })}
                    className="accent-primary"
                />
                <span className="text-xs text-text-muted">Randomize</span>
            </label>
        </div>
        {!gs.random_seed && (
            <input 
                type="number" 
                value={gs.seed || 0}
                onChange={(e) => update({ seed: parseInt(e.target.value, 10) })}
                className="w-full bg-black/20 border border-white/10 rounded p-2 text-xs"
            />
        )}
      </div>

      <div className="space-y-4 pt-2 border-t border-white/5">
        <div className="space-y-1">
            <div className="flex justify-between text-xs text-text-muted">
                <span>Quality</span>
                <span>{gs.quality}</span>
            </div>
            <input 
                type="range" min="1" max="10" 
                value={gs.quality}
                onChange={(e) => update({ quality: parseInt(e.target.value, 10) })}
                className="w-full accent-primary h-1 bg-white/10 rounded-lg appearance-none cursor-pointer"
            />
        </div>
        <div className="space-y-1">
            <div className="flex justify-between text-xs text-text-muted">
                <span>Safety Filter</span>
                <span>{gs.safety}</span>
            </div>
            <input 
                type="range" min="0" max="3" 
                value={gs.safety}
                onChange={(e) => update({ safety: parseInt(e.target.value, 10) })}
                className="w-full accent-primary h-1 bg-white/10 rounded-lg appearance-none cursor-pointer"
            />
        </div>
      </div>

      <div className="space-y-2 pt-2 border-t border-white/5">
        <label className="text-text-muted text-xs uppercase font-semibold">Reasoning (Thinking)</label>
        <div className="grid grid-cols-2 gap-4">
            <div className="space-y-1">
                <label className="text-xs text-text-muted">Pro: Level</label>
                <select 
                    value={gs.thinking_level || "high"}
                    onChange={(e) => update({ thinking_level: e.target.value })}
                    className="w-full bg-black/20 border border-white/10 rounded p-2 text-xs"
                >
                    <option value="low">Low (Faster)</option>
                    <option value="high">High (Better)</option>
                </select>
            </div>

            <div className="space-y-1">
                <label className="text-xs text-text-muted">Nano: Budget</label>
                <div className="flex gap-2">
                    <input 
                        type="number" 
                        value={gs.thinking_budget}
                        onChange={(e) => update({ thinking_budget: parseInt(e.target.value, 10) })}
                        className="w-full bg-black/20 border border-white/10 rounded p-2 text-xs"
                        placeholder="0 to disable"
                    />
                </div>
                <p className="text-[10px] text-text-muted">-1 = Dynamic, 0 = Off</p>
            </div>
        </div>
      </div>

      <div className="space-y-2 pt-2 border-t border-white/5">
        <label className="text-text-muted text-xs uppercase font-semibold">Generation Behavior</label>
        <select 
            value={gs.generate_behavior}
            onChange={(e) => update({ generate_behavior: e.target.value })}
            className="w-full bg-black/20 border border-white/10 rounded p-2 text-xs"
        >
            <option value="keep">Keep Existing Images</option>
            <option value="replace">Replace Existing Images</option>
        </select>
        
        <label className="flex items-center gap-2 cursor-pointer mt-2">
            <input 
                type="checkbox" 
                checked={gs.regen_use_same_seed}
                onChange={(e) => update({ regen_use_same_seed: e.target.checked })}
                className="accent-primary"
            />
            <span className="text-xs text-text-muted">Regenerate using same seed</span>
        </label>
        
        <label className="flex items-center gap-2 cursor-pointer">
            <input 
                type="checkbox" 
                checked={gs.prompt_highlighting}
                onChange={(e) => update({ prompt_highlighting: e.target.checked })}
                className="accent-primary"
            />
            <span className="text-xs text-text-muted">Syntax Highlighting</span>
        </label>
      </div>

      <div className="pt-4">
        <Button onClick={applyToSelected} className="w-full" variant="secondary" size="sm">
            Apply Defaults to Selected Rows
        </Button>
        <p className="text-[10px] text-text-muted mt-2 text-center">
            Resets specific row settings to use these globals.
        </p>
      </div>
    </div>
  );
}
