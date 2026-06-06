import { RowDTO } from '@/api/types';
import { api } from '@/api/client';
import { useQueryClient } from '@tanstack/react-query';

export function RowSettingsOverride({ row }: { row: RowDTO }) {
    const queryClient = useQueryClient();
    const s = row.settings;

    const update = async (patch: Record<string, unknown>) => {
        await api.updateRow(row.id, { settings: patch });
        queryClient.invalidateQueries({ queryKey: ['state'] });
    };

    return (
        <div className="grid grid-cols-2 gap-x-4 gap-y-3 text-xs p-1">
            <div className="col-span-2 text-text-muted font-semibold border-b border-white/5 pb-1 mb-1">
                Override Global Settings
            </div>
            
            <div className="flex flex-col gap-1">
                <label className="text-text-muted">Provider</label>
                <input 
                    className="bg-surface border border-white/10 rounded px-2 py-1"
                    placeholder="Global"
                    value={s.provider_id || ""}
                    onChange={e => update({ provider_id: e.target.value || null })} 
                />
            </div>

            <div className="flex flex-col gap-1">
                <label className="text-text-muted">Model</label>
                <input 
                    className="bg-surface border border-white/10 rounded px-2 py-1"
                    placeholder="Global"
                    value={s.model_id || ""}
                    onChange={e => update({ model_id: e.target.value || null })} 
                />
            </div>

            <div className="flex flex-col gap-1">
                <label className="text-text-muted">Size</label>
                <select 
                    className="bg-surface border border-white/10 rounded px-2 py-1"
                    value={s.size_preset || ""}
                    onChange={e => update({ size_preset: e.target.value || null })}
                >
                    <option value="">Global</option>
                    <option value="Square 1024">Square 1024</option>
                    <option value="Portrait">Portrait</option>
                    <option value="Landscape">Landscape</option>
                    <option value="Custom">Custom</option>
                </select>
            </div>

            <div className="flex flex-col gap-1">
                <label className="text-text-muted">Style</label>
                <select 
                    className="bg-surface border border-white/10 rounded px-2 py-1"
                    value={s.style_preset || ""}
                    onChange={e => update({ style_preset: e.target.value || null })}
                >
                    <option value="">Global</option>
                    <option value="None">None</option>
                    <option value="Photorealistic">Photorealistic</option>
                    <option value="Illustration">Illustration</option>
                    <option value="3D Render">3D Render</option>
                </select>
            </div>

            <div className="flex flex-col gap-1">
                <label className="text-text-muted">Seed</label>
                <div className="flex gap-2">
                    <input 
                        type="number"
                        className="bg-surface border border-white/10 rounded px-2 py-1 flex-1"
                        placeholder="Global"
                        value={s.seed ?? ""}
                        onChange={e => update({ seed: e.target.value ? parseInt(e.target.value, 10) : null })}
                        disabled={s.random_seed === true}
                    />
                    <label className="flex items-center gap-1 cursor-pointer">
                        <input 
                            type="checkbox" 
                            checked={s.random_seed === true} 
                            onChange={e => update({ random_seed: e.target.checked ? true : null })}
                        />
                        <span>Rnd</span>
                    </label>
                </div>
            </div>

            <div className="flex flex-col gap-1">
                <label className="text-text-muted">Image Count</label>
                <input 
                    type="number" min="1" max="8"
                    className="bg-surface border border-white/10 rounded px-2 py-1"
                    placeholder="Global"
                    value={s.num_images ?? ""}
                    onChange={e => update({ num_images: e.target.value ? parseInt(e.target.value, 10) : null })}
                />
            </div>

            <div className="flex flex-col gap-1">
                <label className="text-text-muted">Quality (1-10)</label>
                <input 
                    type="number" min="1" max="10"
                    className="bg-surface border border-white/10 rounded px-2 py-1"
                    placeholder="Global"
                    value={s.quality ?? ""}
                    onChange={e => update({ quality: e.target.value ? parseInt(e.target.value, 10) : null })}
                />
            </div>

            <div className="flex flex-col gap-1">
                <label className="text-text-muted">Safety (0-3)</label>
                <input 
                    type="number" min="0" max="3"
                    className="bg-surface border border-white/10 rounded px-2 py-1"
                    placeholder="Global"
                    value={s.safety ?? ""}
                    onChange={e => update({ safety: e.target.value ? parseInt(e.target.value, 10) : null })}
                />
            </div>

            <div className="col-span-2 flex flex-col gap-1">
                <label className="text-text-muted">Negative Prompt</label>
                <textarea 
                    className="bg-surface border border-white/10 rounded px-2 py-1 h-12 resize-none placeholder:text-white/10"
                    placeholder="Global Default"
                    value={s.negative_prompt || ""}
                    onChange={e => update({ negative_prompt: e.target.value || null })}
                />
            </div>
            
            <button 
                className="col-span-2 mt-2 text-text-muted hover:text-white underline text-left"
                onClick={() => update({ 
                    provider_id: null, model_id: null, size_preset: null, custom_size: null, num_images: null, style_preset: null,
                    seed: null, random_seed: null, quality: null, safety: null, negative_prompt: null, keep_images: null,
                    generate_behavior: null, regen_use_same_seed: null
                })}
            >
                Reset All Overrides
            </button>
        </div>
    );
}
